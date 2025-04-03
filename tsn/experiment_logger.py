# tsn/experiment_logger.py
import csv
import os
import time
import subprocess
import statistics


CSV_HEADER = ['timestamp', 'scheduler_name', 'latency', 'jitter', 'schedule_adherence']


def ensure_csv_file(filename):

    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(CSV_HEADER)


def log_experiment_data(filename, timestamp, scheduler_name, latency, jitter, schedule_adherence):
    """
    Record the experimental data into a CSV file, recording only the core indicators:
    - timestamp: sampling time
    - scheduler_name: the name of the GCL algorithm used
    - latency: end-to-end latency (ms)
    - jitter: latency jitter (ms)
    - schedule_adherence: scheduling accuracy (the difference between the expected effective time and the actual time, in nanoseconds)
    """
    ensure_csv_file(filename)
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, scheduler_name, latency, jitter, schedule_adherence])


def measure_latency_jitter(net, source_host="h1", target_host="h3", count=5, timeout=1):
    """
    Use the ping command inside Mininet to collect multiple latency data and calculate the average latency and jitter (average absolute deviation of adjacent differences).

    Parameters:
    - net: Mininet network object
    - source_host: source host name of the ping
    - target_host: target host name
    - count: number of pings (default 5 times)
    - timeout: ping timeout (seconds)

    Return:
    - (avg_latency, jitter) For example ("0.081ms", "0.005ms")
    - If failed, an error string is returned
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
    Simple measurement of scheduling accuracy: by comparing the expected effective time with the current time difference (in nanoseconds) collected after the configuration command is executed.

    Parameters:
    - expected_base_time: expected effective time of GCL configuration (in nanoseconds)

    Returns:
    - schedule_adherence: absolute error, in nanoseconds
    """
    actual_time = int(time.time() * 1e9)
    adherence = abs(actual_time - expected_base_time)
    return adherence


if __name__ == '__main__':
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

    # Measuring latency and jitter
    latency, jitter = measure_latency_jitter(net, source_host="h1", target_host="h3", count=5)
    print("Latency:", latency, "Jitter:", jitter)

    # Simulate the expected effective time (for example, delay the current time by 5 seconds, in nanoseconds)
    expected_base_time = int((time.time() + 5) * 1e9)
    schedule_adherence = measure_schedule_adherence(expected_base_time)
    print("Scheduling accuracy (error in nanoseconds):", schedule_adherence)


    log_file = "experiment_data.csv"
    timestamp = time.time()
    scheduler_name = "HeuristicGCLScheduler"
    log_experiment_data(log_file, timestamp, scheduler_name, latency, jitter, schedule_adherence)
    print("Experimental data recording completed")

    net.stop()
