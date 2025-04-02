import threading
import time
from mininet.log import info

class BaseScheduler:
    def setup(self, net):
        """抽象方法：初始化网络调度配置"""
        raise NotImplementedError

    def dynamic_update(self, net):
        """抽象方法：动态更新逻辑"""
        raise NotImplementedError

    def start_dynamic_update(self, net):
        """启动动态更新线程"""
        self._stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._update_loop,
            args=(net,),
            daemon=True
        )
        self.thread.start()

    def _update_loop(self, net):
        """通用的更新循环"""
        while not self._stop_event.is_set():
            try:
                self.dynamic_update(net)
            except Exception as e:
                info(f"!! 调度器错误: {str(e)}\n")
            time.sleep(self.get_update_interval())

    def get_update_interval(self):
        """获取更新间隔（子类可覆盖）"""
        return 30  # 默认30秒

    def stop(self):
        """停止调度器"""
        self._stop_event.set()
        self.thread.join()