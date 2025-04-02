#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time, os

def create_tsn_topo():
    setLogLevel('info')
    net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
    c0 = net.addController('c0')

    # 交换机 + 物理多队列网卡绑定
    s1 = net.addSwitch('s1')
    Intf('ens160', node=s1)       # 把 vmxnet3 (ens160) 绑定给 s1

    s2 = net.addSwitch('s2')
    Intf('ens192', node=s2)       # 把第二块 vmxnet3 (ens192) 绑定给 s2

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
    config_taprio(net)

    CLI(net)
    net.stop()

def load_kernel_modules():
    for m in ['sch_taprio','ptp']:
        os.system(f"sudo modprobe {m} || true")

def setup_ptp_sync(net):
    info("*** Configuring PTP Master on h1\n")
    net.get('h1').cmd('sudo ptpd4 -C -L -g -i h1-eth0 &')
    for node in [net.get('s1'), net.get('s2'), net.get('h2'), net.get('h3')]:
        intf = node.intfList()[0].name
        node.cmd(f"sudo ptpd4 -C -L -s -u 10.0.0.1 -i {intf} &")
    time.sleep(5)

def config_taprio(net):
    for sw, iface in [(net.get('s1'),'ens160'), (net.get('s2'),'ens192')]:
        sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null || true")
        base_time = int((time.time()+2)*1e9)
        cmd = (
            f"sudo tc qdisc add dev {iface} root taprio "
            f"num_tc 2 "
            f"map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
            f"queues 1@0 1@1 "
            f"base-time {base_time} "
            f"sched-entry S 01 100000 "
            f"sched-entry S 10 100000 "
            f"clockid CLOCK_TAI flags 0x1"
        )
        output = sw.cmd(cmd + " 2>&1")
        if "Error" in output:
            info(f"*** ERROR configuring taprio on {iface}: {output}\n")
        else:
            info(f"[{sw.name}] Taprio OK on {iface}\n")

if __name__ == '__main__':
    create_tsn_topo()
