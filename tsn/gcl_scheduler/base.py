# tsn/gcl_scheduler/base.py
from abc import ABC, abstractmethod

class GCLScheduler(ABC):
    @abstractmethod
    def generate_gcl(self):
        """
        生成 GCL 配置。
        返回：调度表字符串和周期（单位：ns）
        """
        pass
