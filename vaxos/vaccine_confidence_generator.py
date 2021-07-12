
from vaxos.vaccine_simulator import VaccineSimulator

from vaxos.params import Params
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta
import numpy as np
import json, os
import time


def generate_confidence(scenario, num_runs):

    params_dict = Params().read_params()
    # scenario_list = Params().get_scenarios()

    # scenario_list = [
    #     "current_balanced_PZ_moh_dist_FortnightInvite_RR80_2WReserveBookingLimit",
    #     "current_balanced_PZ_moh_dist_FortnightInvite_RR80_Current",
    # ]

    # for scenario in scenario_list:
    # print(scenario)
    params = params_dict[scenario]
    params["randomised_demand"] = True ### NOTE IMPORTANT

    epoch = params['duration'] + params['second_shot_gap'] + params['max_second_shot_delay']

    results_dir = f"{os.getcwd()}/confidence/{params['name']}"
    os.makedirs(results_dir, exist_ok=True)

    x = [datetime.strftime(datetime.strptime(params['start_date'], "%Y-%m-%d") + relativedelta(days=d) , "%Y-%m-%d")
            for d in list(range(epoch))]

    confidence_total_df =  pd.DataFrame()
    confidence_first_df =  pd.DataFrame()
    confidence_second_df =  pd.DataFrame()

    for i in range(num_runs):
        simulator = VaccineSimulator(params)
        person_rank_df, occupancy_df = simulator.simulate()

        reset_occupancy = occupancy_df.reset_index(level=[0,1]).groupby('period').sum() / params['scale_factor']
        df = reset_occupancy[['first_shot', 'second_shot']].cumsum()[['first_shot', 'second_shot']]
        df['total'] = df['first_shot'] + df['second_shot']

        # try:
        #     confidence_total_df = pd.read_csv(f"results/{params['name']}/confidence_total.csv", index_col=0, header=0, names=list(range(epoch)))
        # except:
        #     confidence_total_df =  pd.DataFrame()
        # confidence_total_df = confidence_total_df.append(pd.DataFrame(data=np.transpose(df['total'].tolist()).reshape(-1, epoch)), ignore_index=True)
        # confidence_total_df.to_csv(f"results/{params['name']}/confidence_total.csv")

        # try:
        #     confidence_first_df = pd.read_csv(f"results/{params['name']}/confidence_first.csv", index_col=0, header=0, names=list(range(epoch)))
        # except:
        #     confidence_first_df =  pd.DataFrame()
        # confidence_first_df = confidence_first_df.append(pd.DataFrame(data=np.transpose(df['first_shot'].tolist()).reshape(-1, epoch)), ignore_index=True)
        # confidence_first_df.to_csv(f"results/{params['name']}/confidence_first.csv")

        # try:
        #     confidence_second_df = pd.read_csv(f"results/{params['name']}/confidence_second.csv", index_col=0, header=0, names=list(range(epoch)))
        # except:
        #     confidence_second_df =  pd.DataFrame()
        # confidence_second_df = confidence_second_df.append(pd.DataFrame(data=np.transpose(df['second_shot'].tolist()).reshape(-1, epoch)), ignore_index=True)
        # confidence_second_df.to_csv(f"results/{params['name']}/confidence_second.csv")

        confidence_total_df = confidence_total_df.append(pd.DataFrame(data=np.transpose(df['total'].tolist()).reshape(-1, len(df['total']))), ignore_index=True)
        confidence_first_df = confidence_first_df.append(pd.DataFrame(data=np.transpose(df['first_shot'].tolist()).reshape(-1, len(df['first_shot']))), ignore_index=True)
        confidence_second_df = confidence_second_df.append(pd.DataFrame(data=np.transpose(df['second_shot'].tolist()).reshape(-1, len(df['second_shot']))), ignore_index=True)

    seconds = time.time()


    confidence_total_df.to_csv(f"confidence/{params['name']}/confidence_total_{seconds}.csv")
    confidence_first_df.to_csv(f"confidence/{params['name']}/confidence_first_{seconds}.csv")
    confidence_second_df.to_csv(f"confidence/{params['name']}/confidence_second_{seconds}.csv")

    confidence_total_trace = generate_confidence_trace(confidence_total_df, x, epoch)
    confidence_first_trace = generate_confidence_trace(confidence_first_df, x, epoch)
    confidence_second_trace = generate_confidence_trace(confidence_second_df, x, epoch)

    data = [confidence_total_trace, confidence_first_trace, confidence_second_trace]
    confidence_fig = go.Figure(data)

    with open(f"confidence/{params['name']}/confidence_trace_{seconds}.json", "w") as img_json:
        json.dump(confidence_fig.to_json(), img_json)

    return confidence_total_df, confidence_first_df, confidence_second_df


def generate_confidence_trace(df, x, epoch, color='rgba(0,100,80,0.2)'):

    stats = df.agg(['mean', 'count', 'std'])
    stats = stats.transpose()
    ci_hi = [0]*epoch
    ci_lo = [0]*epoch

    for i in stats.index:
        ci_hi[int(i)] = np.percentile(df[i], 90)
        ci_lo[int(i)] = np.percentile(df[i], 10)

    stats['ci_hi'] = ci_hi
    stats['ci_lo'] = ci_lo

    y_upper = stats['ci_hi'].to_numpy().tolist()
    y_lower = stats['ci_lo'].to_numpy().tolist()
    confidence_trace = {
        "x": x+x[::-1], # x, then x reversed
        "y": y_upper+y_lower[::-1], # upper, then lower reversed
        "fill": 'toself',
        "fillcolor": color,
        "line": dict(color='rgba(255,255,255,0)'),
        "hoverinfo": "skip",
        "showlegend": False
    }

    return confidence_trace
