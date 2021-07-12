import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
# import dash_bootstrap_components as dbc

from vaxos.app import app, server
from vaxos.apps import dashboard_app, upload_scenario_app, user_guide_app



# dropdown_menu = dbc.DropdownMenu(
#     children=[
#         dbc.DropdownMenuItem("Dashboard", href="/dashboard"),
#         dbc.DropdownMenuItem("UploadScenario", href="/upload_scenario"),
#     ],
#     nav = True,
#     in_navbar = True,
#     label = "Menu",
# )

# navbar = dbc.Navbar(
#     dbc.Container(
#         [
#             html.Div([
#                 html.Div([
#                     html.Img(src='/static/CoBrand-IORA_H-web-1.png',style={'width':'90%', 'margin': '5%'}),
#                 ], className="two columns"),
#                 html.Div([
#                     html.H1(children='Vaccine Deployment Simulator'),
#                 ], className="ten columns"),
#             ], className="row",
#             ),
#             dbc.NavbarToggler(id="navbar-toggler2"),
#             dbc.Collapse(
#                 dbc.Nav(
#                     # right align dropdown menu with ml-auto className
#                     [dropdown_menu], className="ml-auto", navbar=True
#                 ),
#                 id="navbar-collapse2",
#                 navbar=True,
#             ),
#         ]
#     ),
#     # color="dark",
#     # dark=True,
#     # className="mb-4",
# )

# def toggle_navbar_collapse(n, is_open):
#     if n:
#         return not is_open
#     return is_open

# for i in [2]:
#     app.callback(
#         Output(f"navbar-collapse{i}", "is_open"),
#         [Input(f"navbar-toggler{i}", "n_clicks")],
#         [State(f"navbar-collapse{i}", "is_open")],
#     )(toggle_navbar_collapse)

# # embedding the navigation bar
# app.layout = html.Div([
#     dcc.Location(id='url', refresh=False),
#     navbar,
#     html.Div(id='page-content')
# ])


# @app.callback(Output('page-content', 'children'),
#               Input('url', 'pathname'))
# def display_page(pathname):
#     # print(pathname)
#     if pathname == '/dashboard':
#         return dashboard_app.layout
#     elif pathname == '/upload_scenario':
#         return 'Hello World'
#     else:
#         return '404'

tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '6px'
}

app.layout = html.Div([
    html.Div([
        html.Div([
            html.Div([
                html.Img(src='/static/CoBrand-IORA_H-web-1.png',style={
                    'height': '50px', 'margin': '15px',
                # 'width':'240px',
                }),
            ], className="two columns", style={}),
            html.Div([
                html.Img(src='/static/VaxOSLogo_thin.png',style={'height': '50px','margin': '15px',}),
            ], className="ten columns"),
                # html.Div([
                #     html.H4(children='(Vaccine Appointments Optimization Suite)')
                # ]),
        ], className="row",),

        # dcc.Tabs(id='tab_app_chooser', value='upload_scenario', children=[
        #     dcc.Tab(label='Scenario', value='upload_scenario'),
        #     dcc.Tab(label='Dashboard', value='dashboard'),
        # ]),
        dcc.Tabs(
            id="tab_app_chooser",
            value='dashboard',
            children=[
                dcc.Tab(
                    label='Dashboard',
                    value='dashboard',
                    style=tab_style, selected_style=tab_selected_style
                ),
                dcc.Tab(
                    label='Upload Scenario',
                    value='upload_scenario',
                    style=tab_style, selected_style=tab_selected_style
                ),
                dcc.Tab(
                    label='User Guide',
                    value='user_guide',
                    style=tab_style, selected_style=tab_selected_style
                )
                ], style=tabs_styles,
            ),
        html.Div(id='tabs-content-classes')
    ], className="row",
        style={'background-color':'white',
            'height': '140px', #'14%',
            'position':'fixed',
            'top':'0', 'width':'100%',
            'zIndex':'99',
        },
    ),

    html.Div(id='tab-content')

    # dcc.Location(id='url', refresh=False),
    # html.Div(id='page-content')
])


@app.callback(Output('tab-content', 'children'),
              Input('tab_app_chooser', 'value'))
def render_content(tab):
    if tab == 'upload_scenario':
        return upload_scenario_app.layout
    elif tab == 'dashboard':
        return dashboard_app.layout
    elif tab == 'user_guide':
        return user_guide_app.layout


def run_server():
    app.run_server(debug=True, host='0.0.0.0', port=8050)


if __name__ == '__main__':
    run_server()
    # app.run_server(debug=True, host='0.0.0.0')
