import datetime as dt

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from dash import dcc
from dash.dependencies import Input, Output, State

from FBDomainViewer.fbmc_data import load_data
from FBDomainViewer.fbmc_domain import FBDomainPlots
from FBDomainViewer.lta_domain import create_lta_domain, create_lta_domain_new, calculate_FB_exchange
from FBDomainViewer.plot import create_fb_domain_plot

external_stylesheets = [dbc.themes.BOOTSTRAP, dbc.themes.GRID, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'padding': '30px'
    }
}

HUBS = ['AT', 'BE', 'CZ', 'DE', 'FR', 'HR', 'HU', 'NL', 'PL', 'RO', 'SI', 'SK']

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "15em",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
    "zIndex": 10
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "15em",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}


def blank_figure():
    fig = go.Figure(go.Scatter(x=[], y=[]))
    fig.update_layout(template=None)
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=True)
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=True)
    return fig

def layout():
    sidebar = dash.html.Div(
        [
            dash.html.P("Choose MTU:", className="control_label"),
            dash.html.Div([
                dcc.DatePickerSingle(
                    id='date-picker',
                    min_date_allowed=dt.date(2022, 6, 9),
                    max_date_allowed=dt.date.today(),
                    initial_visible_month=dt.date(2022, 9, 17),
                    date=dt.date(2022, 9, 17),
                ),
                dcc.Input(
                    id="hour-selection", type="number", placeholder="Choose Hour",
                    min=0, max=23, step=1, value=22, size="6"),
                ],
                style={"display": "inline-flex"}
            ),
            dash.html.P("Choose BZs for X-Axis:", className="control_label", style={"margin-top": "2em"}),
            dash.html.Div(
                [
                    dcc.Dropdown(HUBS, id="x-domain-1", placeholder="", value="DE"),
                    dcc.Dropdown(HUBS, id="x-domain-2", placeholder="", value="FR")
                ], 
                # style={"display": "inline-flex"}
            ),           
            dash.html.P("Choose BZs for Y-Axis:", className="control_label", style={"margin-top": "2em"}),
            dash.html.Div(
                [
                    dcc.Dropdown(HUBS, id="y-domain-1", placeholder="", value="DE"),
                    dcc.Dropdown(HUBS, id="y-domain-2", placeholder="", value="NL")
                ], 
                # style={"display": "inline-flex"}
            ), 
            dash.html.Div(id='lineloading-display-transmission',
                    style={"font-size": "small", "margin-top": "2em"}),
            dbc.Checklist(
                options=[
                    {"label": "Shift to MCP:", "value": 1},
                    {"label": "Show LTA Bounds", "value": 2},
                    {"label": "Show LTA Bounds 2", "value": 3},
                    ],
                value=[],
                id="switches-domain",
                switch=True,
                # style={"margin-top": "10px"}
            ),
        ],
        style=SIDEBAR_STYLE,
    )

    content = dash.html.Div(
        [
            dcc.Graph(
                id='domain-plot', figure=blank_figure(), 
                responsive=True, 
                style={"height": "90vh"}
            ),
        ],
        id="page-content", style=CONTENT_STYLE)
    return dash.html.Div([sidebar, content])

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
        show_lta = True if 2 in switches else False
        show_lta_2 = True if 3 in switches else False

        print(switches, show_lta)
        if not all(s in HUBS for s in [x_domain_1, x_domain_2, y_domain_1, y_domain_2]):
            return blank_figure()

        domain_x = [x_domain_1, x_domain_2]
        domain_y = [y_domain_1, y_domain_2]

        mtu = pd.Timestamp(f"{date}T{str(hour)}:00:00.000Z")
        print(mtu)
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
        
        exchange = exchange[(
            exchange.index.get_level_values("from").isin(zones)
            &exchange.index.get_level_values("to").isin(zones)
        )]
        
        # for f,t in ltn.index:
        #     mcp.loc[f] += ltn.loc[(f,t), "ltn"]
        #     mcp.loc[t] -= ltn.loc[(f,t), "ltn"]
        #     exchange.loc[(f, t), "exchange"] += ltn.loc[(f,t), "ltn"]


        eli_exchange, ram_correction = calculate_FB_exchange(domain, lta, zones, mcp, exchange)
        # domain.loc[ram_correction.index, "ram"] = ram_correction.ram
        # print(domain.loc[ram_correction.index, "ram"])
        fbmc = FBDomainPlots(zones, domain)

        if show_lta and not show_lta_2:
            lta_domain = create_lta_domain(lta, zones, domain_x, domain_y)
        elif show_lta and show_lta_2:
            lta_domain = create_lta_domain_new(domain, lta, zones, domain_x, domain_y, mcp, exchange)

        timestep = domain.timestep.unique()[0]
        fb_domain = fbmc.generate_flowbased_domain(
            domain_x=domain_x, 
            domain_y=domain_y, 
            timestep=timestep, 
            exchange=eli_exchange if shift_mcp else None, 
            lta_domain=lta_domain if show_lta else None, 
        )

        fig = create_fb_domain_plot(
            fb_domain, 
            eli_exchange, 
            zones, 
            lta_domain if show_lta else None, 
            show_plot=False
        )
        return fig

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = layout()
add_callbacks(app)
server = app.server

if __name__ == "__main__":
    options = {
        "debug": False, 
        "threaded": True, 
        "use_reloader": True,
        "port": "8050", 
        "host": "127.0.0.1"
    }
    app.run_server(**options)
    
