import numpy as np


def analyze_results():
    with open('results.txt') as f:
        timestamps = [int(line.strip()) for line in f]

    send_times = timestamps[::2]
    recv_times = timestamps[1::2]

    delays = [(r - s) / 1e6 for s, r in zip(send_times, recv_times)]

    print(f"平均延迟: {np.mean(delays):.3f}ms")
    print(f"最大延迟: {np.max(delays):.3f}ms")
    print(f"延迟抖动: {np.std(delays):.3f}ms")

    # 检测时间偏差是否符合CQF周期
    periods = np.diff([t // 300000 for t in recv_times])
    print(f"周期一致性: {np.unique(periods)}")


if __name__ == '__main__':
    analyze_results()