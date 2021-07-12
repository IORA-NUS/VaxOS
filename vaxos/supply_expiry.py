
import plotly
import plotly.express as px
import plotly.graph_objects as go

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import math, json, os
import numpy as np
from numpy.random import normal, randint


class SupplyExpiry:

    def __init__(self, scenario='Actual', confidence=None):
        self.scenario = scenario

        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.supply_expiry_df = pd.read_csv(f'{dir_path}/inputs/supply/{scenario}.csv', parse_dates=['Supply', 'Expiry', 'Dwell',])

        self.supply_expiry_df["cum_Supply"] = self.supply_expiry_df.sort_values(by=['Supply'])["Quantity"].cumsum()
        self.supply_expiry_df["cum_Expiry"] = self.supply_expiry_df.sort_values(by=['Expiry'])["Quantity"].cumsum()
        self.supply_expiry_df["cum_Dwell"] = self.supply_expiry_df.sort_values(by=['Dwell'])["Quantity"].cumsum()

    def get_supply_vector(self, start_date_str, length, state, vaccine, cumulative=True, include_init=True):

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        vector = [0] * length
        for days in range(length):
            new_dt = start_date + relativedelta(days=days)

            supply_expiry_data = self.supply_expiry_df
            if vaccine != 'All':
                if include_init == True:
                    supply_expiry_data = supply_expiry_data[supply_expiry_data['Maker'].isin([vaccine, f'{vaccine}_Init'])]
                else:
                    supply_expiry_data = supply_expiry_data[supply_expiry_data['Maker'] == vaccine]
            else:
                if include_init == True:
                    pass
                else:
                    supply_expiry_data = supply_expiry_data[~(supply_expiry_data['Maker'].str.contains('Init'))]


            value = 0
            # supply_expiry_data.sort_values(by=[state], inplace=True, ignore_index=True)
            # supply_expiry_data[f"cum_{state}"] = supply_expiry_data["Quantity"].cumsum()
            supply_expiry_data[f"cum_{state}"] = supply_expiry_data.sort_values(by=[state])["Quantity"].cumsum()
            # supply_expiry_data[f"cum_{state}"] = supply_expiry_data["Quantity"].cumsum()
            for idx, row in supply_expiry_data.sort_values([state]).iterrows():
                if cumulative == True:
                    if row[state] <= new_dt:
                        value = row[f'cum_{state}']
                    else:
                        break
                else:
                    if row[state] == new_dt:
                        value += row[f'Quantity']

            vector[days] = value

        return vector

    def get_vaccine_consumed(self):
        return self.vaccine_consumed

    def get_supply_expiry_figure(self, start_date_str, length, vaccine, cumulative=True, include_init=True, x_axis='date'):

        supply = self.get_supply_vector(start_date_str, length, 'Supply', vaccine=vaccine, cumulative=cumulative, include_init=include_init)

        if x_axis == 'date':
            x = [datetime.strftime(datetime.strptime(start_date_str, "%Y-%m-%d") + relativedelta(days=d) , "%Y-%m-%d") for d in list(range(length))]
        else:
            x = list(range(length))

        confidence_trace = self.get_confidence_trace(start_date_str, length, vaccine)


        supply_trace = {
        # "x": self.supply_expiry_df.sort_values(by=['Supply'])['Supply'],
        # "y": self.supply_expiry_df.sort_values(by=['Supply'])["cum_Supply"],
        # "line": {"shape": 'hv', "color": "black",},
        "x": x, #self.supply_expiry_df.sort_values(by=['Supply'])['Supply'],
        "y": supply, #self.supply_expiry_df.sort_values(by=['Supply'])["cum_Supply"],
        "line": { "color": "black",},
        "mode": 'lines',
        "name": 'Supply',
        "type": 'scatter',
        }

        expiry_trace = {
        "x": self.supply_expiry_df.sort_values(by=['Expiry'])['Expiry'],
        "y": self.supply_expiry_df.sort_values(by=['Expiry'])["cum_Expiry"],
        "line": {"shape": 'hv', "color": "purple",},
        # "x": x, #self.supply_expiry_df.sort_values(by=['Expiry'])['Expiry'],
        # "y": expiry, # self.supply_expiry_df.sort_values(by=['Expiry'])["cum_Expiry"],
        # "line": {"color": "purple",},
        "mode": 'lines',
        "name": 'Expiry',
        "type": 'scatter',
        }


        # data = [supply_trace, expiry_trace, confidence_trace]
        data = [supply_trace, confidence_trace]
        supply_expiry_fig = go.Figure(data)

        supply_expiry_fig.update_layout(
            title="Supply Schedule",
            xaxis={'title': 'Time'},
            yaxis={'title': '# Doses'}
        )

        supply_expiry_fig.add_shape(type="rect",
                    name="Simulation Period",
                    x0=start_date_str,
                    x1=datetime.strftime(datetime.strptime(start_date_str, "%Y-%m-%d") + relativedelta(days=length) , "%Y-%m-%d"),
                    y0=0, y1=self.supply_expiry_df["cum_Supply"].max(),
                    line=dict(
                        color="MediumPurple",
                        width=2,
                        dash="dot",
                        ),
                    fillcolor="MediumPurple",
                    opacity=0.15
                    )

        supply_expiry_fig.update_yaxes(title_text="# Doses", rangemode="tozero")

        return supply_expiry_fig

    def get_confidence_trace(self, start_date_str, length, vaccine):

        dir_path = os.path.dirname(os.path.realpath(__file__))

        try:
            with open(f"{dir_path}/confidence/{self.scenario}_{vaccine}.json") as confidence_trace_file:
                confidence_trace = json.load(confidence_trace_file)
                return confidence_trace
        except:
            pass


        x = [datetime.strftime(datetime.strptime(start_date_str, "%Y-%m-%d") + relativedelta(days=d) , "%Y-%m-%d") for d in list(range(length))]

        supply = self.get_supply_vector(start_date_str, length, 'Supply', vaccine=vaccine)

        df = self.confidence_simulation(supply)

        stats = df.agg(['mean', 'count', 'std'])
        stats = stats.transpose()
        ci_hi = [0]*len(supply)
        ci_lo = [0]*len(supply)

        for i in stats.index:
            ci_hi[i] = np.percentile(df[i], 90)
            ci_lo[i] = np.percentile(df[i], 10)

        stats['ci_hi'] = ci_hi
        stats['ci_lo'] = ci_lo

        y_upper = stats['ci_hi'].to_numpy().tolist()
        y_lower = stats['ci_lo'].to_numpy().tolist()
        confidence_trace = {
            "x": x+x[::-1], # x, then x reversed
            "y": y_upper+y_lower[::-1], # upper, then lower reversed
            "fill": 'toself',
            "fillcolor": 'rgba(0,100,80,0.2)',
            "line": dict(color='rgba(255,255,255,0)'),
            "hoverinfo": "skip",
            "showlegend": False
        }

        with open(f"{dir_path}/confidence/{self.scenario}_{vaccine}.json", 'w') as confidence_trace_file:
            json.dump(confidence_trace, confidence_trace_file)

        return confidence_trace

    def confidence_simulation(self, supply):

        df = pd.DataFrame(data=np.transpose(supply).reshape(-1, len(supply)))

        for sim in range(10000):
            schedule = self.get_perturbed_supply(supply)

            df = df.append(pd.DataFrame(data=np.transpose(schedule).reshape(-1, len(schedule))), ignore_index=True)

        return df

    def get_supply_at_confidence_level(self, start_date_str, length, vaccine, ptile=None):

        supply = self.get_supply_vector(start_date_str, length, 'Supply', vaccine=vaccine)
        if ptile == None:
            return [supply[0]] + [supply[i]-supply[i-1] for i in range(1, len(supply))]
        else:
            df = self.confidence_simulation(supply)
            # stats = df.agg(['mean', 'count', 'std'])
            # stats = stats.transpose()
            supply_conf = [0]*len(supply)

            # for i in stats.index:
            for i in range(len(supply)):
                supply_conf[i] = int(np.percentile(df[i], ptile))

            # print('supply_conf', supply_conf)

            return [supply_conf[0]] + [supply_conf[i]-supply_conf[i-1] for i in range(1, len(supply_conf))]

    def remove_confidence_trace(self, vaccine):

        dir_path = os.path.dirname(os.path.realpath(__file__))

        try:
            os.remove(f"{dir_path}/confidence/{self.scenario}_{vaccine}.json")
        except Exception as e:
            print(e)

    def get_perturbed_supply(self, supply):

        schedule = [0]*len(supply)

        last_start = -math.inf
        for start in range(len(supply)):
            if supply[start] == last_start:
                last_start = supply[start]
                continue
            for end in range(start+1, len(supply)):
                if supply[end] > supply[start]:
                    break

            if end==start:
                schedule[end] = schedule[end-1]
                break

            # print(start, end)
            if start < 14: # Assume first 2 weeks is deterministic supply)
                s = supply[start]
                i = 0
            else:
                s = normal(supply[start], 50000)
                i = randint(min(end-start, 7))

            for day in range(i):
                if start+day == 0:
                    schedule[start+day] = s
                else:
                    schedule[start+day] = schedule[start+day-1]

            for day in range(start+i, end):
                schedule[day] = s

        return schedule
