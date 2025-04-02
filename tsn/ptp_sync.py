# tsn/ptp_sync.py
import time
from mininet.log import info

def setup_ptp_sync(net):
    info("*** 配置软件PTP同步\n")
    ptp_conf = """
                [global]
                tx_timestamp_timeout 100
                logSyncInterval 0
                syncReceiptTimeout 3
                neighborPropDelayThresh 800
                min_neighbor_prop_delay -20000000
                """
    # 主节点配置（h1）
    h1 = net.get('h1')
    h1.cmd("echo '%s' > /tmp/ptp.conf" % ptp_conf)
    h1.cmd("sudo ptp4l -i h1-eth0 -m -S -f /tmp/ptp.conf --socket_priority=0 > /tmp/ptp_master.log 2>&1 &")
    h1.cmd("sudo phc2sys -m -s h1-eth0 -c CLOCK_REALTIME -O 0 -u 1 > /tmp/phc2sys_master.log 2>&1 &")

    # 从节点配置
    for node in [net.get('s1'), net.get('s2'), net.get('h2'), net.get('h3')]:
        intf = node.intfList()[0].name
        node.cmd("echo '%s' > /tmp/ptp.conf" % ptp_conf)
        node.cmd(f"sudo ptp4l -i {intf} -m -S -f /tmp/ptp.conf -s --socket_priority=0 > /tmp/ptp_slave.log 2>&1 &")
        node.cmd(f"sudo phc2sys -m -s {intf} -c CLOCK_REALTIME -O 0 -u 1 > /tmp/phc2sys_slave.log 2>&1 &")
    time.sleep(8)  # 等待同步完成
