# tsn/taprio_config.py
import time

def config_taprio(net):
    base_time = int((time.time() + 5) * 1e9)  # Take effect in 5 seconds
    for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
        # Clear old configuration
        sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
        # Configure the new taprio
        cmd = (
            f"sudo tc qdisc replace dev {iface} root taprio "
            f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
            f"queues 1@0 1@1 "
            f"base-time {base_time} "
            f"sched-entry S 01 500000 "  # 500us open TC0
            f"sched-entry S 10 500000 "  # 500us open TC1
            f"clockid CLOCK_REALTIME "   # Using the system clock
            f"flags 0x0"
        )
        sw.cmd(cmd)
