from .base import BaseScheduler
import time, os
from mininet.log import info

class Scheduler(BaseScheduler):
    def setup(self, net):
        info("*** 初始化智能调度器配置\n")
        base_time = int((time.time() + 5) * 1e9)

        s1_iface = 'ens160'
        s2_iface = 'ens192'

        for sw, iface in [(net.get('s1'), s1_iface), (net.get('s2'), s2_iface)]:
            try:
                # 清理旧配置
                del_result = sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
                if "RTNETLINK" in del_result:
                    info(f"!! {sw.name} 清理失败: {del_result}\n")

                # 修改 schedulers/enhanced.py 配置
                num_tc = 3  # 保持需求不变
                queues_config = "1@0 1@1 1@2 1@3"  # 兼容硬件支持（实际使用3tc但多分配一个队列）

                cmd = (
                    f"sudo tc qdisc replace dev {iface} root taprio "
                    f"num_tc {num_tc} "
                    f"map 0 0 0 0 1 1 1 1 2 2 2 2 0 0 0 0 "  # 16优先级映射
                    f"queues {queues_config} "  # 根据硬件队列调整
                    f"base-time {base_time} "
                    f"sched-entry S 01 300000 "
                    f"sched-entry S 02 600000 "
                    f"sched-entry S 04 100000 "
                    f"clockid CLOCK_REALTIME "
                    f"fp 0 1500 1 1500 2 1500 "
                    f"flags 0x0"
                )

                # 执行并检查
                info(f"正在配置 {sw.name} 的 {iface}...\n")
                result = sw.cmd(cmd + " 2>&1")

                if "Error" in result or "failed" in result.lower():
                    info(f"!! {sw.name} 配置失败: {result}\n")
                else:
                    info(f"++ {sw.name} 配置成功\n")
                    if result.strip():
                        info(f"   警告: {result.strip()}\n")

            except Exception as e:
                info(f"!! {sw.name} 异常: {str(e)}\n")

    def dynamic_update(self, net):
        info("*** 执行智能动态调整\n")
        # 这里可以添加网络状态监测和智能调整逻辑
        pass  # 实际实现需要具体业务逻辑

    def get_update_interval(self):
        return 10  # 更频繁的更新