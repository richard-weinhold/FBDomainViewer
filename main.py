import datetime as dt
import pandas as pd
import requests
from pathlib import Path
from plotly.offline import plot

import json

from domain_viewer.data_processing import load_data, ZONES, add_alegro_exchange
from domain_viewer.fbmc_domain import FBDomainPlots
from domain_viewer.extended_lta_inclusion import calculate_FB_exchange
from domain_viewer.fbmc_domain_plot import create_fb_domain_plot

if __name__ == "__main__":

    # Setup 
    date = "2025-07-07" # Businessday
    hour = "19" # Hour in CET
    domain_x = ["DE", "FR"] # Domain x-Axis
    domain_y = ["DE", "AT"] # Domain y-Axis
    shift_mcp = True # Shift Domain to Market Clearing Point 

    request_session = requests.Session()
    request_session.headers.update({
        'user-agent': 'riw@50Hertz',
        'Authorization': 'DomainViewer'
    })
    
    # Read Proxy File if it exists. 
    if Path.cwd().joinpath("proxy.json").is_file():
        with open(Path.cwd().joinpath("proxy.json"), 'r') as f:
            proxy = json.load(f)
        request_session.proxies.update(proxy)

    mtu = pd.Timestamp(
        dt.datetime.strptime(f"{date}T{str(hour).zfill(2)}", "%Y-%m-%dT%H")
        ).tz_localize("Europe/Berlin")
    print(mtu)

    # Read Data from JAO
    data = load_data(mtu, request_session)
    domain = data["domain"].copy()
    mcp = data["mcp"].loc[mtu.isoformat()]
    lta = data["lta"]

    exchange = add_alegro_exchange(data["exchange"], mcp, mtu)
    cond = (
        exchange.index.get_level_values("from").isin(ZONES)
        &exchange.index.get_level_values("to").isin(ZONES)
    )
    exchange = exchange[cond]

    # Calculate Extended LTA Inclusion (ELI) Flow Components
    eli_exchange, eli_np, ram_correction, alpha = calculate_FB_exchange(domain, lta, ZONES, mcp, exchange)
    
    # ELI calculation can cause issues, these are reflected in ram_corrections 
    # (that are expected to be very small)
    domain.loc[ram_correction.index, "ram"] += ram_correction.ram
    domain.loc[:, "ram"] *= alpha
    if not ram_correction.empty:
        print("RAM Correction", domain.loc[ram_correction.index, ["cb", "co", "ram"]])

    # Calculate flow-based Domain, i.e. creating the relevant plot-points and lines
    fbmc = FBDomainPlots(ZONES, domain)
    fb_domain = fbmc.generate_flowbased_domain(
        domain_x=domain_x,
        domain_y=domain_y,
        mtu=mtu,
        exchange=eli_exchange if shift_mcp else None,
        lta_domain=None,
    )

    # Create plot. 
    fig = create_fb_domain_plot(
        fb_domain,
        eli_exchange,
        ZONES,
        None,
        alpha,
        show_plot=True
    )

    # Write domain plot as html and open
    fig.write_html("fb_domain.html", full_html=False, include_plotlyjs='cdn')
    plot(fig)
