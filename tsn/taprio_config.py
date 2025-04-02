# tsn/taprio_config.py
import time

def config_taprio(net):
    """初始软件友好型配置"""
    base_time = int((time.time() + 5) * 1e9)  # 5秒后生效
    for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
        # 清除旧配置
        sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
        # 配置新的 taprio
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
