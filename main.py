# main.py
import argparse
from tsn.topology import create_tsn_topo
from tsn.gcl_scheduler.heuristic import HeuristicGCLScheduler


# 如果后续增加其他算法，也可在此导入对应模块

def parse_args():
    parser = argparse.ArgumentParser(description="TSN GCL Scheduler Selection")
    parser.add_argument(
        '--gcl',
        type=str,
        default='heuristic',
        help="选择 GCL 算法，例如 'heuristic'（默认）"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.gcl == 'heuristic':
        scheduler = HeuristicGCLScheduler(cycle_time=200000)
    else:
        print(f"未识别的 GCL 算法 '{args.gcl}'，使用默认 'heuristic'")
        scheduler = HeuristicGCLScheduler(cycle_time=200000)

    create_tsn_topo(scheduler)
