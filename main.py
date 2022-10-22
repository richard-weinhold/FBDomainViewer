
import os 
import numpy as np 
import pandas as pd

from FBDomainViewer import load_data, lta_constraints
from FBDomainViewer.fbmc_domain import FBDomainPlots
from FBDomainViewer.plot import create_fb_domain_plot

# %%
if __name__ == "__main__":
    mtu = pd.Timestamp("2022-09-17T22:00:00.000Z")
    # mtu = pd.Timestamp("2022-09-18T02:00:00.000Z")
    # mtu = pd.Timestamp("2022-09-19T05:00:00.000Z")
    # mtu = pd.Timestamp("2022-08-16T03:00:00.000Z")
    
    domain_x=["DE", "FR"]
    domain_y=["DE", "NL"]

    data = load_data(mtu)
    domain = data["domain"].copy()
    zones = data["zones"]
    mcp=data["mcp"]
    lta = data["lta"]
    ltn = data["ltn"]
    exchange = data["exchange"]

    print("Number of IVAs", len(domain[domain.iva > 0]))
    
    domain = domain.loc[domain.ram > 1, :]
    domain["f@mcp"] = np.dot(domain.loc[:, zones].values, mcp.loc[zones].values)
    domain["ram@mcp"] = domain["ram"] - domain["f@mcp"]
    
    domain_warn = domain.loc[domain["ram@mcp"] < 0, domain.columns[:7]]
        
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
        exchange=exchange, 
    )
    fig = create_fb_domain_plot(
        fb_domain, 
        exchange, 
        zones, 
        lta, 
        show_plot=True
    )





