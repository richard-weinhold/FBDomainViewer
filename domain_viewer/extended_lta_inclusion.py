import cvxpy as cp
import numpy as np 
import pandas as pd 
import time

def create_ELI_constraints(domain, lta, zones):
    
    ram_threshold = 1
    domain.loc[domain.ram < ram_threshold, "ram"] = ram_threshold
    ptdf = domain.loc[:, zones].values
    ram = domain.loc[:, "ram"].values
    Z = len(zones)
    AL_IDX = [zones.index(z) for z in zones if "AL" in z]

    NetPos = cp.Variable(Z, name="NetPos")
    NetPosFB = cp.Variable(Z, name="NetPosFB")
    NetPosLTA = cp.Variable(Z, name="NetPosLTA")
    Flow = cp.Variable((Z,Z), name="Flow")
    FlowFB = cp.Variable((Z,Z), name="FlowFB")
    FlowLTA = cp.Variable((Z,Z), "FlowLTA")
    Alpha = cp.Variable(name="Alpha")
    Slack = cp.Variable(len(ram), name="Slack")
    SlackNP = cp.Variable(Z, name="SlackNP")
    SlackFlowPos = cp.Variable((Z,Z), name="SlackFlowPos")
    SlackFlowNeg = cp.Variable((Z,Z), name="SlackFlowNeg")

    constraints = [
        FlowFB >= 0,
        FlowLTA >= 0,
        sum(NetPosLTA[AL_IDX]) == 0,
        sum(NetPos[AL_IDX]) == 0,
        Alpha >= 0,
        Alpha <= 1,
        Slack >= 0, #-1e-2, 
        Slack <= 100, 
        SlackNP >= -10, 
        SlackNP <= 10, 
        SlackFlowPos >= 0, 
        SlackFlowNeg >= 0, 
        SlackFlowPos <= 1e-2, 
        SlackFlowNeg <= 1e-2, 
        NetPos == NetPosFB + NetPosLTA + SlackNP,
        Flow == FlowFB + FlowLTA,
        ptdf@NetPosFB <= Alpha * ram + Slack,
        sum(NetPos) == 0,
        sum(NetPosFB) == 0,
        sum(NetPosLTA) == 0,
    ]
    for z in range(Z):
        constraints.append(NetPosFB[z] == sum([
            FlowFB[z, zz] - FlowFB[zz, z] # for zz in range(Z)]))
            + (SlackFlowPos[z, zz] - SlackFlowPos[zz, z]) 
            - (SlackFlowNeg[z, zz] - SlackFlowNeg[zz, z]) for zz in range(Z)]))
        constraints.append(NetPosLTA[z] == sum([FlowLTA[z, zz] - FlowLTA[zz, z] for zz in range(Z)]))

    for z in range(Z):
        for zz in range(Z):
            if not z==zz:
                if (zones[z], zones[zz]) in lta.index:
                    constraints.append(FlowLTA[z,zz] <= (1-Alpha) * lta.loc[(zones[z], zones[zz]), "lta"])  
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
            if not z==zz:
                if (zones[z], zones[zz]) in exchange.index:
                    constr.append(
                        prob.var_dict["Flow"][z,zz] >= exchange.loc[(zones[z], zones[zz]), "exchange"] + prob.var_dict["SlackFlowPos"][z,zz] - prob.var_dict["SlackFlowNeg"][z,zz] )          
                    constr.append(prob.var_dict["SlackFlowNeg"][z,zz] <= exchange.loc[(zones[z], zones[zz]), "exchange"])          
                
                else:
                    constr.append(prob.var_dict["Flow"][z,zz] <= 0)
        
    start_time  = time.time()
    obj = -sum(
        sum(prob.var_dict["Slack"]*1000) 
        + sum(prob.var_dict["SlackFlowPos"] 
              + prob.var_dict["SlackFlowNeg"])) + prob.var_dict["Alpha"]*1e3 
    objective = cp.Maximize(obj)
    prob = cp.Problem(objective, constr)
    prob.solve(
        solver=cp.SCIPY, 
        scipy_options={
            "method": "highs-ds",
            "presolve": True
        },
        verbose=False
    )
    cond = (prob.var_dict["Slack"].value > 1e-2)
    domain_copy = domain.loc[cond].copy()
    domain_copy.loc[:, "ram"] += prob.var_dict["Slack"].value[cond]
 
    df = exchange.copy()
    df["Flow"] = [prob.var_dict["Flow"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["FlowFB"] = [prob.var_dict["FlowFB"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["FlowLTA"] = [prob.var_dict["FlowLTA"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["SlackFlowNeg"] = [prob.var_dict["SlackFlowNeg"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["SlackFlowPos"] = [prob.var_dict["SlackFlowPos"].value[zones.index(i), zones.index(j)] for i,j in exchange.index]
    df["LTA"] = [lta.loc[(i,j), "lta"] for i,j in exchange.index if (i,j) in lta.index] + [0, 0]  
    
    df_np = pd.DataFrame(index=zones)
    df_np["MCP"] = [mcp[z]for z in zones]
    df_np["NetPosFB"] = [prob.var_dict["NetPosFB"].value[zones.index(z)] for z in zones]
    df_np["NetPosLTA"] = [prob.var_dict["NetPosLTA"].value[zones.index(z)] for z in zones]
    df_np["NetPos"] = [prob.var_dict["NetPos"].value[zones.index(z)] for z in zones]
    df_np["SlackNP"] = [prob.var_dict["SlackNP"].value[zones.index(z)] for z in zones]
    end_time = time.time()
    print("Sum Slack", sum(prob.var_dict["Slack"].value), sum(prob.var_dict["SlackNP"].value))
    print("Alpha", prob.var_dict["Alpha"].value)
    
    # tmp = {z: sum(df.loc[pd.IndexSlice[z,:],"FlowFB"]) - sum(df.loc[pd.IndexSlice[:,z],"FlowFB"]) for z in zones}
    # {z: df_np.loc[z, "NetPosFB"] - tmp[z]  for z in zones}
    return df, df_np, domain_copy, prob.var_dict["Alpha"].value