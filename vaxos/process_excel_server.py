import os
import time
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor

from vaxos.excel_scenario_loader import ExcelScenarioLoader

def process_excel_server():

    executor = ProcessPoolExecutor()

    dir_path = os.path.dirname(os.path.realpath(__file__)) + "/inputs/excel"

    # print(f'Listening for excel files at {dir_path}')

    # while True:
    #     # scenarios = [f for f in os.listdir(dir_path) if (f.find('params') >= 0 and f.find('.json') >= 0)]
    #     scenarios = [f for f in os.listdir(dir_path) if f.find('.xlsx') >= 0]

    #     for scenario in scenarios:
    #         print(f'Executing {scenario}')
    #         excel_loader = ExcelScenarioLoader(scenario)
    #         # excel_loader.run_all()
    #         p = Process(target=excel_loader.run_all)
    #         p.start()
    #         p.join(5)

    #         print(f'Started {scenario} in a new Process')

    #         # time.sleep(5)

    scenarios = [f for f in os.listdir(dir_path) if f.find('.xlsx') >= 0]

    for scenario in scenarios:
        excel_loader = ExcelScenarioLoader(scenario)
        future = executor.submit(excel_loader.run_all)

        print(future.result())
        print(f'Started {scenario} in a new Process')


if __name__ == '__main__':
    process_excel_server()
