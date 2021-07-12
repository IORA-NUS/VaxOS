from vaxos.vaccine_confidence_generator import generate_confidence
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
    # simulator = VaccineSimulator(params_dict[scenario])
    # person_rank, occupancy = simulator.simulate()
    # result = simulator.save()
    confidence_total_df, confidence_first_df, confidence_second_df = generate_confidence(scenario, 5)


if __name__ == '__main__':
    p = Pool(24)
    with p:
        for i in range(2):
            p.map(parallel_execution, scenario_list)
            time.sleep(0.1)

# for scenario in scenario_list:
#     print(scenario)
#     # simulator = VaccineSimulator(params_dict[scenario])
#     # person_rank, occupancy = simulator.simulate()
#     # result = simulator.save()

#     proc = threading.Thread(target=parallel_execution, args=(scenario,))
#     proc.start()

