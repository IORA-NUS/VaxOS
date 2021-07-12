import os, sys
current_path = os.path.abspath('.')
parent_path = os.path.dirname(current_path)
sys.path.append(parent_path)

from vaxos.vaccine_simulator import VaccineSimulator
import plotly.express as px
import plotly.graph_objects as go
import threading
import multiprocessing as mp
from multiprocessing import Pool

from vaxos.params import Params


params_dict = Params().read_params()

scenario_list = [

    # 'paper_holdback_supply95_BL-None_INV-None_Risk-0W_Strategy-First_W-0_Pref-random0',
    # 'paper_holdback_supply100_BL-None_INV-None_Risk-0W_Strategy-First_W-0_Pref-random0',

    # 'paper_lambda_1_0WRisk_supply100_BL-lp_INV-None_Risk-0W_Strategy-First_W-1_Pref-random0',
    'paper_lambda_1_1WRisk_supply100_BL-lp_INV-None_Risk-1W_Strategy-First_W-1_Pref-random0',

]

def parallel_execution(scenario):
    print(scenario)
    simulator = VaccineSimulator(params_dict[scenario])
    person_rank, occupancy = simulator.simulate()
    result = simulator.save()


if __name__ == '__main__':
    p = Pool(24)
    with p:
        p.map(parallel_execution, scenario_list)

