import dash
import dash_bootstrap_components as dbc
from dash import dcc
import dash_daq as daq
import numpy as np
import pandas as pd
import itertools
import requests
from dash.dependencies import Input, Output, State
from flask import request
import plotly.graph_objects as go
from datetime import date

external_stylesheets = [dbc.themes.BOOTSTRAP, dbc.themes.GRID, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'padding': '30px'
    }
}

def blank_figure():
    fig = go.Figure(go.Scatter(x=[], y=[]))
    fig.update_layout(template=None)
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=True)
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=True)
    return fig

def layout():
    layout = dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody(dbc.Form([
                dash.html.P("Choose MTU:", className="control_label"),
                dbc.Row([
                    dbc.Col(
                        dcc.DatePickerSingle(
                            id='my-date-picker-single',
                            min_date_allowed=date(1995, 8, 5),
                            max_date_allowed=date(2017, 9, 19),
                            initial_visible_month=date(2017, 8, 5),
                            date=date(2017, 8, 25),
                            
                        )),
                    dbc.Col(
                        dcc.Dropdown([x for x in range(1, 25)], 1, id='demo-dropdown')
                    )
                ]),
                dash.html.Div(id='lineloading-display-transmission',
                        style={"font-size": "small", "margin-top": "10px"}),
                dbc.Checklist(
                    options=[
                        {"label": "Shift to MCP:", "value": 1},
                        {"label": "Show LTA Bounds", "value": 2},
                        ],
                    value=[],
                    id="switches-domain",
                    switch=True,
                    style={"margin-top": "10px"}
                ),
            ]))), style={"padding": "15px"}, width={"size": 4}),
            dbc.Col(
                dbc.Col(dcc.Graph(id='domain_plot', figure=blank_figure(), responsive=True, style={"height": "80vh"}), 
                width={"size": 8}, style={"padding": "15px"})),
            ])
        ], fluid=True)
    return layout

if __name__ == "__main__":
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.layout = layout()
    default_options = {
        "debug": True, 
        "use_reloader": False,
        "port": "8050", 
        "host": "127.0.0.1"
    }
    app.run_server(**default_options)
    
