from os import listdir
import base64
from base64 import b64encode
import pandas as pd
from flask import send_file

import dash, json, dash_table, os
import dash_core_components as dcc
# import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_html_components as html
from dash.dependencies import Input, Output, State

from vaxos.db.file_upload import FileUpload, db
from vaxos.db.status import Status
from vaxos.db.db_utils import clear_db_history
from vaxos.excel_scenario_loader import ExcelScenarioLoader
from vaxos.process_excel_server import process_excel_server

from vaxos.result_processor import ResultProcessor

# import plotly.express as px
# import plotly

from vaxos.app import app

@app.server.route('/scenario_template')
def download_csv():
    return send_file('examples/scenario_template.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet ',
                     attachment_filename='scenario_template.xlsx',
                     as_attachment=True)


layout = html.Div([

    html.Div([
        dcc.Markdown('''
        #### Scenario Upload

        1. Describe the scenario In Excel format. Click [here](/scenario_template) to download the template
        2. Name the scenario appropriately before uploading the scenario.
        3. Switch to the "Upload Scenario" tab and upload the file.
        4. Multiple sub-scenarios are automatically created by VaxOS and the execution status is accessible in the same tab.
        5. One one or more scenarios have Status='Completed" The results can be viewed using the "Dashboard" Tab

        #### Dashboard

        1. The dashboard displays Performance analytics for all the Preset and newly uploaded scenarios
        2. The interface has 2 columns, each representing performance metrics for the chosen scenario from the dropdown box.
        3. For all the Preset Scenarios, the following Naming convention is used. Using this Example:

            > ##### Stretch6_Elder6069_CPCone_29Mar_NoInit_RR80_0WRisk_NoPref_1DoseLimit
            > - **Stretch6**: Optional. Indicates scenarios with 6 weeks between 1st and 2nd Dose. If not specified, Model assumes default Inter-dose duration of 3 Weeks for Pfizer and 4 Weekd for Moderna Vaccines.
            > - **ExtSupply**: Optional. Indicates Scenarios includes supply beyond the simulation Horizon. This has been included to provide a baseline to compare the Stretch6 Scenarios
            > - **Elder6069**: Indicates Arrival Distribution
            > - **CPCone \ Aggressive \ Current**: Solver choice
            >     - **CPCone**: Booking Limits generated using Liner Program and Invitation Schedule generated using Co-Positive Cone Model
            >     - **Agressive**: Booking Limits generated using Liner Program and Invitation Schedule generated using An Aggressive heuristic
            >     - **Current**: Booking Limits generated using Reimen count and Invitation Schedule manually updated from Current policy
            > - **29Mar**: Start date of the planning Horizon
            > - **NoInit \ WithInit**: Specifies Initial condition setup.
            > - **RR80**: % Response Rate of the Invited Population. Used to genetate arrivals in the Simulation model.
            > - **0WRisk**: Specifies Protection level for 2nd Dose inventory. Risk is the reverse of Reservation and is specified based of the Inter-Dose Duration.
            > - **NoPref \ PzPref70**: Specifies the choice model for Vaccine Preference.
            >     - **NoPref**: Indicates That an individual doe not have a preference for type of Vaccine.
            >     - **PzPref70**: indicates 70% of individuals prefer Pfizer as their only vaccine Choice. The reminder prefer the Alternate vaccine.
            > - **1DoseLimit \ 2DoseLimit**: Control Policy
            >     - **1DoseLimit**: Appointment book applies only First dose Booking Limit Control
            >     - **2DoseLimit**: Appointment book applies both First and Second Dose Booking Limit Controls.

        4. The Dashboard contains a Table and a collection of Charts to demonstrate performance of each scenario.
        5. The Two columns of Dashboard can be used to Compare 2 scenarios side by side. Do ensure that the scenarios a valid comparison (specifically with reg to Input dataset)

        ''')], className='eight columns'),

    html.Div([
        html.H3('Admin'),
        html.Button("Rebuild All Scenarios",
                    id='rebuild_all_scenarios', n_clicks=0,
                    style={'color': 'red'}),

    ], className='four columns'),
    # html.H3('Scenario Upload'),
    # html.Ol([
    #     html.Li([
    #         html.P('Describe the scenario In Excel format. Click'),
    #         html.A('here', href='/examples/scenatio_template.xlsx'),
    #         html.P('to download the template'),
    #         ]),
    #     html.Li(),
    #     html.Li(),
    #     html.Li(),
    # ]),


], className="row",
        style={'margin-top':'8%',})


@app.callback(Output('rebuild_all_scenarios', 'n_clicks'),
            Input('rebuild_all_scenarios', 'n_clicks'),
            )
def rebuild_all_scenarios(n):

    if n > 0:
        ResultProcessor.rebuild_all()

    return 0

