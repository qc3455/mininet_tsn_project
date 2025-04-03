# tsn/experiment_logger.py
import csv
import os
import time
import subprocess
import statistics

# 只保留核心字段
CSV_HEADER = ['timestamp', 'scheduler_name', 'latency', 'jitter', 'schedule_adherence']


def ensure_csv_file(filename):
    """
    如果文件不存在，则创建文件并写入标题行。
    """
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(CSV_HEADER)


def log_experiment_data(filename, timestamp, scheduler_name, latency, jitter, schedule_adherence):
    """
    将实验数据记录到 CSV 文件中，只记录核心指标：
      - timestamp: 采样时间
      - scheduler_name: 使用的 GCL 算法名称
      - latency: 端到端延迟（ms）
      - jitter: 延迟抖动（ms）
      - schedule_adherence: 调度准确性（预期生效时间与实际时间的误差，单位纳秒）
    """
    ensure_csv_file(filename)
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, scheduler_name, latency, jitter, schedule_adherence])


def measure_latency_jitter(net, source_host="h1", target_host="h3", count=5, timeout=1):
    """
    通过在 Mininet 内部使用 ping 命令采集多次延迟数据，并计算平均延迟和抖动（相邻差值的平均绝对偏差）。

    参数：
      - net: Mininet 网络对象
      - source_host: 发起 ping 的源主机名称
      - target_host: 目标主机名称
      - count: ping 的次数（默认5次）
      - timeout: ping 超时时间（秒）

    返回：
      - (avg_latency, jitter) 例如 ("0.081ms", "0.005ms")
      - 若失败，则返回错误提示字符串
    """
    latencies = []
    src = net.get(source_host)
    tgt = net.get(target_host)
    for i in range(count):
        result = src.cmd("ping -c 1 -W {} {}".format(timeout, tgt.IP()))
        if result and "time=" in result:
            for line in result.splitlines():
                if "time=" in line:
                    try:
                        latency_str = line.split("time=")[1].split()[0]
                        latency = float(latency_str)
                        latencies.append(latency)
                    except Exception as e:
                        print(f"Latency parse error: {e}")
        else:
            print("Ping error:", result.strip())
    if not latencies:
        return ("latency_error", "jitter_error")

    avg_latency = statistics.mean(latencies)
    if len(latencies) > 1:
        diffs = [abs(latencies[i] - latencies[i - 1]) for i in range(1, len(latencies))]
        jitter_val = statistics.mean(diffs)
    else:
        jitter_val = 0.0
    return (f"{avg_latency:.3f}ms", f"{jitter_val:.3f}ms")


def measure_schedule_adherence(expected_base_time):
    """
    简单测量调度准确性：通过对比预期生效时间与配置命令执行后采集的当前时间差值（单位纳秒）。

    参数：
      - expected_base_time: GCL 配置的预期生效时间（纳秒）

    返回：
      - schedule_adherence: 绝对误差，单位纳秒
    """
    actual_time = int(time.time() * 1e9)
    adherence = abs(actual_time - expected_base_time)
    return adherence


if __name__ == '__main__':
    # 测试部分（构建简单 Mininet 拓扑）
    from mininet.net import Mininet
    from mininet.node import Controller
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

    # 测量延迟和抖动
    latency, jitter = measure_latency_jitter(net, source_host="h1", target_host="h3", count=5)
    print("延迟:", latency, "抖动:", jitter)

    # 模拟一个预期生效时间（例如当前时间延后5秒，单位纳秒）
    expected_base_time = int((time.time() + 5) * 1e9)
    schedule_adherence = measure_schedule_adherence(expected_base_time)
    print("调度准确性（误差纳秒）:", schedule_adherence)

    # 记录一次实验数据
    log_file = "experiment_data.csv"
    timestamp = time.time()
    scheduler_name = "HeuristicGCLScheduler"
    log_experiment_data(log_file, timestamp, scheduler_name, latency, jitter, schedule_adherence)
    print("实验数据记录完毕")

    net.stop()
