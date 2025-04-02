#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.link import Intf
from mininet.cli import CLI

def topo():
    net = Mininet(controller=Controller, switch=OVSSwitch)

    # 创建交换机
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    # 绑定物理 vmxnet3 接口
    Intf('ens160', node=s1)
    Intf('ens192', node=s2)

    # 添加两个测试主机
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')

    # 交换机-主机 & 交换机-交换机 链路
    net.addLink(h1, s1)
    net.addLink(s2, h2)
    net.addLink(s1, s2)

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    topo()
