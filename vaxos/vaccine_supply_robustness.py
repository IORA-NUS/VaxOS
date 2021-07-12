
from vaxos.vaccine_simulator import VaccineSimulator
from vaxos.supply_expiry import SupplyExpiry

from vaxos.params import Params, vaccine_types
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta
import numpy as np
import json, os
import time
from random import random


class SupplyRobustness:
    def __init__(self, scenario):

        self.scenario = scenario
        params_dict = Params().read_params()

        # num_runs = 5
        # num_supply_runs = 500

        self.params = params_dict[scenario]
        # self.params["randomised_demand"] = True ### NOTE IMPORTANT
        # self.params["scale_factor"] = 0.05 ### NOTE IMPORTANT


        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.results_dir = f"{dir_path}/results/{self.scenario}"
        os.makedirs(self.results_dir, exist_ok=True)

        summary_df = pd.DataFrame(columns=[
            'Name',
            'Total TPut',
            'Booked Appt',
            'Missed Appt',
            'Spillover Appt',
            'Waiting Time',
            'Appt Waiting Time',
        ])

        try:
            summary_df = pd.read_csv(f"{self.results_dir}/supply_robustness_stats.csv")
        except:
            summary_df.to_csv(f"{self.results_dir}/supply_robustness_stats.csv", index=False)

        # self.simulator = VaccineSimulator(self.params)


    def run_instance(self, idx):

        # idx = 0

        simulator = VaccineSimulator(self.params)
        person_rank_df, occupancy_df = simulator.simulate()
        summary_stat = {}

        stats = simulator.stats

        summary_stat['Name'] = self.params['name']
        summary_stat['Total TPut'] = stats['Total Throughput'] / self.params['scale_factor']
        summary_stat['Booked Appt'] = stats['Booked Appointments']['All'] / self.params['scale_factor']
        summary_stat['Missed Appt'] = stats['Missed Appointments']['All'] / self.params['scale_factor']
        summary_stat['Spillover Appt'] = stats['Spillover Appointments'] / self.params['scale_factor']
        summary_stat['Waiting Time'] = stats['Avg Waiting Time (Missed appts == Max Wait)']['All']
        summary_stat['Appt Waiting Time'] = stats['Avg Appt Waiting Time (Missed appts == Max Wait)']['All']

        time.sleep(random() * 3)
        summary_df = pd.read_csv(f"{self.results_dir}/supply_robustness_stats.csv")
        summary_df = summary_df.append(summary_stat, ignore_index=True)
        summary_df.to_csv(f"{self.results_dir}/supply_robustness_stats.csv", index=False)

        print(summary_df)
