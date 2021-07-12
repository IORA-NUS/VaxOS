import math, json, os, plotly
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime
import datetime as dt
from dateutil.relativedelta import relativedelta
from math import ceil, log, floor

from vaxos.params import demand_types, location_types, vaccine_types, Params
from vaxos.supply_expiry import SupplyExpiry # get_supply_expiry_figure, vaccine_consumed

def df_to_plotly(df):
    return {'z': df.values.tolist(),
            'x': df.columns.tolist(),
            'y': df.index.tolist()}

def human_format(number):
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    if number < 1000000:
        return '%d%s' % (number / k**magnitude, units[magnitude])
    else:
        return '%.1f%s' % (number / k**magnitude, units[magnitude])


class ResultProcessor:
    ''' '''
    scenario = None
    results_dir = None
    occupancy_df = None
    arrival_df = None
    person_rank_df = None
    kpi = None
    curr_appt_first_sum = None
    curr_appt_second_sum = None

    def __init__(self, scenario):
        ''' '''
        self.scenario = scenario
        self.dir_path = os.path.dirname(os.path.realpath(__file__))

        self.results_dir = f"{self.dir_path}/results/{scenario}"

        with open(f"{self.results_dir}/results.json") as kpi_file:
            self.kpi = json.load(kpi_file)

        self.person_rank_df = pd.read_csv(f"{self.results_dir}/person_rank_df.csv", index_col=0,
                                dtype={
                                    "space_time": "string",
                                    "location": "string",
                                    "period": int,
                                    "arrival_time": int,
                                    "waiting_time": int,
                                    "preference_rank": int,
                                    "location_rank": int,
                                    # "d_type": "string",
                                    "appt_time": int,
                                    "appt_waiting_time": int,
                                })
        params = self.kpi['params']
        self.start_date = datetime.strptime(params['start_date'], "%Y-%m-%d")
        self.horizon_date = self.start_date + relativedelta(days=params['duration']-1)
        self.horizon = params['duration'] - 1

        self.planning_duration = params['planning_duration'] if params.get('planning_duration') is not None else params['duration']
        self.planning_horizon_date = self.start_date + relativedelta(days=self.planning_duration-1)
        self.planning_horizon = self.planning_duration - 1


        self.occupancy_df = pd.read_csv(f"{self.results_dir}/occupancy_df.csv", index_col=[0,1])
        self.arrival_df = pd.read_csv(f"{self.results_dir}/arrival_df.csv", index_col=[0])

        self.occupancy_df['date'] = pd.to_datetime(datetime.strptime(params['start_date'], "%Y-%m-%d").date())
        self.occupancy_df['time_added'] = pd.to_timedelta(self.occupancy_df['period'],'d')
        self.occupancy_df['date'] = self.occupancy_df['date'] + self.occupancy_df['time_added']

        # Gather Initial Consditions
        self.reset_occupancy = self.occupancy_df.reset_index(level=[0,1]).groupby('date').sum() / params['scale_factor']
        self.vaccine_types_used = self.occupancy_df['vaccine'].unique()
        # self.reset_occupancy.reset_index(inplace=True)


        # self.curr_appt_second_sum = [0] * params['duration']
        # for vac in vaccine_types:
        #     _, second_appts, _ = Params.get_appt_book(params, vac)
        #     self.curr_appt_second_sum = np.add(self.curr_appt_second_sum, second_appts[0:params['duration']])

        self.longest_epoch = 0
        self.curr_appt_second_sum = {}
        for vac in vaccine_types:
            _, second_appts, _ = Params.get_appt_book(params, vac)
            self.curr_appt_second_sum[vac] = second_appts[0:params['duration']]

            if self.longest_epoch < params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']:
                self.longest_epoch = params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']

    @classmethod
    def get_scenarios(cls):
        # scenarios = [f for f in os.listdir('results') if f[0] != '.' and (f.find('balanced') == 0 or f.find('current') == 0 or  f.find('toy') == 0)]
        dir_path = os.path.dirname(os.path.realpath(__file__))

        scenarios = [f for f in os.listdir(f'{dir_path}/results') ]
        scenarios.sort()
        # print(scenarios)
        return scenarios

    @classmethod
    def rebuild_all(cls):
        for scenario in cls.get_scenarios():
            proc = ResultProcessor(scenario)
            print(scenario)
            proc.generate_dashboard(True)

    def update_stats(self):
        # Time to reach TPut
        params = self.kpi['params']
        inter_ttr_gap = 200000

        reset_occupancy = self.occupancy_df.reset_index(level=[0,1]).groupby('period').sum() / params['scale_factor']
        max_first_dose = reset_occupancy['first_shot'].sum()

        idx = 0
        cum = 0
        ttr = {}

        tput_threshold = 0

        while tput_threshold < max_first_dose:
            tput_threshold += inter_ttr_gap

            idx = 0
            cum = 0
            for row in reset_occupancy.sort_values('period').iterrows():
                if (cum < tput_threshold) and ((cum + row[1]['first_shot']) >= tput_threshold):
                    ttr[human_format(tput_threshold)] = idx + 1
                cum += row[1]['first_shot']
                idx += 1
                if ttr.get(human_format(tput_threshold)) is not None:
                    # print(human_format(tput_threshold), idx+1)
                    break

        self.kpi['stats']['Time To Reach Tput'] = ttr

        # KPIs at 60% period
        kpi_period = ceil(params['duration'] * 0.6)

        kpi_period_df = self.person_rank_df[(self.person_rank_df['arrival_time'] >= 0) & (self.person_rank_df['period'] < kpi_period)]
        res = {}

        res_all = kpi_period_df.agg({'period': 'count', 'waiting_time': 'mean', 'appt_waiting_time': 'mean' })
        res['All'] = res_all.to_dict()
        res['All']['Tput'] = res['All'].pop('period')  / params['scale_factor']

        for vac in vaccine_types:
            res_vac = kpi_period_df[kpi_period_df['vaccine'] == vac].agg({'period': 'count', 'waiting_time': 'mean', 'appt_waiting_time': 'mean' })
            res[vac] = res_vac.to_dict()
            res[vac]['Tput'] = res[vac].pop('period') / params['scale_factor']

        self.kpi['stats'][f'KPI at {kpi_period//7}W'] = res



    def get_summary_stats(self):
        ''' '''
        results_dir = f"{os.getcwd()}/results"
        summary_stats = []

        for scenario in self.get_scenarios():
            with open(f"{results_dir}/{scenario}/results.json") as results_file:
                results = json.load(results_file)
                summary_stats.append({
                    "Scenario": results['params']['name'],
                    "Description": results['params']['description'],
                    "Arrival Dist": json.dumps(results['params']['distribution']),
                    "Utility Bias": json.dumps(results['params']['utility']),
                    "Response Rate": json.dumps(results['params']['response_rate']),
                    "Avg. Waiting Time": results['stats']['Avg Waiting Time (First Shot)'],
                    "Avg. Appt Waiting Time": results['stats'].get('Avg Appt Waiting Time (First Shot)'),
                    "TPut Percentile": json.dumps(results['stats']['TPut Percentile (by Period)']),
                    "Avg. Daily TPut": results['stats']['Daily Throughout'],
                    # "Demand": json.dumps(results['params']['demand']),
                    # "Target": json.dumps(results['params']['target']),
                    "Time To Reach Tput": json.dumps(results['stats'].get('Time To Reach Tput')),
                    "First Shot Capacity Limit":
                        "" if results['params'].get('first_shot_limit') is None else json.dumps(results['params']['first_shot_limit'])
                })

        summary_df = pd.DataFrame.from_dict(summary_stats)
        summary_df.to_excel('summary.xlsx', sheet_name='summary')

        return summary_stats

    def get_vaccine_usage(self):
        # vaccine Usage
        reset_occupancy = self.occupancy_df.reset_index(level=[0,1]).groupby('period').sum()
        # reset_occupancy[['first_shot', 'second_shot']].cumsum()
        reset_occupancy['total'] = reset_occupancy['first_shot'] + reset_occupancy['second_shot']

        # arrival = pd.DataFrame(self.population.arrival)
        # fig_vaccine_usage = make_subplots(specs=[[{"secondary_y": True}]])

        fig_vaccine_usage = px.bar(self.arrival_df, barmode='stack', opacity=0.5, labels={'variable': 'Population Group'},
            category_orders={'variable': ['old', '3', '4', '5', '6', '7']}
        )
        # fig_bar = px.bar(arrival_df, barmode='stack', opacity=0.5, labels={'variable': 'Population Group'})
        # fig_line = px.line(reset_occupancy[['first_shot', 'second_shot', 'total']].cumsum()[['first_shot', 'second_shot', 'total']])
        fig_line = px.line(reset_occupancy[['first_shot', 'second_shot', 'total']])
        fig_line.data[0].name = 'First Shot'
        fig_line.data[0].line.dash = 'dot'
        fig_line.data[1].name = 'Second Shot'
        fig_line.data[1].line.dash = 'dot'
        fig_line.data[2].name = 'Total Dose'

        for trace in fig_line['data']:
            fig_vaccine_usage.add_trace(trace,)

        fig_vaccine_usage.update_layout(
            title="Vaccine Usage with arrival",
            xaxis_title="Time (Days)",
            barmode='stack',
        )

        fig_vaccine_usage.update_yaxes(title_text="# Doses", rangemode="tozero")

        return fig_vaccine_usage

    def get_arrival_pattern(self):

        params = self.kpi['params']
        # detailed_arrival_df = self.person_rank_df.groupby(['appt_time', 'd_type', 'arrival_time']).size().reset_index(name='arrivals')
        detailed_arrival_df = self.person_rank_df.groupby(['appt_time', 'arrival_time']).size().reset_index(name='arrivals')

        # fig_arrival = px.bar(arrival_df, barmode='stack', opacity=0.5, labels={'variable': 'Population Group'},
        #     category_orders={'variable': ['old', '3', '4', '5', '6', '7']}
        # )
        fig_arrival = px.bar(detailed_arrival_df, x='arrival_time', y='arrivals', color='appt_time',color_continuous_scale=px.colors.sequential.Redor)
        fig_arrival.update(layout_coloraxis_showscale=False)

        fig_arrival.update_layout(
            title=f"Arrival Pattern ({params['distribution']}, Multiple waves)",
            xaxis_title="Time (Days)",
            barmode='stack',
        )

        fig_arrival.update_yaxes(title_text="# Doses", rangemode="tozero")

        return fig_arrival

    def get_vaccination_rate(self):

        if len(self.vaccine_types_used) > 1:
            num_subplots = len(self.vaccine_types_used) + 1
            subplot_titles = vaccine_types + ['All']
        else:
            num_subplots = len(self.vaccine_types_used)
            subplot_titles = vaccine_types


        fig = make_subplots(
            rows=num_subplots,
            cols=1,
            # subplot_titles=subplot_titles,
            row_titles=subplot_titles,
            shared_xaxes=True,
            shared_yaxes=True,
            vertical_spacing=0.02)

        idx = 1

        for vac in subplot_titles: #self.vaccine_types_used:

            fig_vaccine_usage_cumulative = self.get_vac_vaccination_rate(vac)

            for data in fig_vaccine_usage_cumulative['data']:
                if vac != 'All':
                    data['showlegend'] = False
                else:
                    data['legendgroup'] = vac

                fig.add_trace(data, row=idx, col=1)

                if self.horizon != self.planning_horizon:
                    fig.add_vline(x=self.planning_horizon, line_width=1, line_dash="dot", line_color="dodgerblue",
                                annotation_text=f"Planning Horizon", annotation_position="top right",
                                row=idx, col=1)

                fig.add_vline(x=self.horizon, line_width=1, line_dash="dot", line_color="dodgerblue",
                            annotation_text=f"Horizon", annotation_position="top right",
                            row=idx, col=1)

            idx += 1

        time_to_reach_tput = self.kpi['stats']['Time To Reach Tput']
        for k, v in time_to_reach_tput.items():
            # print(type(k), type(v))
            if type(v) == int:
                # for idx in range(len(self.vaccine_types_used)):
                fig.add_vline(x=v-1, line_width=1, line_dash="dash", line_color="gray",
                            annotation_text=f"{k}<br>{v}d", annotation_position="bottom",
                            annotation_font_size=10,
                            row=num_subplots, col=1)

        fig.update_layout(height=num_subplots * 400,
            title_text='Vaccination Rate (Future Arrivals)',
        )
        fig.update_xaxes(visible=False)

        return fig

    def get_vac_vaccination_rate(self, vaccine='All'):
        ''' '''
        params = self.kpi['params']
        supply_expiry = SupplyExpiry(params['supply_scenario_display'])

        reset_occupancy = self.occupancy_df.reset_index(level=[0,1])

        if vaccine == 'All':
            reset_occupancy = reset_occupancy.groupby(['date']).sum() / params['scale_factor']
            reset_occupancy.reset_index(inplace=True)
            cum_occupancy = reset_occupancy
            # cum_occupancy.set_index('date', inplace=True)
            supply = [0] * self.longest_epoch
            # supply = [0] * params['duration']
            risk = params['risk']

            # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = 0
            cum_occupancy[f"Reserve at {risk} day Risk"] = 0
            for vac in self.vaccine_types_used:
                vac_reset_occupancy = self.occupancy_df.reset_index(level=[0,1])

                vac_reset_occupancy = vac_reset_occupancy[vac_reset_occupancy['vaccine']==vac].groupby(['date']).sum() / params['scale_factor']
                vac_reset_occupancy.reset_index(inplace=True)
                vac_cum_occupancy = vac_reset_occupancy
                vac_cum_occupancy.set_index('date', inplace=True)

                # vac_cum_occupancy['second_shot'] = vac_cum_occupancy['second_shot'] + np.append(self.curr_appt_second_sum[vac], [0]* (len(vac_cum_occupancy['second_shot']) - len(self.curr_appt_second_sum[vac])))
                # cum_occupancy['second_shot'] = cum_occupancy['second_shot'] + np.append(self.curr_appt_second_sum[vac], [0]* (len(cum_occupancy['second_shot']) - len(self.curr_appt_second_sum[vac])))

                vac_cum_occupancy[f"reserve"] = (vac_cum_occupancy.iloc[::-1]
                                                                # .rolling(max(0, params['vaccine_settings'][vac]['second_shot_gap'] - params['risk']), min_periods=0)['second_shot']
                                                                .rolling(max(0, params['vaccine_settings'][vac]['second_shot_gap'] - risk), min_periods=0)['second_shot']
                                                                .sum()
                                                                .iloc[::-1])

                # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = cum_occupancy[f"Reserve at {params['risk']} day Risk"] + (vac_cum_occupancy[f"reserve"].tolist() + ([0] * (len(cum_occupancy) - len(vac_cum_occupancy))))
                cum_occupancy[f"Reserve at {risk} day Risk"] = cum_occupancy[f"Reserve at {risk} day Risk"] + (vac_cum_occupancy[f"reserve"].tolist() + ([0] * (len(cum_occupancy) - len(vac_cum_occupancy))))

                supply = np.add(supply, supply_expiry.get_supply_vector(params['start_date'], self.longest_epoch, state='Supply', vaccine=vac, cumulative=True, include_init=False))
                # supply = np.add(supply, supply_expiry.get_supply_vector(params['start_date'], params['duration'], state='Supply', vaccine=vac, cumulative=True, include_init=False))
                supply = supply.tolist()

        else:
            risk = params['vaccine_settings'][vaccine].get('risk', params['risk'])
            reset_occupancy = reset_occupancy[reset_occupancy['vaccine']==vaccine].groupby(['date']).sum() / params['scale_factor']
            reset_occupancy.reset_index(inplace=True)
            cum_occupancy = reset_occupancy
            # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = (cum_occupancy.iloc[::-1]
            #                                                 .rolling(max(0, params['vaccine_settings'][vaccine]['second_shot_gap'] - params['risk']), min_periods=0).second_shot
            cum_occupancy[f"Reserve at {risk} day Risk"] = (cum_occupancy.iloc[::-1]
                                                            .rolling(max(0, params['vaccine_settings'][vaccine]['second_shot_gap'] - risk), min_periods=0).second_shot
                                                            .sum()
                                                            .iloc[::-1])

            supply = supply_expiry.get_supply_vector(params['start_date'], self.longest_epoch, state='Supply', vaccine=vaccine, cumulative=True, include_init=False)
            # supply = supply_expiry.get_supply_vector(params['start_date'], params['duration'], state='Supply', vaccine=vaccine, cumulative=True, include_init=False)

        # supply = supply + ([supply[-1]] * (self.longest_epoch - params['duration']) )

        cum_occupancy['cum_supply'] = supply[:len(cum_occupancy)]
        cum_occupancy['total'] = cum_occupancy['first_shot'] + cum_occupancy['second_shot']
        cum_occupancy['inventory'] = cum_occupancy['cum_supply']  - cum_occupancy['total'].cumsum()

        fig_vaccine_usage_cumulative = px.line(cum_occupancy[['first_shot', 'second_shot']].cumsum()[['first_shot', 'second_shot']])
        fig_vaccine_usage_cumulative.update_layout(
            title="Vaccination Rate (Upcoming appointments)",
            xaxis_title="Time (Date)",
        )

        # fig_safety = px.line(cum_occupancy[f"Reserve at {params['risk']} day Risk"])
        fig_safety = px.line(cum_occupancy[f"Reserve at {risk} day Risk"])
        fig_safety.data[0].line.color = 'magenta'
        for data in fig_safety['data']:
            # data['legendgroup'] = vaccine
            fig_vaccine_usage_cumulative.add_trace(data)


        fig_inventory = px.bar(cum_occupancy['inventory'])
        fig_inventory.update_traces(marker_color='#f58518', marker_opacity=0.4)

        for data in fig_inventory['data']:
            # data['legendgroup'] = vaccine
            fig_vaccine_usage_cumulative.add_trace(data)

        fig_vaccine_usage_cumulative.update_yaxes(title_text="# Doses", rangemode="tozero")
        fig_vaccine_usage_cumulative.update_xaxes(visible=False)

        return fig_vaccine_usage_cumulative

    def get_supply_demand(self):
        ''' '''
        if len(self.vaccine_types_used) > 1:
            num_subplots = len(self.vaccine_types_used) + 1
            subplot_titles = vaccine_types + ['All']
        else:
            num_subplots = len(self.vaccine_types_used)
            subplot_titles = vaccine_types

        fig = make_subplots(
            rows=num_subplots,
            cols=1,
            # subplot_titles=subplot_titles,
            row_titles=subplot_titles,
            shared_xaxes=True,
            # shared_yaxes=True,
            vertical_spacing=0.02)

        idx = 1

        for vac in subplot_titles: #self.vaccine_types_used:

            supply_expiry_fig = self.get_vac_supply_demand(vac)

            for data in supply_expiry_fig['data']:
                if vac != 'All':
                    data['showlegend'] = False
                else:
                    data['legendgroup'] = vac

                fig.add_trace(data, row=idx, col=1)

                if self.horizon != self.planning_horizon:
                    fig.add_vline(x=self.planning_horizon_date.timestamp() * 1000, line_width=1, line_dash="dot", line_color="dodgerblue",
                                annotation_text=f"Planning Horizon", annotation_position="top right",
                                row=idx, col=1)

                fig.add_vline(x=self.horizon_date.timestamp() * 1000, line_width=1, line_dash="dot", line_color="dodgerblue",
                            annotation_text=f"Horizon", annotation_position="top right",
                            row=idx, col=1)

            idx += 1

        fig.update_yaxes(rangemode="tozero")
        fig.update_layout(height=num_subplots * 400,
                title_text='Cumulative Vaccination with Supply, Inventory and Reserve',
            )
        return fig

    def get_vac_supply_demand(self, vaccine):
        ''' '''
        params = self.kpi['params']
        supply_expiry = SupplyExpiry(params['supply_scenario_display'])

        reset_occupancy = self.occupancy_df.reset_index(level=[0,1])
        if vaccine == 'All':
            reset_occupancy = reset_occupancy.groupby(['date']).sum() / params['scale_factor']
            reset_occupancy.reset_index(inplace=True)
            cum_occupancy = reset_occupancy
            cum_occupancy.set_index('date', inplace=True)

            curr_appt_second_sum = [0]*self.longest_epoch
            risk = params['risk']


            # for vac in self.vaccine_types_used:
            #     vac_curr_appt_second_sum = np.append(np.array(self.curr_appt_second_sum[vac]), [0]* max(0, self.longest_epoch - len(self.curr_appt_second_sum[vac])))
            #     curr_appt_second_sum = np.add(curr_appt_second_sum, vac_curr_appt_second_sum).tolist()

            # cum_occupancy['second_shot'] = cum_occupancy['second_shot'] + np.append(curr_appt_second_sum, [0]* (len(cum_occupancy['second_shot']) - len(curr_appt_second_sum)))

            # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = (cum_occupancy.iloc[::-1]
            #                                                 .rolling(max(0, params['vaccine_settings'][vac]['second_shot_gap'] - params['risk']), min_periods=0)['second_shot']
            #                                                 .sum()
            #                                                 .iloc[::-1])
            # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = 0
            cum_occupancy[f"Reserve at {risk} day Risk"] = 0
            for vac in self.vaccine_types_used:
                vac_reset_occupancy = self.occupancy_df.reset_index(level=[0,1])

                vac_reset_occupancy = vac_reset_occupancy[vac_reset_occupancy['vaccine']==vac].groupby(['date']).sum() / params['scale_factor']
                vac_reset_occupancy.reset_index(inplace=True)
                vac_cum_occupancy = vac_reset_occupancy
                vac_cum_occupancy.set_index('date', inplace=True)

                vac_cum_occupancy['second_shot'] = vac_cum_occupancy['second_shot'] + np.append(self.curr_appt_second_sum[vac], [0]* (len(vac_cum_occupancy['second_shot']) - len(self.curr_appt_second_sum[vac])))
                cum_occupancy['second_shot'] = cum_occupancy['second_shot'] + np.append(self.curr_appt_second_sum[vac], [0]* (len(cum_occupancy['second_shot']) - len(self.curr_appt_second_sum[vac])))

                vac_cum_occupancy[f"reserve"] = (vac_cum_occupancy.iloc[::-1]
                                                                # .rolling(max(0, params['vaccine_settings'][vac]['second_shot_gap'] - params['risk']), min_periods=0)['second_shot']
                                                                .rolling(max(0, params['vaccine_settings'][vac]['second_shot_gap'] - risk), min_periods=0)['second_shot']
                                                                .sum()
                                                                .iloc[::-1])

                # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = cum_occupancy[f"Reserve at {params['risk']} day Risk"] + vac_cum_occupancy[f"reserve"]
                cum_occupancy[f"Reserve at {risk} day Risk"] = cum_occupancy[f"Reserve at {risk} day Risk"] + vac_cum_occupancy[f"reserve"]

        else:
            risk = params['vaccine_settings'][vaccine].get('risk', params['risk'])
            reset_occupancy = reset_occupancy[reset_occupancy['vaccine']==vaccine].groupby(['date']).sum() / params['scale_factor']
            reset_occupancy.reset_index(inplace=True)
            cum_occupancy = reset_occupancy
            cum_occupancy.set_index('date', inplace=True)

            cum_occupancy['second_shot'] = cum_occupancy['second_shot'] + np.append(self.curr_appt_second_sum[vaccine], [0]* (len(cum_occupancy['second_shot']) - len(self.curr_appt_second_sum[vaccine])))

            # cum_occupancy[f"Reserve at {params['risk']} day Risk"] = (cum_occupancy.iloc[::-1]
                                                            # .rolling(max(0, params['vaccine_settings'][vaccine]['second_shot_gap'] - params['risk']), min_periods=0)['second_shot']
            cum_occupancy[f"Reserve at {risk} day Risk"] = (cum_occupancy.iloc[::-1]
                                                            .rolling(max(0, params['vaccine_settings'][vaccine]['second_shot_gap'] - risk), min_periods=0)['second_shot']
                                                            .sum()
                                                            .iloc[::-1])

        cum_occupancy['total'] = cum_occupancy['first_shot'] + cum_occupancy['second_shot']

        # supply_expiry_fig = supply_expiry.get_supply_expiry_figure(params['start_date'], params['duration'], vaccine=vaccine)
        supply_expiry_fig = supply_expiry.get_supply_expiry_figure(params['start_date'], self.longest_epoch, vaccine=vaccine)

        # try:
        #     with open(f"confidence/{self.scenario}/confidence_trace.json") as confidence_file:
        #         confidence_fig = plotly.io.from_json(json.load(confidence_file))
        #         for data in confidence_fig['data']:
        #             supply_expiry_fig.add_trace(data)
        # except: pass

        fig_vaccine_usage_cumulative_adjusted = px.line(cum_occupancy[['first_shot', 'second_shot', 'total']].cumsum()[['first_shot', 'second_shot', 'total']]) #+ supply_expiry.get_vaccine_consumed())

        for data in fig_vaccine_usage_cumulative_adjusted['data']:
            # data['legendgroup'] = vaccine
            supply_expiry_fig.add_trace(data)

        # fig_safety = px.line(cum_occupancy[f"Reserve at {params['risk']} day Risk"])
        fig_safety = px.line(cum_occupancy[f"Reserve at {risk} day Risk"])
        fig_safety.data[0].line.color = 'magenta'
        for data in fig_safety['data']:
            # data['legendgroup'] = vaccine
            supply_expiry_fig.add_trace(data)

        # # missed appointments
        # missed_appt_df = self.person_rank_df[self.person_rank_df['location_rank']==-1].groupby('arrival_time').count().reset_index()
        # missed_appt_df['date'] = pd.to_datetime(datetime.strptime(params['start_date'], "%Y-%m-%d").date())
        # missed_appt_df['time_added'] = pd.to_timedelta(missed_appt_df['arrival_time'],'d')
        # missed_appt_df['date'] = missed_appt_df['date'] + missed_appt_df['time_added']
        # fig_missed_appt = px.bar(missed_appt_df, x='date', y='preference_rank', barmode='stack',
        #                     labels={'preference_rank':'Spillover'})

        # for data in fig_missed_appt['data']:
        #     supply_expiry_fig.add_trace(data)

        # Inventory

        # supply = supply_expiry.get_supply_vector(params['start_date'], params['duration'], state='Supply', vaccine=vaccine)
        supply = supply_expiry.get_supply_vector(params['start_date'], self.longest_epoch, state='Supply', vaccine=vaccine)

        new_supply = [0]*len(cum_occupancy)
        for i in range(len(cum_occupancy)):
            if i < len(supply):
                new_supply[i] = supply[i]
            else:
                new_supply[i] = supply[len(supply)-1]

        cum_occupancy['cum_supply'] = new_supply
        cum_occupancy['inventory'] = cum_occupancy['cum_supply']  - cum_occupancy['total'].cumsum()

        fig_inventory = px.bar(cum_occupancy['inventory'])
        fig_inventory.update_traces(marker_color='#f58518', marker_opacity=0.4)

        for data in fig_inventory['data']:
            # data['legendgroup'] = vaccine
            supply_expiry_fig.add_trace(data)

        return supply_expiry_fig

    def get_target_chart(self):
        fig = go.Figure()
        params = self.kpi['params']
        target_df = pd.DataFrame()

        for vac in vaccine_types:
            reset_occupancy = self.occupancy_df.reset_index(level=[0,1], drop=True)
            reset_occupancy = reset_occupancy[reset_occupancy['vaccine']==vac].groupby(['date']).sum() / params['scale_factor']
            reset_occupancy.reset_index(inplace=True)

            tmp_df = pd.DataFrame()
            vac_first_dose_booking_limit = np.append(np.array(params['vaccine_settings'][vac]['first_dose_booking_limit']), [0]* max(0, self.longest_epoch - len(np.array(params['vaccine_settings'][vac]['first_dose_booking_limit']))))
            # print(len(np.array(params['vaccine_settings'][vac]['first_dose_booking_limit'])))

            tmp_df[f'first_dose_bl'] = vac_first_dose_booking_limit
            tmp_df[f'week_target'] = tmp_df[f'first_dose_bl'].iloc[::-1].rolling(7, min_periods=0).sum().iloc[::-1]

            tmp_df[f'day_first_dose'] = reset_occupancy['first_shot'] #.reset_index(drop=True)
            tmp_df[f'day_second_dose'] = reset_occupancy['second_shot'] #.reset_index(drop=True)

            tmp_df['day_second_dose'] = tmp_df['day_second_dose'] + np.append(self.curr_appt_second_sum[vac], [0]* (len(tmp_df) - len(self.curr_appt_second_sum[vac])))

            tmp_df[f'week_first_dose'] = tmp_df[f'day_first_dose'].iloc[::-1].rolling(7, min_periods=0).sum().iloc[::-1]
            tmp_df[f'week_second_dose'] = tmp_df[f'day_second_dose'].iloc[::-1].rolling(7, min_periods=0).sum().iloc[::-1]

            tmp_df[f'day_capacity'] = 0
            for loc in location_types:
                # print(len(tmp_df), len(params['vaccine_settings'][vac]['location'][loc]))
                num_loc_list = params['vaccine_settings'][vac]['location'][loc]
                if len(num_loc_list) < len(tmp_df):
                    num_loc_list.extend([num_loc_list[-1]] * (len(tmp_df) - len(num_loc_list)))

                tmp_df[f'day_capacity'] = tmp_df[f'day_capacity'] +  (np.array(num_loc_list) * params['capacity'][loc])
                # tmp_df[f'day_capacity'] = tmp_df[f'day_capacity'] +  np.array(params['vaccine_settings'][vac]['location'][loc]) * params['capacity'][loc]

            tmp_df[f'week_capacity'] = tmp_df[f'day_capacity'].iloc[::-1].rolling(7, min_periods=0).sum().iloc[::-1]

            tmp_df['vaccine'] = vac

            tmp_df[f'period'] = reset_occupancy['period'] #.reset_index(drop=True)
            tmp_df[f'date'] = reset_occupancy['date'] #.reset_index(drop=True)

            target_df = target_df.append(tmp_df)
            vac_df = tmp_df[::7].dropna()

            vac_df = vac_df[vac_df['date'] < pd.to_datetime(datetime.strptime(params['start_date'], "%Y-%m-%d").date() + relativedelta(days= params['duration']+1)) ]
            # fig.add_trace(go.Scatter(x=vac_df['date'], y=vac_df['week_target'], mode='markers', name=f'{vac} target', marker= {'color':'black', 'opacity': 0.6, 'symbol': 'diamond'}))



        total_df = target_df.groupby('date').sum().reset_index()
        total_df = total_df[::7].dropna()
        total_df = total_df[total_df['date'] < pd.to_datetime(datetime.strptime(params['start_date'], "%Y-%m-%d").date() + relativedelta(days= params['duration']+1)) ]


        fig.add_trace(go.Scatter(x=total_df['date'], y=total_df['week_target'], mode='markers+lines', name="Target", marker={'color': 'red', 'symbol': 'circle-dot', 'size':8}, line={'dash': 'dot', 'width': 1}))
        fig.add_trace(go.Scatter(x=total_df['date'], y=total_df['week_capacity'], mode='markers+lines', name="Capacity", marker={'color': 'orange', 'symbol': 'circle-dot', 'opacity': 0.6 }, line={'dash': 'dot', 'width': 1}))
        fig.add_trace(go.Bar(x=total_df['date'], y=total_df['week_first_dose'], name=f'First Dose Total', opacity=0.6, marker={'color': 'blue',}, )) # 'opacity': 0.6}, ))
        fig.add_trace(go.Bar(x=total_df['date'], y=total_df['week_second_dose'], name=f'Second Dose Total', opacity=0.3, marker={'color': 'blue',}, )) # 'opacity': 0.3}, ))

        fig.update_layout(barmode='stack', title_text='Weekly Doses Administered')

        return fig

    def get_utilization(self):
        # VC utilization
        agg_occ = self.occupancy_df.groupby('period')[['first_shot', 'second_shot', 'capacity']].sum()
        agg_occ = agg_occ.eval('first_shot_util = first_shot*100/capacity')
        agg_occ = agg_occ.eval('second_shot_util = second_shot*100/capacity')
        agg_occ = agg_occ.eval('total_util = (first_shot+second_shot)*100/capacity')

        fig_vc_utilization = px.line(agg_occ, y=['first_shot_util', 'second_shot_util', 'total_util'], labels={'variable': 'Utilization %'},  title='VC Utilization')
        fig_vc_utilization.data[0].name = 'First Shot'
        fig_vc_utilization.data[0].line.dash = 'dot'
        fig_vc_utilization.data[1].name = 'Second Shot'
        fig_vc_utilization.data[1].line.dash = 'dot'
        fig_vc_utilization.data[2].name = 'Total'
        # fig_vc_utilization.data[2].line.dash = 'dot'

        fig_vc_utilization.update_yaxes(title_text="Capacity %", rangemode="tozero")
        fig_vc_utilization.update_layout()

        return fig_vc_utilization

    def get_waiting_time(self):

        if len(self.vaccine_types_used) > 1:
            num_subplots = len(self.vaccine_types_used) + 1
            subplot_titles = vaccine_types + ['All']
        else:
            num_subplots = len(self.vaccine_types_used)
            subplot_titles = vaccine_types

        fig = make_subplots(
            rows=num_subplots,
            cols=2,
            row_titles=subplot_titles,
            column_titles=['Since Invitation', 'Since Arrival'],
            shared_xaxes='columns',
            shared_yaxes='columns',
            vertical_spacing=0.04)

        idx = 1
        for vac in subplot_titles: #self.vaccine_types_used:

            fig_appt_waiting_time, fig_waiting_time = self.get_vac_waiting_time(vac)

            for data in fig_appt_waiting_time['data']:
                data['showlegend'] = False

                fig.add_trace(data, row=idx, col=1)

            for data in fig_waiting_time['data']:
                data['showlegend'] = False

                fig.add_trace(data, row=idx, col=2)

            idx += 1

        fig.update_layout(height=num_subplots * 400,
                    title_text='Waiting Time',
                    barmode="stack",
                )

        # for idx in range(num_subplots*2):
        #     if idx == 0:
        #         fig.update_layout({f'yaxis_visible': False})
        #     else:
        #         fig.update_layout({f'yaxis{idx+1}_visible': False})

        return fig
        # # Waitingtime Histogram
        # waiting_time = self.person_rank_df[self.person_rank_df['preference_rank'] >= 0]
        # fig_waiting_time_hist = px.histogram(waiting_time, x="appt_waiting_time",
        #         color='appt_time',
        #         labels={'variable': 'Population Group'},
        #         color_discrete_sequence=px.colors.sequential.Redor
        #     )
        #             # category_orders={'d_type': ['old', '3', '4', '5', '6', '7']})
        # fig_waiting_time_hist.update_layout(
        #     title="Waiting time Distribution",
        #     xaxis_title="Waiting time (Days)",
        #     yaxis_title="Count",
        # )

        # return fig_waiting_time_hist

    def get_vac_waiting_time(self, vaccine):

        # Waitingtime Histogram
        if vaccine == 'All':
            waiting_time = self.person_rank_df[self.person_rank_df['preference_rank'] >= 0]
        else:
            waiting_time = self.person_rank_df[(self.person_rank_df['preference_rank'] >= 0) & (self.person_rank_df['vaccine'] == vaccine)]

        fig_appt_waiting_time_hist = px.histogram(waiting_time, x="appt_waiting_time",
                color='appt_time',
                labels={-1: 'Existing Appts'},
                color_discrete_sequence=px.colors.sequential.Redor,
                # histnorm='percent'
            )
                    # category_orders={'d_type': ['old', '3', '4', '5', '6', '7']})
        fig_appt_waiting_time_hist.update_layout(
            title="Waiting time Distribution",
            xaxis_title="Waiting time (Days)",
            # yaxis_title="Percent",
            yaxis_visible=False,
            barmode='stack'
        )

        fig_waiting_time_hist = px.histogram(waiting_time, x="waiting_time",
                color='appt_time',
                labels={-1: 'Existing Appts'},
                color_discrete_sequence=px.colors.sequential.Redor,
                # histnorm='percent'
            )
                    # category_orders={'d_type': ['old', '3', '4', '5', '6', '7']})
        fig_waiting_time_hist.update_layout(
            title="Waiting time Distribution",
            xaxis_title="Waiting time (Days)",
            # yaxis_title="Percent",
            yaxis_visible=False,
            barmode='stack'
        )

        return fig_appt_waiting_time_hist, fig_waiting_time_hist

    def get_location_pref(self):
        # Booking PreferenceRank
        slots_assigned = self.person_rank_df[self.person_rank_df['preference_rank'] >= 0]
        fig_preferred_location_hist = px.histogram(slots_assigned,
                                                    x="location_rank",
                                                    color='location'
                                                )
        fig_preferred_location_hist.update_layout(
            title="Preferred Location Distribution",
            xaxis_title="Rank (Location)",
            yaxis_title="Count",
        )

        return fig_preferred_location_hist

    def get_occupancy(self):
        occupancy_df = self.occupancy_df
        params = self.kpi['params']

        occupancy_df['first_shot_percent'] = 0
        occupancy_df['second_shot_percent'] = 0
        # Add 2nd shot Appt book to occupancy
        for loc in location_types:
            for vac in vaccine_types:
                epoch = params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']
                for period in range(epoch):
                    # for loc_id in range(params['vaccine_settings'][vac]['location'][loc][period]):
                    # occupancy_df.loc[
                    #     # (occupancy_df['location'] == f"{loc}_{vac}_{loc_id:02d}") & \
                    #     occupancy_df['location'].str.contains(f"{loc}_{vac}_") & \
                    #     (occupancy_df['period'] == period),
                    #     'first_shot'] += params['vaccine_settings'][vac]['appt_book']['first_dose'][loc][period] * params['scale_factor']
                    occupancy_df.loc[
                        # (occupancy_df['location'] == f"{loc}_{vac}_{loc_id:02d}") & \
                        occupancy_df['location'].str.contains(f"{loc}_{vac}_") & \
                        (occupancy_df['period'] == period),
                        'second_shot'] += params['vaccine_settings'][vac]['appt_book']['second_dose'][loc][period] * params['scale_factor']

            # Occupancy
            occupancy_df.loc[occupancy_df['location'].str.contains(loc), 'first_shot_percent'] = occupancy_df[occupancy_df['location'].str.contains(loc)]['first_shot'] / (params['capacity'][loc] * params['scale_factor'])
            occupancy_df.loc[occupancy_df['location'].str.contains(loc),'second_shot_percent'] = occupancy_df[occupancy_df['location'].str.contains(loc)]['second_shot'] /  (params['capacity'][loc] * params['scale_factor'])
            # occupancy_df['total_percent'] = (occupancy_df['first_shot'] + occupancy_df['second_shot']) / occupancy_df['capacity']

        occupancy_df['total_percent'] = occupancy_df['first_shot_percent'] + occupancy_df['second_shot_percent']

        # # Occupancy
        # occupancy_df['first_shot_percent'] = occupancy_df['first_shot'] / occupancy_df['capacity']
        # occupancy_df['second_shot_percent'] = occupancy_df['second_shot'] / occupancy_df['capacity']
        # occupancy_df['total_percent'] = (occupancy_df['first_shot'] + occupancy_df['second_shot']) / occupancy_df['capacity']


        # First Shot
        first_shot_pivot = self.occupancy_df.pivot(index="location", columns="period", values='first_shot_percent')

        fig_first_shot_occupancy = go.Figure(data=go.Heatmap(df_to_plotly(first_shot_pivot)),)
        fig_first_shot_occupancy.update_layout(
            title="1st Shot Occupancy (% of capacity)",
            xaxis_title="Time (Days)",
            yaxis_title="VC Location",
        )
        # Second Shot
        second_shot_pivot = self.occupancy_df.pivot(index="location", columns="period", values='second_shot_percent')

        fig_second_shot_occupancy = go.Figure(data=go.Heatmap(df_to_plotly(second_shot_pivot)),)
        fig_second_shot_occupancy.update_layout(
            title="2nd Shot Occupancy (% of capacity)",
            xaxis_title="Time (Days)",
            yaxis_title="VC Location",
        )

        total_pivot = self.occupancy_df.pivot(index="location", columns="period", values='total_percent')

        fig_total_occupancy = go.Figure(data=go.Heatmap(df_to_plotly(total_pivot)),)
        fig_total_occupancy.update_layout(
            title="Total Occupancy (% of capacity)",
            xaxis_title="Time (Days)",
            yaxis_title="VC Location",
        )

        return fig_first_shot_occupancy, fig_second_shot_occupancy, fig_total_occupancy

    def get_booking_limits(self):
        ''' '''
        params = self.kpi['params']

        if len(self.vaccine_types_used) > 1:
            num_subplots = len(self.vaccine_types_used) + 1
            subplot_titles = vaccine_types + ['All']
        else:
            num_subplots = len(self.vaccine_types_used)
            subplot_titles = vaccine_types

        fig = make_subplots(
            rows=num_subplots,
            cols=1,
            # subplot_titles=subplot_titles,
            row_titles=subplot_titles,
            shared_xaxes=True,
            shared_yaxes=True,
            vertical_spacing=0.02)

        idx = 1
        for vac in subplot_titles: #self.vaccine_types_used:

            fig_limits, inv_df = self.get_vac_booking_limits(vac)

            for data in fig_limits['data']:
                if vac != 'All':
                    data['showlegend'] = False
                else:
                    data['legendgroup'] = vac

                fig.add_trace(data, row=idx, col=1)

                if self.horizon != self.planning_horizon:
                    fig.add_vline(x=self.planning_horizon, line_width=1, line_dash="dot", line_color="dodgerblue",
                                annotation_text=f"Planning Horizon", annotation_position="top right",
                                row=idx, col=1)

                fig.add_vline(x=self.horizon, line_width=1, line_dash="dot", line_color="dodgerblue",
                            annotation_text=f"Horizon", annotation_position="top right",
                            row=idx, col=1)

            idx += 1

        # inv_waves = inv_df[inv_df['total'] > 0].index.to_list()
        # inv_waves = inv_df[0:params['duration']:params['invitation_frequency']].index.to_list()
        inv_waves = inv_df[0:self.planning_duration:params['invitation_frequency']].index.to_list()


        wave_idx = 1
        for x in inv_waves:
            fig.add_vline(x=x, line_width=1, line_dash="dash", line_color="gray",
                                annotation_text=f"Wave {wave_idx}", annotation_position="top",
                                row=num_subplots, col=1)
            wave_idx += 1

        fig.update_yaxes(rangemode="tozero")
        fig.update_layout(height=num_subplots * 400,
                    title_text='Booking Limits',
                    )
        return fig

    def get_vac_booking_limits(self, vaccine='All'):

        params = self.kpi['params']
        # Booking limit and Invitation
        # fig_limits = go.Figure()
        supply_expiry = SupplyExpiry(params['supply_scenario_display'])
        # fig_limits = supply_expiry.get_supply_expiry_figure(params['start_date'], self.longest_epoch, vaccine=vaccine, include_init=False, x_axis='num')
        fig_limits = supply_expiry.get_supply_expiry_figure(params['start_date'], self.longest_epoch, vaccine=vaccine, include_init=True, x_axis='num')

        inv_invitation = params['invitation'] + ([0] * (params['duration'] - len(params['invitation'])))

        appt_book_first = None

        if vaccine == 'All':
            first_inventory = [0]*self.longest_epoch
            second_inventory = [0]*self.longest_epoch
            # inv_target = [0]*self.longest_epoch
            # inv_invitation = [0]*self.longest_epoch

            for vac in vaccine_types:
                vac_first_inventory = np.array(params['vaccine_settings'][vac]['first_dose_booking_limit'])
                vac_second_inventory = np.array(params['vaccine_settings'][vac]['second_dose_booking_limit'])
                # vac_inv_target = np.array(params['vaccine_settings'][vac]['target'])

                vac_first_inventory = np.append(vac_first_inventory, [0]* max(0, self.longest_epoch - len(vac_first_inventory)))
                vac_second_inventory = np.append(vac_second_inventory, [0]* max(0, self.longest_epoch - len(vac_second_inventory)))
                # vac_inv_target = np.append(vac_inv_target, [0]* max(0, self.longest_epoch - len(vac_inv_target)))

                first_inventory = np.add(first_inventory, vac_first_inventory).tolist()
                second_inventory = np.add(second_inventory, vac_second_inventory).tolist()
                # inv_target = np.add(inv_target, vac_inv_target).tolist()

                vac_appt_book_first, _, _ = Params.get_appt_book(params, vac)
                if appt_book_first is None:
                    appt_book_first = vac_appt_book_first
                else:
                    appt_book_first = np.add(appt_book_first, vac_appt_book_first).tolist()

        else:
            first_inventory = np.array(params['vaccine_settings'][vaccine]['first_dose_booking_limit'])
            second_inventory = np.array(params['vaccine_settings'][vaccine]['second_dose_booking_limit'])

            first_inventory = np.append(first_inventory, [0]* max(0, self.longest_epoch - len(first_inventory)))
            second_inventory = np.append(second_inventory, [0]* max(0, self.longest_epoch - len(second_inventory)))

            first_inventory = first_inventory.tolist()
            second_inventory = second_inventory.tolist()

            # inv_target = params['vaccine_settings'][vaccine]['target']
            inv_invitation = (np.array(inv_invitation) * params['vaccine_settings'][vaccine]['invitation_split']).tolist()

            appt_book_first, _, _ = Params.get_appt_book(params, vaccine)

        df_first = pd.DataFrame(first_inventory)
        df_second = pd.DataFrame(second_inventory)

        df = pd.concat([df_first, df_second], axis=1)

        df.columns = ['first_shot', 'second_shot']
        df['total'] = df['first_shot'] + df['second_shot']

        fig_vac = px.line(df.cumsum()[['first_shot', 'second_shot', 'total']],
                            labels={
                                'index': 'Time (days)',
                                'value': '',
                                'variable': 'Booking Limits',
                                    })

        fig_vac.data[0].line.dash = 'dot'
        # fig_vac.data[0].name = f'{vaccine} First Dose Limit'
        fig_vac.data[0].name = f'First Dose Limit'
        fig_vac.data[1].line.dash = 'dot'
        # fig_vac.data[1].name = f'{vaccine} Second Dose Limit'
        fig_vac.data[1].name = f'Second Dose Limit'
        fig_vac.data[2].line.dash = 'dot'
        # fig_vac.data[2].name = f'{vaccine} Total Limit'
        fig_vac.data[2].name = f'Total Limit'

        for data in fig_vac['data']:
            # data['legendgroup'] = vaccine
            fig_limits.add_trace(data)

        # # inv_df = pd.DataFrame(params['vaccine_settings'][vac]['target'], columns=['target'])
        # inv_df = pd.DataFrame(inv_target, columns=['target'])
        # inv_df['total'] = inv_df['target']

        inv_df = pd.DataFrame(inv_invitation, columns=['invitation'])
        inv_df['appt_book_first_dose'] = appt_book_first + ([0] * (len(inv_df) - len(appt_book_first)) )
        inv_df['existing_appt_at_invitation'] = (inv_df.iloc[::-1]
                                                    .rolling(params['invitation_frequency'], min_periods=0)['appt_book_first_dose']
                                                    .sum()
                                                    .iloc[::-1])

        # inv_df.loc[inv_df['invitation']==0, 'existing_appt_at_invitation'] = 0

        # inv_df['total'] = ((inv_df['invitation'] * params['plan_response_rate']) - inv_df["existing_appt_at_invitation"]) / params['plan_response_rate']
        inv_df['total'] = inv_df['invitation']
        inv_df['cum_total'] = inv_df.cumsum()['total']

        # base = (inv_df[inv_df['total']>0]["cum_total"]).tolist()
        base = (inv_df[0:params['duration']:params['invitation_frequency']]["cum_total"]).tolist()
        base = ([0]) + base[:len(base)-1]
        # x = inv_df[inv_df['total']>0].index.tolist()
        x = inv_df[0:params['duration']:params['invitation_frequency']].index.tolist()
        # y = ((inv_df[inv_df['total']>0]['total'] - inv_df[inv_df['total']>0]["existing_appt_at_invitation"]) / params['response_rate']).tolist()
        # y = inv_df[inv_df['total']>0]['total'].tolist()
        y = inv_df[0:params['duration']:params['invitation_frequency']]['total'].tolist()
        trace_invitations = {
            "x": x,
            "y": y,
            "base": base,
            # "name": 'Target',
            "name": 'Invitations',
            "type": 'bar',
            "text": y,
            "texttemplate": '%{text:.3s}',
            "textposition": 'outside',
            "textfont_size": 12,
            # "textfont": {
            #     "family": "sans serif",
            #     "size": 18,
            # },
            "width": [4] * len(x),
            "marker": {"color": "red" if vaccine =='All' else ("purple" if vaccine=='Moderna' else "green")},
            # "legendgroup": vaccine,
        }
        # y2 = inv_df[inv_df['total']>0]["existing_appt_at_invitation"].tolist()
        y2 = inv_df[0:params['duration']:params['invitation_frequency']]["existing_appt_at_invitation"].tolist()
        trace_existing_appt = {
            "x": x,
            "y": y2,
            "base": base,
            # "name": 'Target',
            "name": 'Existing Appointments',
            "type": 'bar',
            "text": y2,
            "texttemplate": '%{text:.3s}',
            "textposition": 'outside',
            "textfont_size": 12,
            # "textfont": {
            #     "family": "sans serif",
            #     "size": 18,
            # },
            "width": [4] * len(x),
            "marker": {"color": "gray"},
            # "legendgroup": vaccine,
        }

        if vaccine == 'All':
            fig_limits.add_trace(trace_invitations)
            fig_limits.add_trace(trace_existing_appt)

        fig_limits.update_layout(
            title=f"Booking Limits & Est Invitation (Response Rate{params['response_rate']})",
            barmode='stack',
            # showlegend = True if vaccine == 'All' else False
            # showlegend=False,
        )

        return fig_limits, inv_df

    def get_report(self):
        params = self.kpi['params']
        # # inv_df = pd.DataFrame(params['demand'])
        # inv_df = pd.DataFrame(params['target'], columns=['target'])
        # # cols = list(inv_df.columns)
        # # cols.remove('old')
        # # inv_df['invitations'] = inv_df[cols].sum(axis=1)
        # inv_df['invitations'] = inv_df['target']
        # inv_df.at[0, 'invitations'] += params['init']['first_dose_appt']

        # inv_waves = inv_df[inv_df['invitations'] > 0].index

        # self.occupancy_df['date'] = pd.to_datetime(datetime.strptime(params['start_date'], "%Y-%m-%d").date())
        # self.occupancy_df['time_added'] = pd.to_timedelta(self.occupancy_df['period'],'d')
        # self.occupancy_df['date'] = self.occupancy_df['date'] + self.occupancy_df['time_added']

        # # Gather Initial Consditions
        # reset_occupancy = self.occupancy_df.reset_index(level=[0,1]).groupby('period')['first_shot', 'second_shot'].sum() / params['scale_factor']


        # # reset_occupancy['first_shot'] = reset_occupancy['first_shot'] + self.curr_appt_first_sum[:len(reset_occupancy['first_shot'])]
        # # reset_occupancy['second_shot'] = reset_occupancy['second_shot'] + self.curr_appt_second_sum[:len(reset_occupancy['second_shot'])]

        # reset_occupancy['second_shot'] = reset_occupancy['second_shot'] + np.append(self.curr_appt_second_sum, [0]* (len(reset_occupancy['second_shot']) - len(self.curr_appt_second_sum)))

        # reset_occupancy["Doses Reserved for Safety (Policy)"] = (reset_occupancy.iloc[::-1]
        #                                                 .rolling(params['saftey_reservation'], min_periods=0).second_shot
        #                                                 .sum()
        #                                                 .iloc[::-1])

        # reset_occupancy["Doses Needed for Ringfence"] = (reset_occupancy.rolling(params['saftey_reservation'], min_periods=0)['first_shot']
        #                                                 .sum())
        # reset_occupancy.at[0, "Doses Needed for Ringfence"] += params['init']['num_recieved_first_dose']
        # reset_occupancy["Doses Needed for Ringfence"] -= reset_occupancy["second_shot"]


        # reset_occupancy['total'] = reset_occupancy['first_shot'] + reset_occupancy['second_shot']

        # reset_occupancy.sort_index(inplace=True)
        # reset_occupancy['Total First Dose Administered'] = reset_occupancy['first_shot'].cumsum() + params['init']['num_completed_regimens'] + params['init']['num_recieved_first_dose']
        # reset_occupancy['Total Second Dose Administered'] = reset_occupancy['second_shot'].cumsum() + params['init']['num_completed_regimens']
        # reset_occupancy['Suggested Invitations'] = inv_df['invitations']

        # supply_expiry = SupplyExpiry(params['supply_scenario_display'])

        # # Inventory

        # supply = supply_expiry.get_supply_vector(params['start_date'], params['duration'], cumulative=False)

        # reset_occupancy['supply'] = supply + ([0]* (len(reset_occupancy) - len(supply)))
        # reset_occupancy['cum_supply'] = reset_occupancy['supply'].cumsum()
        # reset_occupancy["Incoming Supply"] = (reset_occupancy.iloc[::-1]
        #                                                 .rolling(params['saftey_reservation'], min_periods=0)['supply']
        #                                                 .sum()
        #                                                 .iloc[::-1])


        # reset_occupancy['Total Doses Remaining'] = reset_occupancy['cum_supply']  - reset_occupancy['total'].cumsum()

        # reset_occupancy['Total Doses Remaining (after safety)'] = reset_occupancy['Total Doses Remaining'] - reset_occupancy['Doses Reserved for Safety (Policy)']

        # report = reset_occupancy.iloc[inv_waves]
        # report = report[[
        #     'Doses Reserved for Safety (Policy)',
        #     'Doses Needed for Ringfence',
        #     'Total First Dose Administered',
        #     'Total Second Dose Administered',
        #     'Incoming Supply',
        #     'Total Doses Remaining',
        #     'Total Doses Remaining (after safety)',
        #     'Suggested Invitations',
        # ]].transpose()

        # return report.to_dict()
        return {}

    def generate_dashboard(self, rebuild=False):
        # def generate_dashboard(self, scenario):
        ''' '''

        if rebuild == False:
            try:
                with open(f"{self.results_dir}/dashboard.json") as dash_file:
                    dashboard = json.load(dash_file)
                    return dashboard
            except:
                pass

        self.update_stats()

        fig_vaccine_usage = self.get_vaccine_usage()

        fig_arrival = self.get_arrival_pattern()

        fig_vaccine_usage_cumulative = self.get_vaccination_rate()

        supply_expiry_fig = self.get_supply_demand()

        fig_target = self.get_target_chart()

        fig_vc_utilization = self.get_utilization()

        fig_waiting_time_hist = self.get_waiting_time()

        fig_preferred_location_hist = self.get_location_pref()

        fig_first_shot_occupancy, fig_second_shot_occupancy, fig_total_occupancy = self.get_occupancy()

        fig_limits = self.get_booking_limits()

        report = self.get_report()

        figures = {
            'fig_vaccine_usage': fig_vaccine_usage,
            'fig_vaccine_usage_cumulative': fig_vaccine_usage_cumulative,
            'fig_vc_utilization': fig_vc_utilization,
            'fig_preferred_location_hist': fig_preferred_location_hist,
            'fig_waiting_time_hist': fig_waiting_time_hist,
            'fig_first_shot_occupancy': fig_first_shot_occupancy,
            'fig_second_shot_occupancy': fig_second_shot_occupancy,
            'fig_total_occupancy': fig_total_occupancy,
            'supply_expiry_fig': supply_expiry_fig,
            'fig_target': fig_target,
            'fig_arrival': fig_arrival,
            'fig_limits': fig_limits,
        }

        # dashboard[self.params['name']] = {
        dashboard = {
            'params': self.kpi['params'],
            'results': {
                'stats': self.kpi['stats'],
                'report': report,
                # 'figures': {
                #     'fig_vaccine_usage': fig_vaccine_usage.to_json(),
                #     'fig_vc_utilization': fig_vc_utilization.to_json(),
                #     'fig_preferred_location_hist': fig_preferred_location_hist.to_json(),
                #     'fig_waiting_time_hist': fig_waiting_time_hist.to_json(),
                #     'fig_first_shot_occupancy': fig_first_shot_occupancy.to_json(),
                #     'fig_second_shot_occupancy': fig_second_shot_occupancy.to_json(),
                # },
            },
        }

        for key, fig in figures.items():
            fig.add_annotation(
                showarrow=False,
                text=self.scenario,
                xref="paper", yref="paper",
                xanchor='right',
                x=1,
                yanchor='top',
                y=-0.15
            )

            fig.write_image(f"{self.results_dir}/{key}.png")

            with open(f"{self.results_dir}/{key}.json", "w") as img_json:
                json.dump(fig.to_json(), img_json)

        with open(f"{self.results_dir}/dashboard.json", "w") as dash_file:
            json.dump(dashboard, dash_file)

        return dashboard

