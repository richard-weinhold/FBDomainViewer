# -*- coding: utf-8 -*-
"""
Created on Sat Oct  8 15:52:22 2022

@author: riw
"""

    # exchange["from"][0]
    # tmp_ex = exchange[exchange["from"].isin(zones)&exchange["to"].isin(zones)].set_index(["from", "to"]).copy()
    # tmp["ex"] = [tmp_ex.loc[tmp_ex["from"] == z, "exchange"].sum() - tmp_ex.loc[tmp_ex["to"] == z, "exchange"].sum() for z in zones]
    
    # tmp_lta = lta.set_index(["from", "to"]).copy()
    # t = [i for i in tmp_ex.index if i in tmp_lta.index]

    # tmp_ex["lta"] = tmp_lta.loc[t, "ram"]
    # vertices_ntc_domain = int(np.math.factorial(len(tmp_lta.index)) / np.math.factorial(len(zones))  / 
    #     np.math.factorial(len(tmp_lta.index) - len(zones))) 
    
    
    # domain.to_csv("data/tmp/domain_mcp.csv")
    # lta.to_csv("data/tmp/lta.csv")

    # analytics
    # ex_lta = pd.merge(
    #     exchange, lta, 
    #     how="outer", left_on=["from", "to"], 
    #     right_index=True).drop("timestep", axis=1)[["from", "to", "exchange", "lta"]].fillna(0)
    
    # ex_lta.to_csv("data/tmp/ex_lta.csv")
    # domain.to_csv("data/tmp/domain_mcp.csv")
    # cond = exchange["from"].isin(zones) & exchange["to"].isin(zones)
    # pd.merge(
    #     exchange[cond].groupby("from").sum(), 
    #     -exchange[cond].groupby("to").sum(), how="outer", right_index=True, left_index=True).sum(axis=1)
    
    
    
    
def lta_bounds(lta, zones, domain_x, domain_y):
    domain_x = ["BE", "FR"]
    domain_y = ["DE", "FR"]
    # Problem data.
    lta_constr = lta_constraints(lta, zones)
    A = lta_constr.loc[:, zones].values
    b = lta_constr.lta.values
    domain_x_indices = [zones.index(z) for z in domain_x]
    domain_y_indices = [zones.index(z) for z in domain_y]
    # Construct the problem.
    ex = cp.Variable(len(b))
    netpos = cp.Variable(len(zones))
    
    # constraints = [
    #     sum(netpos) == 0, 
    #     # netpos[:1] == 0, 
    #     ex <= b,
    #     ex >= 0,
    #     # sum(netpos[domain_x_indices]) == 0,
    #     # sum(netpos[domain_y_indices]) == 0,
    #     netpos == A.T @ ex
    #     ]
    print(f"LTA Limits for {'>'.join(domain_x)} and {'>'.join(domain_y)}")
    # N = 100
    # x,y = [],[]
    # for (i, j) in [(1, 1), (1,-1), (-1, -1), (-1, 1)]:
    # # for (i, j) in [(1, 1)]:
    #     for n in range(N):
    #         obj = \
    #             i*(N - 1 - n)*netpos[domain_x_indices]@(np.array([1, -1])) \
    #             + j*n*netpos[domain_y_indices]@(np.array([1, -1]))
    #         objective = cp.Maximize(obj)
    #         prob = cp.Problem(objective, constraints)
    #         prob.solve()
    #         x.append(netpos[domain_x_indices[0]].value)
    #         y.append(netpos[domain_y_indices[0]].value)
    #     print(netpos[domain_y_indices].value)
    #     print(netpos[domain_x_indices].value)
            
    # x,y = sort_vertices(x,y)
    
    # N = 100
    x,y = [],[]
    
    for i in [1, -1]:
        constraints = [
            # sum(netpos) == 0, 
            # netpos[:1] == 0, 
            ex <= b,
            ex >= 0,
            # sum(netpos[domain_x_indices]) == 0,
            # sum(netpos[domain_y_indices]) == 0,
            netpos == A.T@ex
            ]
        obj = i*netpos[domain_x_indices]@(np.array([1, -1])) 
        objective = cp.Maximize(obj)
        prob = cp.Problem(objective, constraints)
        prob.solve()
        x.append(netpos[domain_x_indices[0]].value)
        y.append(0)
            
    for i in [1, -1]:
        constraints = [
            # sum(netpos) == 0, 
            netpos[:1] == 0, 
            ex <= b,
            ex >= 0,
            # sum(netpos[domain_x_indices]) == 0,
            # sum(netpos[domain_y_indices]) == 0,
            netpos == A.T@ex
            ]
        
        obj = i*netpos[domain_y_indices]@(np.array([1, -1])) 
        objective = cp.Maximize(obj)
        prob = cp.Problem(objective, constraints)
        prob.solve()
        y.append(netpos[domain_y_indices[0]].value)
        x.append(0)
        print(netpos[domain_y_indices[0]].value)
    
    # ex[0] = 100
    # ex[1] = 100

    # A.T@ex
    
    # tmp = lta.copy()
    # tmp["t"] = A@netpos.value
    # ex.value
    x,y = sort_vertices(x,y)
    
    return x,y