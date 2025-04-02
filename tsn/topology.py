# tsn/topology.py
import time
import os
import threading
from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from tsn.ptp_sync import setup_ptp_sync
from tsn.taprio_config import config_taprio
from tsn.gcl_scheduler.heuristic import HeuristicGCLScheduler
from tsn.experiment_logger import log_experiment_data, measure_network_performance


def load_kernel_modules():
    for m in ['sch_taprio', 'ptp']:
        os.system(f"sudo modprobe {m} || true")


def create_tsn_topo(scheduler):
    setLogLevel('info')
    net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
    c0 = net.addController('c0')

    # 添加交换机并绑定物理网卡
    s1 = net.addSwitch('s1')
    Intf('ens160', node=s1)  # 绑定物理网卡 ens160

    s2 = net.addSwitch('s2')
    Intf('ens192', node=s2)  # 绑定物理网卡 ens192

    # 添加主机
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    # 建立拓扑链路
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
    config_taprio(net)

    # 启动动态 GCL 更新线程，传入选定的调度器对象
    update_thread = threading.Thread(target=dynamic_gcl_update, args=(net, scheduler))
    update_thread.daemon = True
    update_thread.start()

    CLI(net)
    net.stop()


def dynamic_gcl_update(net, scheduler, log_file='experiment_data.csv'):
    """
    动态 GCL 更新任务，每隔一段时间更新调度表，并记录相关数据到 CSV 文件中。
    """
    scheduler_name = type(scheduler).__name__
    while True:
        time.sleep(30)  # 每隔 30 秒更新一次
        info("\n*** 执行 GCL 更新...\n")
        try:
            # 生成新的 GCL 调度表
            sched_entries, cycle_time = scheduler.generate_gcl()
            base_time = int((time.time() + 5) * 1e9)  # 延迟 5 秒生效

            # 采集额外性能指标数据
            # extra_metrics = measure_network_performance()
            extra_metrics = measure_network_performance(net, source_host="h1", target_host="h3")

            for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
                # 删除旧配置
                sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
                # 构造新的 taprio 命令
                cmd = (
                    f"sudo tc qdisc add dev {iface} root taprio "
                    f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
                    f"queues 1@0 1@1 "
                    f"base-time {base_time} "
                    f"{sched_entries} "
                    f"clockid CLOCK_REALTIME "
                    f"flags 0x0"
                )
                result = sw.cmd(cmd + " 2>&1")
                if "Error" in result:
                    info(f"!! {sw.name} 更新错误: {result}\n")
                else:
                    info(f"++ {sw.name} GCL 更新生效于 {time.ctime(base_time / 1e9)}\n"
                         f"   周期: {cycle_time}ns, 调度表: {sched_entries}\n")

            # 将本次更新数据记录到 CSV 文件中
            log_experiment_data(log_file, time.time(), scheduler_name, cycle_time, sched_entries, extra_metrics)

        except Exception as e:
            info(f"!! 动态更新异常: {str(e)}\n")
