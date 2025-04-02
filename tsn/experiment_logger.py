# tsn/experiment_logger.py
import csv
import os
import time

CSV_HEADER = ['timestamp', 'scheduler_name', 'cycle_time', 'sched_entries', 'extra_metrics']


def ensure_csv_file(filename):
    """
    如果文件不存在，则创建文件并写入标题行。
    """
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(CSV_HEADER)


def log_experiment_data(filename, timestamp, scheduler_name, cycle_time, sched_entries, extra_metrics):
    """
    将实验数据记录到 CSV 文件中。

    参数：
      - filename: CSV 文件名，例如 'experiment_data.csv'
      - timestamp: 当前时间戳
      - scheduler_name: 使用的 GCL 算法名称
      - cycle_time: GCL 周期（单位：纳秒）
      - sched_entries: GCL 调度表字符串
      - extra_metrics: 其他性能指标（例如延迟、抖动信息）
    """
    ensure_csv_file(filename)

    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, scheduler_name, cycle_time, sched_entries, extra_metrics])


def measure_network_performance(net, source_host="h1", target_host="h3", timeout=1):
    """
    通过 Mininet 内部的主机命令采集目标主机的时延数据。

    参数：
      - net: Mininet 网络对象
      - source_host: 发起 ping 命令的源主机名称（默认为 "h1"）
      - target_host: 目标主机名称（默认为 "h3"）
      - timeout: ping 超时时间（秒）

    返回：
      - 成功时返回 "latency=XXms"，失败时返回错误信息字符串。
    """
    try:
        src = net.get(source_host)
        tgt = net.get(target_host)
        # 使用 Mininet 主机对象的 cmd 方法执行 ping 命令
        result = src.cmd("ping -c 1 -W {} {}".format(timeout, tgt.IP()))
        if result and "time=" in result:
            # 解析输出中包含 "time=XX ms" 的部分
            for line in result.splitlines():
                if "time=" in line:
                    try:
                        latency_part = line.split("time=")[1]
                        latency_str = latency_part.split()[0]
                        return f"latency={latency_str}ms"
                    except Exception as e:
                        return f"latency_parse_error: {str(e)}"
            return "latency_no_data"
        else:
            return f"latency_error: {result.strip()}"
    except Exception as e:
        return f"latency_exception: {str(e)}"


if __name__ == '__main__':
    # 简单测试日志记录和测量功能。需要手动构建或导入一个 Mininet 对象进行测试。
    # 这里仅作为示例，实际测试时请确保 net 对象已正确初始化并包含主机 h1 和 h3。
    from mininet.net import Mininet
    from mininet.node import Controller, Host
    from mininet.link import TCLink

    net = Mininet(controller=Controller, link=TCLink)
    c0 = net.addController('c0')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    net.addLink(h1, h3)
    net.build()
    c0.start()
    h1.cmd("ifconfig h1-eth0 10.0.0.1/24")
    h3.cmd("ifconfig h3-eth0 10.0.0.3/24")

    extra_metrics = measure_network_performance(net, source_host="h1", target_host="h3")
    print("测得性能数据:", extra_metrics)

    # 记录一次实验数据
    log_file = "experiment_data.csv"
    timestamp = time.time()
    scheduler_name = "HeuristicGCLScheduler"
    cycle_time = 200000
    sched_entries = "sched-entry S 01 60000 sched-entry S 01 70000 sched-entry S 10 60000"

    log_experiment_data(log_file, timestamp, scheduler_name, cycle_time, sched_entries, extra_metrics)
    print("实验数据记录完毕")

    net.stop()
