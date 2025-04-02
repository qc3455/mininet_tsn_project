#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time, os, threading, random


def create_tsn_topo():
    setLogLevel('info')

    # 预清理步骤（关键修复）
    os.system('mn -c >/dev/null 2>&1')  # 清理Mininet残留
    os.system('sudo pkill -f ptpd4')  # 清除旧的时间同步进程
    os.system('sudo tc qdisc del dev ens160 root 2>/dev/null || true')
    os.system('sudo tc qdisc del dev ens192 root 2>/dev/null || true')

    net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
    c0 = net.addController('c0')

    # 交换机配置添加重试机制
    retry_count = 0
    while retry_count < 3:
        try:
            s1 = net.addSwitch('s1')
            Intf('ens160', node=s1)
            s2 = net.addSwitch('s2')
            Intf('ens192', node=s2)
            break
        except Exception as e:
            info(f"!! 接口绑定失败，重试中... ({str(e)})\n")
            os.system('sudo ip link del s1-eth4 2>/dev/null || true')
            os.system('sudo ip link del s2-eth2 2>/dev/null || true')
            retry_count += 1
            time.sleep(1)

    # 主机配置
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    # 拓扑连接（添加端口指定）
    net.addLink(h1, s1, port1=1, port2=1)
    net.addLink(h2, s1, port1=1, port2=2)
    net.addLink(s1, s2, port1=3, port2=1)  # 明确指定交换机间连接端口
    net.addLink(s2, h3, port1=2, port2=1)

    # 启动网络前二次清理
    for sw in [s1, s2]:
        for intf in sw.intfList():
            sw.cmd(f"sudo ip link del {intf.name} 2>/dev/null || true")
            time.sleep(0.5)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])

    # 等待端口稳定
    time.sleep(2)

    load_kernel_modules()
    setup_ptp_sync(net)

    # 初始配置
    config_taprio(net)

    # 线程安全启动
    net.running = True
    update_thread = threading.Thread(target=dynamic_gcl_update, args=(net,))
    update_thread.daemon = True
    update_thread.start()

    CLI(net)
    net.running = False  # 停止更新线程
    net.stop()


def load_kernel_modules():
    # 确保模块加载
    os.system('sudo modprobe -r sch_taprio 2>/dev/null || true')
    os.system('sudo modprobe sch_taprio')
    os.system('sudo modprobe ptp')


# ... 其他函数保持原有结构，重点添加以下改进 ...

def config_taprio(net):
    """增强的配置函数"""
    for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
        # 彻底清除残留配置
        for _ in range(2):  # 双重清理确保成功
            sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null || true")
            time.sleep(0.2)

        # 生成未来2秒后的基准时间
        base_time = int((time.time() + 2) * 1e9)

        # 添加随机偏移避免冲突
        base_time += random.randint(0, 5000000)

        # 构建配置命令
        cmd = (
            f"sudo tc qdisc replace dev {iface} root taprio "
            f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
            f"queues 1@0 1@1 "
            f"base-time {base_time} "
            f"sched-entry S 01 50000 "
            f"sched-entry S 10 50000 "
            f"clockid CLOCK_TAI flags 0x1"
        )

        # 带重试的执行
        for attempt in range(3):
            result = sw.cmd(cmd + " 2>&1")
            if "Error" not in result:
                break
            time.sleep(1)


def dynamic_gcl_update(net):
    """改进的更新线程"""
    while getattr(net, 'running', False):
        try:
            time.sleep(30)
            info("\n*** 执行安全更新...\n")

            # 暂停流量防止冲突
            os.system('sudo tc qdisc add dev ens160 handle ffff: ingress 2>/dev/null')
            os.system('sudo tc qdisc add dev ens192 handle ffff: ingress 2>/dev/null')

            # 执行配置更新
            config_taprio(net)

            # 恢复流量
            os.system('sudo tc qdisc del dev ens160 ingress 2>/dev/null')
            os.system('sudo tc qdisc del dev ens192 ingress 2>/dev/null')

        except Exception as e:
            info(f"!! 动态更新失败: {str(e)}\n")

def generate_heuristic_gcl():
    """启发式GCL生成算法（示例实现）"""
    # 示例算法：随机生成3个时间槽，总周期200000ns
    entries = []
    remaining = 200000
    for _ in range(2):
        duration = random.randint(50000, 150000)
        gate_state = random.choice(["01", "10"])
        entries.append(f"sched-entry S {gate_state} {duration}")
        remaining -= duration

    # 添加最后一个时间槽保证周期完整
    entries.append(f"sched-entry S {random.choice(['01', '10'])} {remaining}")

    # 添加保护带防止冲突
    cycle_time = 200000 + 10000  # 增加10us保护间隔
    return " ".join(entries), cycle_time


if __name__ == '__main__':
    create_tsn_topo()
