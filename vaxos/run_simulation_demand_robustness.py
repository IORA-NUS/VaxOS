# from vaccine_demand_robustness import demand_robustness
from vaxos.vaccine_demand_robustness import DemandRobustness

import plotly.express as px
import plotly.graph_objects as go
import threading
import multiprocessing as mp
from multiprocessing import Pool
import time

from vaxos.params import Params


scenario = ''

if __name__ == '__main__':
    p = Pool(24)

    demand_robustness = DemandRobustness(scenario)
    with p:
        # for i in range(2):
        p.map(demand_robustness.run_instance, range(5))
        time.sleep(0.1)

