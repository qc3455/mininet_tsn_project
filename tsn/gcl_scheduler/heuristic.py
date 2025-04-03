# tsn/gcl_scheduler/heuristic.py
import random
from tsn.gcl_scheduler.base import GCLScheduler

class HeuristicGCLScheduler(GCLScheduler):
    def __init__(self, cycle_time=200000):
        self.cycle_time = cycle_time  # Fixed period (nanoseconds)

    def generate_gcl(self):
        cycle_time = self.cycle_time
        n_slots = 3
        min_duration = 50000  # The minimum duration of each time slot (nanoseconds)
        entries = []
        remaining = cycle_time

        for i in range(n_slots - 1):
            # Ensure that the remaining time meets the minimum requirements for subsequent time slots.
            max_possible = remaining - (n_slots - i - 1) * min_duration
            duration = random.randint(min_duration, max_possible)
            gate_state = random.choice(["01", "10"])
            entries.append(f"sched-entry S {gate_state} {duration}")
            remaining -= duration

        # Use the remaining time directly for the last time slot.
        gate_state = random.choice(["01", "10"])
        entries.append(f"sched-entry S {gate_state} {remaining}")

        total = sum(int(e.split()[-1]) for e in entries)
        assert total == cycle_time, f"The periods do not match {total} vs {cycle_time}"
        return " ".join(entries), cycle_time
