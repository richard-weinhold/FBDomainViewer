
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
    if mcp.loc["ALBE"] > 0:
        albe_exchange = pd.DataFrame(index=[("ALBE", "ALDE")], data=[mcp.loc["ALBE"]], columns=["exchange"])
    else:
        albe_exchange = pd.DataFrame(index=[("ALDE", "ALBE")], data=[mcp.loc["ALDE"]], columns=["exchange"])
    exchange = pd.concat([exchange, albe_exchange])
    cond = exchange.index.get_level_values("from").isin(zones)&exchange.index.get_level_values("to").isin(zones)
    exchange = exchange[cond]
    
    # %%
    print("Number of IVAs", len(domain[domain.iva > 0]))
    import cvxpy as cp
    lta_constr = lta_constraints(lta, zones)
    ptdf = domain.loc[:, zones].values
    ram = domain.ram.values
    Z = len(zones)
    net_pos, net_pos_fb, net_pos_lta = cp.Variable(Z), cp.Variable(Z), cp.Variable(Z)
    flow, flow_fb, flow_lta = cp.Variable((Z,Z)), cp.Variable((Z,Z)), cp.Variable((Z,Z))
    alpha1, alpha2 = cp.Variable(), cp.Variable(Z)
    # slack_flow_pos, slack_flow_neg = cp.Variable((Z,Z)), cp.Variable((Z,Z))
    # slack_np_pos, slack_np_neg = cp.Variable(Z), cp.Variable(Z)
    constraints = [
        flow_fb >= 0,
        flow_lta >= 0,
        alpha1 >= 0,
        alpha2 >= 0,
        alpha1 + alpha2 == 1,
        # sum(net_pos_fb) == 0,
        # sum(net_pos_lta) == 0,
        # slack_flow_pos == 0,
        # slack_np_pos == 0,
        # slack_flow_neg == 0,
        # slack_np_neg == 0,
        net_pos == net_pos_fb + net_pos_lta, # + slack_np_pos - slack_np_neg,
        flow == flow_fb + flow_lta, # + slack_flow_pos # - slack_flow_neg,
        ptdf@net_pos_fb <= alpha1 * ram
    ]
    for z in range(Z):
        constraints.append(net_pos_fb[z] == (sum(flow_fb[z, :]) - sum(flow_fb[:, z])))
        constraints.append(net_pos_lta[z] == (sum(flow_lta[z, :]) - sum(flow_lta[:, z])))

    for z in range(Z):
        for zz in range(Z):
            if (zones[z], zones[zz]) in lta.index:
                constraints.append(flow_lta[z,zz] <= alpha2 * lta.loc[(zones[z], zones[zz]), "lta"])
            # else:
            #     constraints.append(flow_lta[z,zz] <= 0)
                
            if (zones[z], zones[zz]) in exchange.index:
                constraints.append(flow[z,zz] == exchange.loc[(zones[z], zones[zz]), "exchange"])
            # else:
                # constraints.append(flow[z,zz] == 0)
    
    for z in range(Z):
        constraints.append(net_pos[z] == mcp[zones[z]])
        
    # obj = sum(sum(slack_np_pos + slack_np_neg)) + sum(slack_np_pos + slack_np_neg)
    obj = sum(sum(flow))
    # obj = -(flow[6,5] - flow[5,6])
    objective = cp.Minimize(obj)
    prob = cp.Problem(objective, constraints)
    prob.solve()    
    print(prob.status)
    net_pos.value
    print(obj.value)
    domain_x_indices = [zones.index(z) for z in domain_x]
    domain_y_indices = [zones.index(z) for z in domain_y]
    
    f = flow.value
    flow.value[6,5] - flow.value[5,6]
    flow_fb.value[6,5] - flow_fb.value[5,6]
    flow_lta.value[6,5] - flow_lta.value[5,6]
    
    flow.value[5,9] - flow.value[9,5]
    flow_fb.value[5,9] - flow_fb.value[9,5]
    flow_lta.value[5,9] - flow_lta.value[9,5]

    
    zones[6]
    n = net_pos.value
    net_pos_fb.value
    net_pos_lta.value
    mcp.index
    t = pd.DataFrame(index=mcp.index)    
    t["mcp"] = mcp.values
    t["np fb"] = [net_pos_fb.value[zones.index(z)] for z in zones]
    t["np lta"] = [net_pos_lta.value[zones.index(z)] for z in zones]
    ex = exchange.reset_index()
    ex = ex[ex["from"].isin(zones)&ex["to"].isin(zones)]
    t["ex"] = [ex.loc[ex["from"] == z, "exchange"].sum() - ex.loc[ex["to"] == z, "exchange"].sum() for z in t.index]

    nex_x = exchange.loc[tuple(domain_x), "exchange"] - exchange.loc[tuple(domain_x[::-1]), "exchange"]
    nex_y = exchange.loc[tuple(domain_y), "exchange"] - exchange.loc[tuple(domain_y[::-1]), "exchange"]


