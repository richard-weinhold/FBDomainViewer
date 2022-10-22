
import os 
import numpy as np 
import pandas as pd

os.chdir("C:/Users/riw/Documents/repositories/FBDomainViewer")

from FBDomainViewer import load_data, lta_constraints
from FBDomainViewer.fbmc_domain import FBDomainPlots
from FBDomainViewer.plot import create_fb_domain_plot

# %%
if __name__ == "__main__":
    mtu = pd.Timestamp("2022-09-17T22:00:00.000Z")
    mtu = pd.Timestamp("2022-09-18T02:00:00.000Z")
    mtu = pd.Timestamp("2022-09-19T05:00:00.000Z")
    mtu = pd.Timestamp("2022-08-16T03:00:00.000Z")
    
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
    
    domain = domain[[c for c in domain.columns if c not in zones] + zones]
    tmp = pd.DataFrame(index=zones)
    tmp["mcp"] = mcp.loc[zones]
    
    
    if mcp.loc["ALBE"] > 0:
        albe_exchange = pd.DataFrame(index=[("ALBE", "ALDE")], data=[mcp.loc["ALBE"]], columns=["exchange"])
        
    else:
        albe_exchange = pd.DataFrame(index=[("ALDE", "ALBE")], data=[mcp.loc["ALDE"]], columns=["exchange"])
    exchange = pd.concat([exchange, albe_exchange])
    
    fbmc = FBDomainPlots(zones, domain)

    timestep = domain.timestep.unique()[0]
    # domain_x=["NL", "DE"]
    domain_x=["AT", "DE"]
    domain_y=["DE", "FR"]
    
    # ltn.loc[lta.index, "ltn"]
    # for i in ltn.index:
    #     if ltn.loc[i, "ltn"] > 0:
    #         print(f"Reduce LTA {'>'.join(i)} by LTN {ltn.loc[i, 'ltn']}")
    #         lta.loc[i, "lta"] -= ltn.loc[i, 'ltn']
            
            
    # lta_bounds_bex(lta, zones, domain_x)
    # lta_bounds_bex(lta, zones, domain_y)
    
    timestep=timestep
    
    fb_domain = fbmc.generate_flowbased_domain(
        domain_x=domain_x, 
        domain_y=domain_y, 
        timestep=timestep, 
        exchange=exchange, 
        # lta=lta
    )
    
    from plotly.offline import plot
    
    # fb_domain.zones
    fig = create_fb_domain_plot(fb_domain, exchange, zones, lta, show_plot=False)
    plot(fig)
    




