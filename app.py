import datetime as dt
import itertools

import dash
import dash_bootstrap_components as dbc
import dash_daq as daq
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from dash import dcc
from dash.dependencies import Input, Output, State
from flask import request

from FBDomainViewer.fbmc_data import load_data, lta_constraints
from FBDomainViewer.fbmc_domain import FBDomainPlots
from FBDomainViewer.plot import create_fb_domain_plot

external_stylesheets = [dbc.themes.BOOTSTRAP, dbc.themes.GRID, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'padding': '30px'
    }
}

HUBS = ['AT', 'BE', 'CZ', 'DE', 'FR', 'HR', 'HU', 'NL', 'PL', 'RO', 'SI', 'SK']

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
                dash.html.Div([
                    dcc.DatePickerSingle(
                        id='date-picker',
                        min_date_allowed=dt.date(2022, 6, 9),
                        max_date_allowed=dt.date.today(),
                        initial_visible_month=dt.date(2022, 9, 17),
                        date=dt.date(2022, 9, 17)
                    ),
                    dcc.Input(
                        id="hour-selection", type="number", placeholder="Choose Hour",
                        min=0, max=23, step=1, value=22, size="6"),
                ]),
                dash.html.P("Choose BZs for X-Axis:", className="control_label"),
                dash.html.Div(
                    [
                        dcc.Dropdown(HUBS, id="x-domain-1", placeholder="", value="DE"),
                        dcc.Dropdown(HUBS, id="x-domain-2", placeholder="", value="FR")
                    ], style={"display": "inline-flex"}
                ),           
                dash.html.P("Choose BZs for Y-Axis:", className="control_label"),
                dash.html.Div(
                    [
                        dcc.Dropdown(HUBS, id="y-domain-1", placeholder="", value="DE"),
                        dcc.Dropdown(HUBS, id="y-domain-2", placeholder="", value="NL")
                    ], style={"display": "inline-flex"}
                ), 
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
            ]))), style={"padding": "15px"}, width={"size": 2}),
            dbc.Col(
                dbc.Col(dcc.Graph(id='domain-plot', figure=blank_figure(), responsive=True, style={"height": "80vh"}), 
                width={"size": 10}, style={"padding": "15px"})),
            ])
        ], fluid=True)
    return layout

def add_callbacks(app):
    @app.callback(
        Output(component_id='domain-plot', component_property='figure'),
        Input(component_id='date-picker', component_property='date'),
        Input(component_id='hour-selection', component_property='value'),
        Input(component_id='switches-domain', component_property='value'),
        Input(component_id='x-domain-1', component_property='value'),
        Input(component_id='x-domain-2', component_property='value'),
        Input(component_id='y-domain-1', component_property='value'),
        Input(component_id='y-domain-2', component_property='value'),
    )
    def update_domain_plot(date, hour, switches, x_domain_1, x_domain_2, y_domain_1, y_domain_2):
        shift_mcp = True if 1 in switches else False
        show_lta = True  if 2 in switches else False

        if not all(s in HUBS for s in [x_domain_1, x_domain_2, y_domain_1, y_domain_2]):
            return blank_figure()

        domain_x = [x_domain_1, x_domain_2]
        domain_y = [y_domain_1, y_domain_2]

        mtu = pd.Timestamp(f"{date}T{str(hour)}:00:00.000Z")
        
        data = load_data(mtu)
        exchange = data["exchange"]
        domain = data["domain"].copy()
        zones = data["zones"]
        mcp=data["mcp"]
        lta = data["lta"]
        ltn = data["ltn"]

        
        if mcp.loc["ALBE"] > 0:
            albe_exchange = pd.DataFrame(index=[("ALBE", "ALDE")], data=[mcp.loc["ALBE"]], columns=["exchange"])
        else:
            albe_exchange = pd.DataFrame(index=[("ALDE", "ALBE")], data=[mcp.loc["ALDE"]], columns=["exchange"])
        exchange = pd.concat([exchange, albe_exchange])
        
        fbmc = FBDomainPlots(zones, domain)

        timestep = domain.timestep.unique()[0]
        fb_domain = fbmc.generate_flowbased_domain(
            domain_x=domain_x, 
            domain_y=domain_y, 
            timestep=timestep, 
            exchange=exchange if shift_mcp else None, 
            # lta=lta
        )
        fig = create_fb_domain_plot(
            fb_domain, 
            exchange, 
            zones, 
            lta if show_lta else None, show_plot=False)
        return fig


if __name__ == "__main__":
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.layout = layout()
    add_callbacks(app)
    default_options = {
        "debug": True, 
        "threaded": True, 
        "use_reloader": True,
        "port": "8050", 
        "host": "127.0.0.1"
    }
    app.run_server(**default_options)
    
