from .base import BaseScheduler
import time, os, random
from mininet.log import info

class Scheduler(BaseScheduler):
    def setup(self, net):
        info("*** 初始化默认调度器配置\n")
        base_time = int((time.time() + 5) * 1e9)
        for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
            sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
            cmd = (
                f"sudo tc qdisc replace dev {iface} root taprio "
                f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
                f"queues 1@0 1@1 "
                f"base-time {base_time} "
                f"sched-entry S 01 500000 "
                f"sched-entry S 10 500000 "
                f"clockid CLOCK_REALTIME "
                f"flags 0x0"
            )
            sw.cmd(cmd)

    def dynamic_update(self, net):
        info("*** 执行默认动态更新\n")
        for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
            base_time = int((time.time() + 5) * 1e9)
            cycle_time = 1000000  # 1ms
            entries = [
                f"sched-entry S {'01' if random.random() > 0.5 else '10'} {500000}",
                f"sched-entry S {'10' if random.random() > 0.5 else '01'} {500000}"
            ]
            cmd = (
                f"sudo tc qdisc replace dev {iface} root taprio "
                f"base-time {base_time} "
                f"{' '.join(entries)} "
                f"clockid CLOCK_REALTIME"
            )
            sw.cmd(cmd)

    def get_update_interval(self):
        return 20  # 默认调度器20秒更新