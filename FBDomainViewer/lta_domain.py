from FBDomainViewer.fbmc_data import lta_constraints
import cvxpy as cp
import numpy as np 
import pandas as pd 
import time

def sort_vertices(vertices_x, vertices_y):
    vertices_sorted = []
    for idx in range(0, len(vertices_x)):
        radius = np.sqrt(np.power(vertices_y[idx], 2) + np.power(vertices_x[idx], 2))
        if vertices_x[idx] >= 0 and vertices_y[idx] >= 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] < 0 and vertices_y[idx] > 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               180 - np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] <= 0 and vertices_y[idx] <= 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               180 - np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] > 0 and vertices_y[idx] < 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               360 + np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
    from operator import itemgetter
    vertices_sorted = sorted(vertices_sorted, key=itemgetter(2))
    
    ## Add first element to draw complete circle
    vertices_sorted.append(vertices_sorted[0])
    vertices_sorted = np.array(vertices_sorted)   
    return vertices_sorted[:, 0], vertices_sorted[:, 1]


def create_lta_domain(lta, zones, domain_x, domain_y):
    # domain_x = ["BE", "FR"]
    # domain_y = ["DE", "FR"]
    lta_constr = lta_constraints(lta, zones)
    A = lta_constr.loc[:, zones].values
    b = lta_constr.lta.values
    domain_x_indices = [zones.index(z) for z in domain_x]
    domain_y_indices = [zones.index(z) for z in domain_y]

    other_bz_indices= [i for i in range(len(zones)) if i not in domain_x_indices + domain_y_indices]
    ex = cp.Variable(len(b))
    netpos = cp.Variable(len(zones))
    
    print(f"LTA Limits for {'>'.join(domain_x)} and {'>'.join(domain_y)}")
    x,y = [],[]
    constraints = [
        sum(netpos) == 0, 
        ex <= b,
        ex >= 0,
        netpos == A.T@ex
        ]
    N = 20
    x,y = [],[]
    for (i, j) in [(1, 1), (1,-1), (-1, -1), (-1, 1)]:
        for n in range(N):
            obj = \
                i*(N - 1 - n)*netpos[domain_x_indices]@(np.array([1, -1])) \
                + j*n*netpos[domain_y_indices]@(np.array([1, -1]))
            objective = cp.Maximize(obj)
            prob = cp.Problem(objective, constraints)
            prob.solve()
            x.append(netpos[domain_x_indices].value@(np.array([1, -1])))
            y.append(netpos[domain_y_indices].value@(np.array([1, -1])))
            
    x,y = sort_vertices(x,y)
    lta_domain = pd.DataFrame()
    lta_domain["x"], lta_domain["y"] = x,y
    return lta_domain

def create_ELI_constraints(domain, lta, zones):
    
    ram_threshold = 1
    domain.loc[domain.ram < ram_threshold, "ram"] = ram_threshold
    ptdf = domain.loc[:, zones].values
    ram = domain.loc[:, "ram"].values
    Z = len(zones)

    NetPos = cp.Variable(Z, name="NetPos")
    NetPosFB = cp.Variable(Z, name="NetPosFB")
    NetPosLTA = cp.Variable(Z, name="NetPosLTA")
    Flow = cp.Variable((Z,Z), name="Flow")
    FlowFB = cp.Variable((Z,Z), name="FlowFB")
    FlowLTA = cp.Variable((Z,Z), "FlowLTA")
    Alpha1, Alpha2 = cp.Variable(name="Alpha1"), cp.Variable(name="Alpha2")
    SlackFB = cp.Variable(len(ram), name="SlackFB")

    constraints = [
        FlowFB >= 0,
        FlowLTA >= 0,
        Alpha1 >= 0,
        Alpha2 >= 0,
        SlackFB >= 0, 
        SlackFB <= 1000, 
        Alpha1 + Alpha2 == 1,
        NetPos == NetPosFB + NetPosLTA,
        Flow == FlowFB + FlowLTA,
        ptdf@NetPosFB <= Alpha1 * ram + SlackFB,
        # sum(NetPos) == 0
    ]
    for z in range(Z):
        constraints.append(NetPosFB[z] == (sum(FlowFB[z, :]) - sum(FlowFB[:, z])))
        constraints.append(NetPosLTA[z] == (sum(FlowLTA[z, :]) - sum(FlowLTA[:, z])))

    for z in range(Z):
        for zz in range(Z):
            if (zones[z], zones[zz]) in lta.index:
                constraints.append(FlowLTA[z,zz] <= Alpha2 * lta.loc[(zones[z], zones[zz]), "lta"])   
            else:
                constraints.append(FlowLTA[z,zz] <= 0)   


    objective = cp.Maximize(1)
    prob = cp.Problem(objective, constraints)
    return prob

def calculate_FB_exchange(domain, lta, zones, mcp, exchange):
    
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

    return df, domain_copy

def create_lta_domain_new(domain, lta, zones, domain_x, domain_y, mcp=None, exchange=None):


    prob = create_ELI_constraints(domain, lta, zones)
    constr = prob.constraints 
    domain_x_indices = [zones.index(z) for z in domain_x]
    domain_y_indices = [zones.index(z) for z in domain_y]
    other_bz_indices= [i for i in range(len(zones)) if i not in domain_x_indices + domain_y_indices]

    if isinstance(mcp, pd.Series):
        for z in other_bz_indices:
            constr.append(prob.var_dict["NetPos"][z] == mcp[zones[z]])
            for zz in other_bz_indices:
                if (zones[z], zones[zz]) in exchange.index:
                    constr.append(prob.var_dict["Flow"][z,zz] == exchange.loc[(zones[z], zones[zz]), "exchange"])
                else:
                    constr.append(prob.var_dict["Flow"][z,zz] <= 0)

    N = 10
    x,y = [],[]
    start_time  = time.time()
    for (i, j) in [(1, 1), (1,-1), (-1, -1), (-1, 1)]:
    # for (i, j) in [( 1, 1)]:
        for n in range(N):
            obj = -sum(prob.var_dict["SlackFB"])*1e4 \
                + i*(N - 1 - n)*prob.var_dict["NetPos"][domain_x_indices]@(np.array([1, -1])) \
                + j*n*prob.var_dict["NetPos"][domain_y_indices]@(np.array([1, -1])) 
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
            # print(prob.status)
            # print(obj.value)
            # print("Alpha 1 / 2", Alpha1.value, Alpha2.value)
            x.append(prob.var_dict["NetPos"][domain_x_indices].value@(np.array([-1, 1])))
            y.append(prob.var_dict["NetPos"][domain_y_indices].value@(np.array([-1, 1])))

    end_time = time.time()
    print("total time taken this loop: ", end_time - start_time)
    x,y = sort_vertices(x,y)
    lta_domain = pd.DataFrame()
    lta_domain["x"], lta_domain["y"] = x,y
    return lta_domain