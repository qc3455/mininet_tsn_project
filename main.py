# main.py
import argparse
from tsn.topology import create_tsn_topo
from tsn.gcl_scheduler.heuristic import HeuristicGCLScheduler



def parse_args():
    parser = argparse.ArgumentParser(description="TSN GCL Scheduler Selection")
    parser.add_argument(
        '--gcl',
        type=str,
        default='heuristic',
        help="Select a GCL algorithm, such as 'heuristic' (default)"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.gcl == 'heuristic':
        scheduler = HeuristicGCLScheduler(cycle_time=200000)
    else:
        print(f"Unidentified GCL algorithm '{args.gcl}'，Use default 'heuristic'")
        scheduler = HeuristicGCLScheduler(cycle_time=200000)

    create_tsn_topo(scheduler)
