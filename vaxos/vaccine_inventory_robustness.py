
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


def inventory_robustness(scenario, num_runs=5, num_supply_runs=500):

    params_dict = Params().read_params()

    # num_runs = 5
    # num_supply_runs = 500

    params = params_dict[scenario]
    params["randomised_demand"] = True ### NOTE IMPORTANT
    # params["demand_generator"] = 'Invited' ### NOTE IMPORTANT

    longest_epoch = 0
    for vac in vaccine_types:

        if longest_epoch < params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']:
            longest_epoch = params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']

    supply_expiry = SupplyExpiry(params['supply_scenario_display'])

    supply = supply_expiry.get_supply_vector(params['start_date'], longest_epoch, state='Supply', vaccine='All', cumulative=True, include_init=True)

    stats_df = pd.DataFrame()

    idx = 0

    for i in range(num_runs):

        simulator = VaccineSimulator(params)
        person_rank_df, occupancy_df = simulator.simulate()

        reset_occupancy = occupancy_df.reset_index(level=[0,1]).groupby('period').sum() / params['scale_factor']

        reset_occupancy = occupancy_df.reset_index(level=[0,1]).groupby('period').sum() / params['scale_factor']

        for vac in vaccine_types:
            _, second_appts, _ = Params.get_appt_book(params, vac)
            curr_appt_second_sum = second_appts[0:longest_epoch]

            reset_occupancy['second_shot'] = reset_occupancy['second_shot'] + (curr_appt_second_sum + ([0]*(len(reset_occupancy) - len(curr_appt_second_sum))))


        df = reset_occupancy[['first_shot', 'second_shot']].cumsum()[['first_shot', 'second_shot']]
        df['total'] = df['first_shot'] + df['second_shot']

        for j in range(num_supply_runs):
            noisy_supply = supply_expiry.get_perturbed_supply(supply)

            inventory = np.array(noisy_supply + ([noisy_supply[-1]] * (len(df['total']) - len(noisy_supply)))) - np.array(df['total'].tolist())

            stats_df[idx] = inventory
            idx += 1


        fig = go.Figure()

        t_stats_df = stats_df.transpose()
        cseq = ['rgb(217, 95, 2)' if i < 0 else 'rgb(27, 158, 119)' for i in t_stats_df.quantile(0.1)]

        for col in list(range(95)):
            fig.add_trace(go.Box(y=t_stats_df[col], name=col, marker={'color': cseq[col]}, boxpoints=False))

        fig.update_layout(showlegend=False, xaxis={'showticklabels': True}, title_text='Inventory (90% confidence) under uncertainty')

        fig.add_annotation(
            showarrow=False,
            text=scenario,
            xref="paper", yref="paper",
            xanchor='right',
            x=1,
            yanchor='top',
            y=-0.15
        )

        results_dir = f"{os.getcwd()}/results/{scenario}"
        # confidence_dir = f"{os.getcwd()}/confidence/{scenario}"
        os.makedirs(results_dir, exist_ok=True)

        fig.write_image(f"{results_dir}/inventory_robustness.png")
        stats_df.to_csv(f"{results_dir}/inventory_robustness_stats.csv")

        with open(f"{results_dir}/inventory_robustness.json", "w") as img_json:
            json.dump(fig.to_json(), img_json)


    # seconds = time.time()

