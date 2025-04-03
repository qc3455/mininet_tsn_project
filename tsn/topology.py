# tsn/topology.py
import time
import os
import threading
from mininet.net import Mininet
from mininet.node import Controller, Host
from mininet.nodelib import LinuxBridge
from mininet.link import Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from tsn.ptp_sync import setup_ptp_sync
from tsn.taprio_config import config_taprio
from tsn.gcl_scheduler.heuristic import HeuristicGCLScheduler
from tsn.experiment_logger import log_experiment_data, measure_latency_jitter, measure_schedule_adherence


def load_kernel_modules():
    for m in ['sch_taprio', 'ptp']:
        os.system(f"sudo modprobe {m} || true")


def create_tsn_topo(scheduler):
    setLogLevel('info')
    net = Mininet(controller=Controller, switch=LinuxBridge, host=Host)
    c0 = net.addController('c0')

    # Add a switch and bind a physical network card
    s1 = net.addSwitch('s1')
    Intf('ens160', node=s1)  # Bind physical network card ens160

    s2 = net.addSwitch('s2')
    Intf('ens192', node=s2)  # Bind physical network card ens192

    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s1, s2)
    net.addLink(s2, h3)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])

    load_kernel_modules()
    setup_ptp_sync(net)
    config_taprio(net)

    # Start the dynamic GCL update thread, passing in the selected scheduler object
    update_thread = threading.Thread(target=dynamic_gcl_update, args=(net, scheduler))
    update_thread.daemon = True
    update_thread.start()

    CLI(net)
    net.stop()


def dynamic_gcl_update(net, scheduler, log_file='experiment_data.csv'):
    scheduler_name = type(scheduler).__name__
    while True:
        time.sleep(30)
        info("\n*** Performing GCL Updates...\n")
        try:
            sched_entries, cycle_time = scheduler.generate_gcl()
            base_time = int((time.time() + 5) * 1e9)  # Delay 5 seconds to take effect

            # Measuring Latency and Jitter
            latency, jitter = measure_latency_jitter(net, source_host="h1", target_host="h3", count=5)
            # Measuring schedule accuracy (expected effective time is base_time)
            schedule_adherence = measure_schedule_adherence(base_time)

            # configuration updates for each switch
            for sw, iface in [(net.get('s1'), 'ens160'), (net.get('s2'), 'ens192')]:
                sw.cmd(f"sudo tc qdisc del dev {iface} root 2>/dev/null; true")
                cmd = (
                    f"sudo tc qdisc add dev {iface} root taprio "
                    f"num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 "
                    f"queues 1@0 1@1 "
                    f"base-time {base_time} "
                    f"{sched_entries} "
                    f"clockid CLOCK_REALTIME "
                    f"flags 0x0"
                )
                result = sw.cmd(cmd + " 2>&1")
                if "Error" in result:
                    info(f"!! Error updating {sw.name}: {result}\n")
                else:
                    info(f"++ GCL update for {sw.name} takes effect at {time.ctime(base_time / 1e9)}\n"
                         f"   Cycle time: {cycle_time}ns, Scheduling table: {sched_entries}\n")

            # Record data into the CSV file
            extra_metrics = "Other custom information"
            # log_experiment_data(log_file, time.time(), scheduler_name, cycle_time,
            #                     sched_entries, latency, jitter, schedule_adherence, extra_metrics)
            log_experiment_data(log_file, time.time(), scheduler_name, latency, jitter, schedule_adherence)

        except Exception as e:
            info(f"!! Exception occurred during dynamic update: {str(e)}\n")