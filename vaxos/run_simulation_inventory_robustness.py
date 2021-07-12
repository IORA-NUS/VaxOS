import os, sys
current_path = os.path.abspath('.')
parent_path = os.path.dirname(current_path)
sys.path.append(parent_path)

from vaxos.vaccine_inventory_robustness import inventory_robustness

import plotly.express as px
import plotly.graph_objects as go
import threading
import multiprocessing as mp
from multiprocessing import Pool
import time

from vaxos.params import Params


params_dict = Params().read_params()
scenario_list = [

]

def parallel_execution(scenario):
    print(scenario)
    inventory_robustness(scenario)

if __name__ == '__main__':
    p = Pool(24)
    with p:
        # for i in range(2):
        p.map(parallel_execution, scenario_list)
        time.sleep(0.1)

# for scenario in scenario_list:
#     print(scenario)
#     # simulator = VaccineSimulator(params_dict[scenario])
#     # person_rank, occupancy = simulator.simulate()
#     # result = simulator.save()

#     proc = threading.Thread(target=parallel_execution, args=(scenario,))
#     proc.start()

