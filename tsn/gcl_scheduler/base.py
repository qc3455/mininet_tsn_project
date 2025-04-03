# tsn/gcl_scheduler/base.py
from abc import ABC, abstractmethod

class GCLScheduler(ABC):
    @abstractmethod
    def generate_gcl(self):
        """
        Generate GCL configuration.
        Returns: Scheduling table string and period (unit: ns)
        """
        pass
