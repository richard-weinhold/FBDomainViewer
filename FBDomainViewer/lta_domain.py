
from FBDomainViewer.fbmc_data import lta_constraints
import cvxpy as cp
import numpy as np 
import pandas as pd 

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


def create_lta_domain(lta, zones, domain_x, domain_y, mcp=None):
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
        if isinstance(mcp, pd.Series):
            print("Here")
            # mcp = mcp.values
            # print(mcp[other_bz_indices])
            constraints.append(sum(netpos) == 0)

        obj = i*netpos[domain_x_indices]@(np.array([1, -1])) 
        objective = cp.Maximize(obj)
        prob = cp.Problem(objective, constraints)
        prob.solve()
        print("Obj", prob.status)
        x.append(netpos[domain_x_indices[0]].value)
        y.append(0)
        print(netpos.value)
            
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

    x,y = sort_vertices(x,y)
    
    lta_domain = pd.DataFrame()
    lta_domain["x"], lta_domain["y"] = x,y

    return lta_domain