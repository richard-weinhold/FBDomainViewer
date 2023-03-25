
import os 
import numpy as np 
import pandas as pd
import cvxpy as cp
import time

from FBDomainViewer import load_data, lta_constraints
from FBDomainViewer.fbmc_domain import FBDomainPlots
from FBDomainViewer.plot import create_fb_domain_plot
from FBDomainViewer.lta_domain import sort_vertices
from FBDomainViewer.lta_domain import create_ELI_constraints

# %%
if __name__ == "__main__":
    # mtu = pd.Timestamp("2022-12-06T22:00:00.000Z")
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

    if mcp.loc["ALBE"] > 0:
        albe_exchange = pd.DataFrame(index=[("ALBE", "ALDE")], data=[mcp.loc["ALBE"]], columns=["exchange"])
    else:
        albe_exchange = pd.DataFrame(index=[("ALDE", "ALBE")], data=[mcp.loc["ALDE"]], columns=["exchange"])

    # for f,t in ltn.index:
    #     mcp.loc[f] += ltn.loc[(f,t), "ltn"]
    #     mcp.loc[t] -= ltn.loc[(f,t), "ltn"]

    exchange = pd.concat([exchange, albe_exchange])
    cond = exchange.index.get_level_values("from").isin(zones)&exchange.index.get_level_values("to").isin(zones)
    exchange = exchange[cond]
    
    # %%
    print("Number of IVAs", len(domain[domain.iva > 0]))

    # ram_threshold = 1
    # domain.loc[domain.ram < ram_threshold, "ram"] = ram_threshold
    # domain.loc[46, "ram"] = 5

    lta.to_csv("lta.csv")
    domain.loc[:, zones].to_csv("ptdf.csv", index=False)
    domain.ram.to_csv("ram.csv", index=False)
    mcp.to_csv("mcp.csv")
    exchange.to_csv("exchange.csv")

    
    prob = create_ELI_constraints(domain, lta, zones)
    constr = prob.constraints 
    for z in range(len(zones)):
        constr.append(prob.var_dict["NetPos"][z] == mcp[zones[z]])
        for zz in range(len(zones)):
            if (zones[z], zones[zz]) in exchange.index:
                constr.append(prob.var_dict["Flow"][z,zz] == exchange.loc[(zones[z], zones[zz]), "exchange"])            
            else:
                constr.append(prob.var_dict["Flow"][z,zz] <= 0)

    start_time  = time.time()
    obj = -sum(prob.var_dict["SlackFB"])*1e4 + prob.var_dict["Alpha1"]*1000 
    objective = cp.Maximize(obj)
    prob = cp.Problem(objective, constr)
    prob.solve(
        solver=cp.SCIPY, 
        scipy_options={
            "method": "highs-ds",
            "presolve": False
        },
        warm_start=True,
    
    )
    print(prob.status)
    print(obj.value)
    print("Sum Slack", sum(prob.var_dict["SlackFB"].value))

    cond = prob.var_dict["SlackFB"].value > 1e-2
    print("On", domain.loc[cond, ["cb", "co"]])
    domain_copy = domain.loc[cond].copy()
    domain_copy.loc[:, "ram"] += prob.var_dict["SlackFB"].value[cond]
 
    print("Alpha 1 / 2", prob.var_dict["Alpha1"].value, prob.var_dict["Alpha2"].value)
    df = exchange.copy()
    df["Flow"] = [prob.var_dict["Flow"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["FlowFB"] = [prob.var_dict["FlowFB"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["FlowLTA"] = [prob.var_dict["FlowLTA"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    # print(df)
    end_time = time.time()
    print("total time taken: ", end_time - start_time)
