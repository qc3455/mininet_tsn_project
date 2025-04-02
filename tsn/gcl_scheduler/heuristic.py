# tsn/gcl_scheduler/heuristic.py
import random
from tsn.gcl_scheduler.base import GCLScheduler

class HeuristicGCLScheduler(GCLScheduler):
    def __init__(self, cycle_time=200000):
        self.cycle_time = cycle_time  # 固定周期（纳秒）

    def generate_gcl(self):
        cycle_time = self.cycle_time
        n_slots = 3  # 总共生成3个时间槽
        min_duration = 50000  # 每个时间槽的最小时长（纳秒）
        entries = []
        remaining = cycle_time

        for i in range(n_slots - 1):
            # 保证剩余时间满足后续槽的最小值要求
            max_possible = remaining - (n_slots - i - 1) * min_duration
            duration = random.randint(min_duration, max_possible)
            gate_state = random.choice(["01", "10"])
            entries.append(f"sched-entry S {gate_state} {duration}")
            remaining -= duration

        # 最后一个时间槽直接使用剩余时间
        gate_state = random.choice(["01", "10"])
        entries.append(f"sched-entry S {gate_state} {remaining}")

        total = sum(int(e.split()[-1]) for e in entries)
        assert total == cycle_time, f"周期不匹配 {total} vs {cycle_time}"
        return " ".join(entries), cycle_time
