from os import listdir
import base64
from base64 import b64encode
import pandas as pd

import dash, json, dash_table, os
import dash_core_components as dcc
# import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_html_components as html
from dash.dependencies import Input, Output, State

from vaxos.db.file_upload import FileUpload, db
from vaxos.db.status import Status
from vaxos.db.db_utils import clear_db_history, purge_db_history
from vaxos.excel_scenario_loader import ExcelScenarioLoader
from vaxos.process_excel_server import process_excel_server

# import plotly.express as px
# import plotly

from vaxos.app import app

UPLOAD_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/inputs/excel"


layout = html.Div([

    html.Div([
        html.Div([
            html.Div([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select File')
                    ]),
                    style={
                        # 'position-top':'fixed',
                        # 'top':'300px',
                    #     'padding-top': '10px',
                        'width': '80%',
                        'height': '300px',
                        'lineHeight': '300px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin-left': '10%',
                        'margin-right': '10%',
                        'background-color': '#CCFFFF',
                        '-webkit-box-shadow': '0 6px 6px -6px #777',
                        '-moz-box-shadow': '0 6px 6px -6px #777',
                        'box-shadow': '0 6px 6px -6px #777',
                        'zIndex': '199',
                    },
                    # Allow multiple files to be uploaded
                    multiple=False
                ),
                html.H3(children='Recent Uploads'),
                html.Div(id='output-data-upload',
                        style={
                            'width': '80%',
                            'margin-left': '10%',
                            'margin-right': '10%',
                        }
                    ),
                html.Div(style={
                            'width': '100%',
                            'height': '40px'
                        }),

                html.Button('Clear History', id='clear-history', n_clicks=0,
                        style={
                            'width': '80%',
                            'margin-left': '10%',
                            'margin-right': '10%',
                        }
                    ),
                html.Div(style={
                            'width': '100%',
                            'height': '40px'
                        }),
                html.Button('Purge DB', id='purge-db', n_clicks=0,
                        style={
                            'width': '80%',
                            'margin-left': '10%',
                            'margin-right': '10%',
                        }
                    ),
            ], className="six columns"),

            html.Div([
                html.H3(children='Recent Scenarios'),
                html.Div(id='execution_status',
                        style={
                            'width': '95%',
                        }
                    ),
            ], className="six columns"),
        ], className="row",
        style={'margin-top':'8%',}
        ),
    ]),

    dcc.Interval(id='refresh_timer', interval= 1 * 1000, n_intervals=0),
    html.Div(id='dummy_1', style={'display': 'none'})
])

def save_file(name, content):
    """Decode and store a file uploaded with Plotly Dash."""
    # print(type(content))
    data = content.encode("utf8").split(b";base64,")[1]
    # print(data)
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))
        # fp.write(content)

    process_excel_server()


# def uploaded_files():
#     """List the files in the upload directory."""
#     files = []
#     for filename in os.listdir(UPLOAD_DIRECTORY):
#         path = os.path.join(UPLOAD_DIRECTORY, filename)
#         if os.path.isfile(path):
#             files.append(filename)
#     return files

@app.callback(Output('clear-history', 'n_clicks'),
            Input('clear-history', 'n_clicks'),
            )
def clear_history(n):

    if n > 0:
        clear_db_history()

    return 0

@app.callback(Output('purge-db', 'n_clicks'),
            Input('purge-db', 'n_clicks'),
            )
def clear_history(n):

    if n > 0:
        purge_db_history()

    return 0



@app.callback(Output('refresh_timer', 'disabled'),
            [Input("upload-data", "filename"),
            Input("upload-data", "contents")],)
def process_file_upload(filename, content):
    # print(filename)
    # print(content)
    if filename is not None and content is not None:
        # for name, data in zip(filename, content):
        save_file(filename, content)

        # excel_loader = ExcelScenarioLoader(filename)
        # excel_loader.run_all()


    # files = uploaded_files()
    # if len(files) == 0:
    #     return [html.Li("No files yet!")]
    # else:
    #     return [html.Li(file) for file in files]
    return False


@app.callback([Output('output-data-upload', 'children'),
                Output('execution_status', 'children')],
            [Input("refresh_timer", "n_intervals"),],)
def refrest_upload_status(n):
    # print(n)

    upload_query = (FileUpload.select()
            .order_by(FileUpload.processing_date.desc())
            # .limit(5)
            )

    upload_df = pd.read_sql(upload_query.sql()[0], db.connection())

    upload_status = dash_table.DataTable(
        id='table',
        style_cell={
            'textAlign': 'left',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        columns=[{"name": i, "id": i} for i in upload_df.columns],
        data=upload_df.head(10).to_dict('records'),
    )


    scenario_query = (Status.select()
            .order_by(Status.init_date.desc())
            # .limit(5)
            )

    scenario_df = pd.read_sql(scenario_query.sql()[0], db.connection())

    scenario_status = dash_table.DataTable(
        id='table',
        style_cell={
            'textAlign': 'left',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        columns=[{"name": i, "id": i} for i in scenario_df.columns],
        data=scenario_df.head(10).to_dict('records'),
    )


    return upload_status, scenario_status
