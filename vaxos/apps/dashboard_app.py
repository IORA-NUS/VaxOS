from os import listdir
from base64 import b64encode

import dash, json, dash_table, os
import dash_core_components as dcc
# import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_html_components as html

from dash.dependencies import Input, Output, State

import pandas as pd

import plotly.express as px
import plotly.graph_objects as go
import plotly

from vaxos.app import app

# from supply_expiry import supply_expiry_fig
from vaxos.result_processor import ResultProcessor

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


scenarios = ResultProcessor.get_scenarios # NOTE THIS IS A FUNCTION

# summary_stats = ResultProcessor().get_summary_stats()
# df = pd.DataFrame.from_dict(summary_stats)

def generate_dashboard(scenario_id, static_image=True):
    # static_image = True
    if scenario_id == None:
        return (
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            dcc.Graph(figure=go.Figure(layout=go.Layout(title=go.layout.Title(text="Figure Not Generated")))),
            "Static" if static_image == True else "Interactive"
        )

    # current = ResultProcessor().generate_dashboard(scenario_id)
    current = ResultProcessor(scenario_id).generate_dashboard()

    current_params = current['params'].copy()
    # current_params.pop('capacity')
    # current_params.pop('location')
    df = pd.DataFrame(list(current_params.items()),columns = ['Key', 'Value'])
    for index, row in df.iterrows():
        if type(row['Value']) is dict or type(row['Value']) is list:
            row['Value'] = json.dumps(row['Value'])
        # if type(row['Value']) is list:
        #     row['Value'] = ', '.join([str(v) for v in row['Value']])

    params_table = dash_table.DataTable(
        id='params_table',
        style_cell={
            'textAlign': 'left',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
    )

    current_stats = current['results']['stats'].copy()
    current_stats.pop('Arrival')
    current_stats.pop('Capacity')
    current_stats.pop('TPut Percentile (by Period)')

    df = pd.DataFrame(list(current_stats.items()),columns = ['Key', 'Value'])
    for index, row in df.iterrows():
        if type(row['Value']) is dict or type(row['Value']) is list:
            row['Value'] = json.dumps(row['Value'])
        # if type(row['Value']) is list:
        #     row['Value'] = ', '.join([str(v) for v in row['Value']])

    stats_table = dash_table.DataTable(
        id='stats_table',
        style_cell={
            'textAlign': 'left',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
    )

    # report = current['results']['report'].copy()
    # # df = pd.DataFrame(list(report.items()),columns = ['Key', 'Value'])
    # df = pd.DataFrame(report)
    # report_table = dash_table.DataTable(
    #     id='report_table',
    #     style_cell={
    #         'textAlign': 'left',
    #         'whiteSpace': 'normal',
    #         'height': 'auto',
    #     },
    #     columns=[{"name": i, "id": i} for i in df.columns],
    #     data=df.to_dict('report'),
    # )


    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    results_dir = f"{dir_path}/results/{scenario_id}"

    if static_image == True:

        img_b64 = b64encode(open(f"{results_dir}/supply_expiry_fig.png", 'rb').read())
        supply_expiry_fig_graph = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_target.png", 'rb').read())
        fig_target = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_limits.png", 'rb').read())
        fig_limits = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_arrival.png", 'rb').read())
        fig_arrival = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_vaccine_usage_cumulative.png", 'rb').read())
        fig_vaccine_usage_cumulative = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        # img_b64 = b64encode(open(f"results/{scenario_id}/fig_vaccine_usage.png", 'rb').read())
        # fig_vaccine_usage = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        # img_b64 = b64encode(open(f"results/{scenario_id}/fig_vc_utilization.png", 'rb').read())
        # fig_vc_utilization = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_waiting_time_hist.png", 'rb').read())
        fig_waiting_time_hist = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_preferred_location_hist.png", 'rb').read())
        fig_preferred_location_hist = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        img_b64 = b64encode(open(f"{results_dir}/fig_total_occupancy.png", 'rb').read())
        fig_total_occupancy = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        # img_b64 = b64encode(open(f"results/{scenario_id}/fig_first_shot_occupancy.png", 'rb').read())
        # fig_first_shot_occupancy = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        # img_b64 = b64encode(open(f"results/{scenario_id}/fig_second_shot_occupancy.png", 'rb').read())
        # fig_second_shot_occupancy = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))

        try:
            img_b64 = b64encode(open(f"{results_dir}/inventory_robustness.png", 'rb').read())
            fig_inventory_robustness = html.Img(src='data:image/png;base64,{}'.format(img_b64.decode()))
        except:
            fig_inventory_robustness = dcc.Graph(figure=go.Figure())

    else:
        with open(f"{results_dir}/supply_expiry_fig.json") as fig_json:
            supply_expiry_fig_graph = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_target.json") as fig_json:
            fig_target = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_limits.json") as fig_json:
            fig_limits = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_arrival.json") as fig_json:
            fig_arrival = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_vaccine_usage_cumulative.json") as fig_json:
            fig_vaccine_usage_cumulative = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        # with open(f"{results_dir}/fig_vaccine_usage.json") as fig_json:
        #     fig_vaccine_usage = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        # with open(f"{results_dir}/fig_vc_utilization.json") as fig_json:
        #     fig_vc_utilization = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_waiting_time_hist.json") as fig_json:
            fig_waiting_time_hist = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_preferred_location_hist.json") as fig_json:
            fig_preferred_location_hist = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        with open(f"{results_dir}/fig_total_occupancy.json") as fig_json:
            fig_total_occupancy = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        # with open(f"{results_dir}/fig_first_shot_occupancy.json") as fig_json:
        #     fig_first_shot_occupancy = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        # with open(f"{results_dir}/fig_second_shot_occupancy.json") as fig_json:
        #     fig_second_shot_occupancy = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        try:
            with open(f"{results_dir}/inventory_robustness.json") as fig_json:
                fig_inventory_robustness = dcc.Graph(figure=plotly.io.from_json(json.load(fig_json)))
        except:
            fig_inventory_robustness = dcc.Graph(figure=go.Figure(
                layout=go.Layout(title=go.layout.Title(text="Figure Not Generated"))))


    return (
            # params_table,
            stats_table,
            # report_table,
            supply_expiry_fig_graph,
            fig_target,
            fig_limits,
            fig_arrival,
            fig_vaccine_usage_cumulative,
            # fig_vaccine_usage,
            # fig_vc_utilization,
            fig_waiting_time_hist,
            fig_preferred_location_hist,
            fig_total_occupancy,
            # fig_first_shot_occupancy,
            # fig_second_shot_occupancy,
            fig_inventory_robustness,
            "Static" if static_image == True else "Interactive",
            scenario_id,
        )



layout = html.Div(children=[

    html.Div([
        # html.Div([
        #     html.Div([
        #         html.Img(src='/static/CoBrand-IORA_H-web-1.png',style={'width':'90%', 'margin': '5%'}),
        #     ], className="two columns"),
        #     html.Div([
        #         html.H1(children='Vaccine Deployment Simulator'),
        #     ], className="ten columns"),
        # ], className="row",
        # ),
        html.Div([

            html.Div([
                dcc.Dropdown(
                    id='scenario-dropdown-left',
                    persistence=True,
                    options=[{'label': s, 'value': s} for s in scenarios()],
                    value=None if len(scenarios()) == 0 else scenarios()[0]
                ),
            ], className="ten columns"),
            html.Div([
                daq.BooleanSwitch(
                    id='static-image-left',
                    on=True,
                    persistence=True,
                    label='Static',
                    labelPosition='bottom'
                ),
            ], className="two columns"),
            html.Div(id='current_scenario-left', children='', style={'display': 'none'}),
            html.Div(id='current_static_image-left', children='', style={'display': 'none'})
        ], className="six columns",
            style={'margin-left':'0',}
        ),

        html.Div([

            html.Div([
                dcc.Dropdown(
                    id='scenario-dropdown-right',
                    persistence=True,
                    options=[{'label': s, 'value': s} for s in scenarios()],
                    # value=scenarios()[0]
                    value=None if len(scenarios()) == 0 else scenarios()[0]
                ),
            ], className="ten columns"),
            html.Div([
                daq.BooleanSwitch(
                    id='static-image-right',
                    on=True,
                    persistence=True,
                    label='Static',
                    labelPosition='bottom'
                ),
            ], className="two columns"),
            html.Div(id='current_scenario-right', children='', style={'display': 'none'}),
            html.Div(id='current_static_image-right', children='', style={'display': 'none'})
        ], className="six columns",),

    ], className="row",
        style={'background-color':'white',
        # 'height':'14%',
        'position':'fixed',
        'top':'140px', 'width':'100%',
        'padding-top': '10px',
        'zIndex':'99',
        '-webkit-box-shadow': '0 6px 6px -6px #777',
        '-moz-box-shadow': '0 6px 6px -6px #777',
        'box-shadow': '0 6px 6px -6px #777',
        },
    ),

    html.Div([
        # html.Div([
        #     html.Div([
        #         html.H3(children='Input Parameters'),
        #         html.Div(id='params-table-left'),
        #     ], className="six columns"),

        #     html.Div([
        #         html.H3(children='Input Parameters'),
        #         html.Div(id='params-table-right'),
        #     ], className="six columns"),
        # ], className="row"),

        html.Div([
            html.Div([
                html.H3(children='Output Stats'),
                html.Div(id='stats-table-left'),
            ], className="six columns"),

            html.Div([
                html.H3(children='Output Stats'),
                html.Div(id='stats-table-right'),
            ], className="six columns"),
        ], className="row"),

        # html.Div([
        #     html.Div([
        #         html.H3(children='Report'),
        #         html.Div(id='report-table-left'),
        #     ], className="six columns"),

        #     html.Div([
        #         html.H3(children='Report'),
        #         html.Div(id='report-table-right'),
        #     ], className="six columns"),
        # ], className="row"),

        html.Div([
            html.Div(id='supply_expiry_fig_graph-left',
                className="six columns"),

            html.Div(id='supply_expiry_fig_graph-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_target-left',
                className="six columns"),

            html.Div(id='fig_target-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_limits-left',
                className="six columns"),

            html.Div(id='fig_limits-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_arrival-left',
                className="six columns"),

            html.Div(id='fig_arrival-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_vaccine_usage_cumulative-left',
                className="six columns"),

            html.Div(id='fig_vaccine_usage_cumulative-right',
                className="six columns"),
        ], className="row"),

        # html.Div([
        #     html.Div(id='fig_vaccine_usage-left',
        #         className="six columns"),

        #     html.Div(id='fig_vaccine_usage-right',
        #         className="six columns"),
        # ], className="row"),

        # html.Div([
        #     html.Div(id='fig_vc_utilization-left',
        #         className="six columns"),

        #     html.Div(id='fig_vc_utilization-right',
        #         className="six columns"),
        # ], className="row"),


        html.Div([
            html.Div(id='fig_waiting_time_hist-left',
                className="six columns"),

            html.Div(id='fig_waiting_time_hist-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_preferred_location_hist-left',
                className="six columns"),

            html.Div(id='fig_preferred_location_hist-right',
                className="six columns"),
        ], className="row"),

        html.Div([
            html.Div(id='fig_total_occupancy-left',
                className="six columns"),

            html.Div(id='fig_total_occupancy-right',
                className="six columns"),

        ], className="row"),

        # html.Div([
        #     html.Div(id='fig_first_shot_occupancy-left',
        #         className="six columns"),

        #     html.Div(id='fig_first_shot_occupancy-right',
        #         className="six columns"),

        # ], className="row"),

        # html.Div([
        #     html.Div(id='fig_second_shot_occupancy-left',
        #         className="six columns"),

        #     html.Div(id='fig_second_shot_occupancy-right',
        #         className="six columns"),
        # ], className="row"),

        html.Div([
            html.Div(id='fig_inventory_robustness-left',
                className="six columns"),

            html.Div(id='fig_inventory_robustness-right',
                className="six columns"),

        ], className="row"),

    ], className="row",
        style={'margin-top':'8%',}
    ),
])

@app.callback(
    dash.dependencies.Output('scenario-dropdown-left', 'options'),
    [dash.dependencies.Input('scenario-dropdown-left', 'value')]
)
def update_date_dropdown(name):
    return [{'label': s, 'value': s} for s in scenarios()]

@app.callback(
    dash.dependencies.Output('scenario-dropdown-right', 'options'),
    [dash.dependencies.Input('scenario-dropdown-right', 'value')]
)
def update_date_dropdown(name):
    return [{'label': s, 'value': s} for s in scenarios()]


@app.callback([
        # Output('params-table-left', 'children'),
        Output('stats-table-left', 'children'),
        # Output('report-table-left', 'children'),
        Output('supply_expiry_fig_graph-left', 'children'),
        Output('fig_target-left', 'children'),
        Output('fig_limits-left', 'children'),
        Output('fig_arrival-left', 'children'),
        Output('fig_vaccine_usage_cumulative-left', 'children'),
        # Output('fig_vaccine_usage-left', 'children'),
        # Output('fig_vc_utilization-left', 'children'),
        Output('fig_waiting_time_hist-left', 'children'),
        Output('fig_preferred_location_hist-left', 'children'),
        Output('fig_total_occupancy-left', 'children'),
        # Output('fig_first_shot_occupancy-left', 'children'),
        # Output('fig_second_shot_occupancy-left', 'children'),
        Output('fig_inventory_robustness-left', 'children'),
        Output('static-image-left', 'label'),
        Output('current_scenario-left', 'children'),
    ],
    [
        Input('scenario-dropdown-left', 'value'),
        Input('static-image-left', 'on'),
    ],
    [
        State('current_scenario-left', 'children'),
        State('current_static_image-left', 'value'),
        State('stats-table-left', 'children'),
        State('supply_expiry_fig_graph-left', 'children'),
        State('fig_target-left', 'children'),
        State('fig_limits-left', 'children'),
        State('fig_arrival-left', 'children'),
        State('fig_vaccine_usage_cumulative-left', 'children'),
        State('fig_waiting_time_hist-left', 'children'),
        State('fig_preferred_location_hist-left', 'children'),
        State('fig_total_occupancy-left', 'children'),
        State('fig_inventory_robustness-left', 'children'),
    ])
def update_output_left(scenario_id, static_image,
                    current_scenario,
                    current_static_image,
                    stats_table,
                    supply_expiry_fig_graph,
                    fig_target,
                    fig_limits,
                    fig_arrival,
                    fig_vaccine_usage_cumulative,
                    fig_waiting_time_hist,
                    fig_preferred_location_hist,
                    fig_total_occupancy,
                    fig_inventory_robustness,
                    ):

    if (current_scenario == scenario_id) and (current_static_image == static_image):
        return (stats_table,
                supply_expiry_fig_graph,
                fig_target,
                fig_limits,
                fig_arrival,
                fig_vaccine_usage_cumulative,
                fig_waiting_time_hist,
                fig_preferred_location_hist,
                fig_total_occupancy,
                fig_inventory_robustness,
                current_scenario,
            )
    else:

        return generate_dashboard(scenario_id, static_image)


@app.callback([
        # Output('params-table-right', 'children'),
        Output('stats-table-right', 'children'),
        # Output('report-table-right', 'children'),
        Output('supply_expiry_fig_graph-right', 'children'),
        Output('fig_target-right', 'children'),
        Output('fig_limits-right', 'children'),
        Output('fig_arrival-right', 'children'),
        Output('fig_vaccine_usage_cumulative-right', 'children'),
        # Output('fig_vaccine_usage-right', 'children'),
        # Output('fig_vc_utilization-right', 'children'),
        Output('fig_waiting_time_hist-right', 'children'),
        Output('fig_preferred_location_hist-right', 'children'),
        Output('fig_total_occupancy-right', 'children'),
        # Output('fig_first_shot_occupancy-right', 'children'),
        # Output('fig_second_shot_occupancy-right', 'children'),
        Output('fig_inventory_robustness-right', 'children'),
        Output('static-image-right', 'label'),
        Output('current_scenario-right', 'children'),
    ],
    [
        Input('scenario-dropdown-right', 'value'),
        Input('static-image-right', 'on'),
    ],
    [
        State('current_scenario-right', 'value'),
        State('current_static_image-right', 'value'),
        State('stats-table-right', 'children'),
        State('supply_expiry_fig_graph-right', 'children'),
        State('fig_target-right', 'children'),
        State('fig_limits-right', 'children'),
        State('fig_arrival-right', 'children'),
        State('fig_vaccine_usage_cumulative-right', 'children'),
        State('fig_waiting_time_hist-right', 'children'),
        State('fig_preferred_location_hist-right', 'children'),
        State('fig_total_occupancy-right', 'children'),
        State('fig_inventory_robustness-right', 'children'),
    ])
def update_output_right(scenario_id, static_image,
                    current_scenario,
                    current_static_image,
                    stats_table,
                    supply_expiry_fig_graph,
                    fig_target,
                    fig_limits,
                    fig_arrival,
                    fig_vaccine_usage_cumulative,
                    fig_waiting_time_hist,
                    fig_preferred_location_hist,
                    fig_total_occupancy,
                    fig_inventory_robustness,
                    ):
    if (current_scenario == scenario_id) and (current_static_image == static_image):
        return (stats_table,
                supply_expiry_fig_graph,
                fig_target,
                fig_limits,
                fig_arrival,
                fig_vaccine_usage_cumulative,
                fig_waiting_time_hist,
                fig_preferred_location_hist,
                fig_total_occupancy,
                fig_inventory_robustness,
                current_scenario,
            )
    else:
        return generate_dashboard(scenario_id, static_image)


# if __name__ == '__main__':
#     app.run_server(debug=True, host='0.0.0.0')
