import dash
import dash_auth
from vaxos.db.user_db import USERNAME_PASSWORD_PAIRS

# import dash_bootstrap_components as dbc

# app = dash.Dash(__name__, suppress_callback_exceptions=True)
# server = app.server

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# external_stylesheets = [dbc.themes.FLATLY, 'https://codepen.io/chriddyp/pen/bWLwgP.css', ]
# external_stylesheets = [dbc.themes.LUX]

from flask import Flask
server = Flask(__name__)

app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD_PAIRS)

# server = app.server
