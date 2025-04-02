#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time, os, threading, random
from types import MethodType

def create_tsn_topo():
    setLogLevel('info')
    net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
    c0 = net.addController('c0')

    # 交换机 + 物理多队列网卡绑定
    s1 = net.addSwitch('s1')
    Intf('ens160', node=s1)  # 把 vmxnet3 (ens160) 绑定给 s1

    s2 = net.addSwitch('s2')
    Intf('ens192', node=s2)  # 把第二块 vmxnet3 (ens192) 绑定给 s2

    # 主机
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    # 拓扑内部链接
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s1, s2)
    net.addLink(s2, h3)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])

    load_kernel_modules()
    setup_ptp_sync(net)

    # 初始配置
    config_taprio(net)

    # 启动动态GCL更新线程
    update_thread = threading.Thread(target=dynamic_gcl_update, args=(net,))
    update_thread.daemon = True
    update_thread.start()

    CLI(net)
    net.stop()


def load_kernel_modules():
    for m in ['sch_taprio', 'ptp']:
        os.system(f"sudo modprobe {m} || true")


def setup_ptp_sync(net):
    info("*** 配置软件PTP同步\n")
    # 生成自定义PTP配置文件
    ptp_conf = """
[global]
tx_timestamp_timeout 100
logSyncInterval 0
syncReceiptTimeout 3
neighborPropDelayThresh 800
min_neighbor_prop_delay -20000000
"""

    # 配置主节点（h1）
    h1 = net.get('h1')
    h1.cmd("echo '%s' > /tmp/ptp.conf" % ptp_conf)
    h1.cmd("sudo ptp4l -i h1-eth0 -m -S -f /tmp/ptp.conf --socket_priority=0 > /tmp/ptp_master.log 2>&1 &")
    h1.cmd("sudo phc2sys -m -s h1-eth0 -c CLOCK_REALTIME -O 0 -u 1 > /tmp/phc2sys_master.log 2>&1 &")

    # 配置从节点
    for node in [net.get('s1'), net.get('s2'), net.get('h2'), net.get('h3')]:
        intf = node.intfList()[0].name
        node.cmd("echo '%s' > /tmp/ptp.conf" % ptp_conf)
        node.cmd(f"sudo ptp4l -i {intf} -m -S -f /tmp/ptp.conf -s --socket_priority=0 > /tmp/ptp_slave.log 2>&1 &")
        node.cmd(f"sudo phc2sys -m -s {intf} -c CLOCK_REALTIME -O 0 -u 1 > /tmp/phc2sys_slave.log 2>&1 &")
    time.sleep(8)  # 关键：必须足够长让同步完成

def config_taprio(net):
    """软件友好型配置"""
    base_time = int((time.time() + 5) * 1e9)  # 5秒后生效
    for sw, iface in [(net.get('s1'),'ens160'), (net.get('s2'),'ens192')]:
        # 清除可能残留的配置
        sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
        # 应用新配置（1ms周期）
        cmd = (
            f"sudo tc qdisc replace dev {iface} root taprio "
            f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
            f"queues 1@0 1@1 "
            f"base-time {base_time} "
            f"sched-entry S 01 500000 "  # 500us开放TC0
            f"sched-entry S 10 500000 "  # 500us开放TC1
            f"clockid CLOCK_REALTIME "   # 使用系统时钟
            f"flags 0x0"
        )
        sw.cmd(cmd)


def dynamic_gcl_update(net):
    """改进版动态GCL更新"""
    while True:
        time.sleep(30)
        info("\n*** 正在执行启发式GCL更新...\n")

        for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
            try:
                sched_entries, cycle_time = generate_heuristic_gcl()
                base_time = int((time.time() + 5) * 1e9)  # 延长到5秒后生效

                # 清除旧配置（强制模式）
                sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")

                # 构建新配置命令（保持配置一致性）
                cmd = (
                    f"sudo tc qdisc add dev {iface} root taprio "
                    f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
                    f"queues 1@0 1@1 "
                    f"base-time {base_time} "
                    f"{sched_entries} "
                    f"clockid CLOCK_REALTIME "  # 保持与初始配置一致
                    f"flags 0x0"  # 软件模式标识
                )

                # 执行配置并验证
                result = sw.cmd(cmd + " 2>&1")
                if "Error" in result:
                    info(f"!! {sw.name}配置失败: {result}\n")
                    sw.cmd(f"sudo tc qdisc replace dev {iface} root taprio ...")  # 回退配置
                else:
                    info(f"++ {sw.name} 新GCL生效于 {time.ctime(base_time / 1e9)}\n"
                         f"   周期: {cycle_time}ns 调度表: {sched_entries}\n")

            except Exception as e:
                info(f"!! {sw.name}更新异常: {str(e)}\n")
                import traceback
                traceback.print_exc()


def generate_heuristic_gcl():
    """修复版启发式GCL生成算法"""
    cycle_time = 200000  # 固定200us周期
    entries = []
    remaining = cycle_time

    # 生成前N-1个时间槽（保证最小间隔）
    for _ in range(2):
        max_duration = remaining - 10000  # 保留10us保护间隔
        duration = random.randint(50000, max_duration) if max_duration > 50000 else 50000
        gate_state = random.choice(["01", "10"])
        entries.append(f"sched-entry S {gate_state} {duration}")
        remaining -= duration

    # 最后一个时间槽（严格对齐周期）
    if remaining > 0:
        entries.append(f"sched-entry S {random.choice(['01', '10'])} {remaining}")
    else:  # 容错处理
        entries.append("sched-entry S 0f 10000")  # 默认开放所有队列

    # 验证周期完整性
    total = sum(int(e.split()[-1]) for e in entries)
    assert total == cycle_time, f"周期不匹配 {total} vs {cycle_time}"

    return " ".join(entries), cycle_time

if __name__ == '__main__':
    create_tsn_topo()
