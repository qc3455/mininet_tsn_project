#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import argparse
import importlib
import os
import time
from schedulers import *
def parse_args():
    parser = argparse.ArgumentParser(description='TSN 实验框架')
    parser.add_argument('-s', '--scheduler', type=str, default='default',
                        help='选择调度器 (default|enhanced)')
    return parser.parse_args()


class TSNNetwork:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.net = None

    def build_topology(self):
        """构建基础网络拓扑"""
        setLogLevel('info')
        self.net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
        c0 = self.net.addController('c0')

        # 添加交换机并绑定物理接口
        s1 = self.net.addSwitch('s1')
        Intf('ens160', node=s1)
        info(f"交换机 s1 接口列表: {[intf.name for intf in s1.intfList()]}\n")  # 显示所有接口名

        s2 = self.net.addSwitch('s2')
        Intf('ens192', node=s2)
        info(f"交换机 s2 接口列表: {[intf.name for intf in s2.intfList()]}\n")

        # 添加主机和连接
        h1 = self.net.addHost('h1', ip='10.0.0.1/24')
        h2 = self.net.addHost('h2', ip='10.0.0.2/24')
        h3 = self.net.addHost('h3', ip='10.0.0.3/24')

        self.net.addLink(h1, s1)
        self.net.addLink(h2, s1)
        self.net.addLink(s1, s2)
        self.net.addLink(s2, h3)

        self.net.build()
        c0.start()
        s1.start([c0])
        s2.start([c0])

    def load_kernel_modules(self):
        """加载内核模块（公共部分）"""
        for m in ['sch_taprio', 'ptp']:
            os.system(f"sudo modprobe {m} || true")

    def setup_ptp_sync(self):
        """PTP时间同步（公共部分）"""
        info("*** 配置软件PTP同步\n")
        ptp_conf = """..."""  # PTP配置保持不变

        # 配置主节点（h1）
        h1 = self.net.get('h1')
        h1.cmd("echo '%s' > /tmp/ptp.conf" % ptp_conf)
        h1.cmd("sudo ptp4l -i h1-eth0 -m -S -f /tmp/ptp.conf --socket_priority=0 > /tmp/ptp_master.log 2>&1 &")

        # 配置从节点...

    def run(self):
        self.build_topology()
        self.load_kernel_modules()
        self.setup_ptp_sync()

        # 初始化调度器配置
        self.scheduler.setup(self.net)

        # 启动动态更新线程
        self.scheduler.start_dynamic_update(self.net)

        CLI(self.net)
        self.net.stop()


def load_scheduler(name):
    """动态加载调度器模块"""
    try:
        module = importlib.import_module(f'schedulers.{name}')
        return module.Scheduler()
    except ImportError:
        raise ValueError(f"无效的调度器: {name}")


if __name__ == '__main__':
    args = parse_args()
    scheduler = load_scheduler(args.scheduler)
    tsn = TSNNetwork(scheduler)
    tsn.run()