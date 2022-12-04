
import pandas as pd 
import numpy as np
import itertools
import io 
import json 
import requests
import pickle
from pathlib import Path

def load_data(mtu):
    
    cache_file = Path("data/cache").joinpath("data_" + mtu.strftime("%Y_%m_%d-%H%M") + ".pickle")
    if cache_file.is_file():
        data = pickle.load(open(cache_file, "rb" ))
    else:
        data = download_data(mtu)
        pickle.dump(data, open(cache_file, "wb"))
    
    return data 

def download_data(mtu):
    def get_url(data):
        return f"https://publicationtool.jao.eu/core/api/core/{data}/index"
    
    s = requests.Session()
    s.headers.update({
        'user-agent': 'riw',
        'Authorization': 'testing'
    })
    
    params = {
        "search": json.dumps({"presolved": True}),
        "date": mtu.isoformat(),
    }
    
    data = {}
    domain_response = s.get(get_url("finalComputation"), params=params)
    data["domain"], data["zones"] = process_final_computation(domain_response)
    
    mcp_response = s.get(get_url("netPos"), params=params)
    data["mcp"] = process_mcp(mcp_response, mtu)
    
    lta_response = s.get(get_url("lta"), params=params)
    data["lta"] = process_lta(lta_response, mtu)
    
    ltn_response = s.get(get_url("ltn"), params=params)
    data["ltn"] = process_ltn(ltn_response, mtu)
    
    exchange_response = s.get(get_url("scheduledExchanges"), params=params)
    data["exchange"] = process_exchange(exchange_response, mtu)
    
    return data
    
    # print(t)
    # c = mcp_response.json()
    # dff = 
    # dff.presolved   
    # # len(dff)
    # # dff
    

    #%%
    
def lta_constraints(lta, zones):
    lta_constraints = []
    for (f,t) in lta.index:
        tmp_ptdf = [0 for z in zones]
        tmp_ptdf[zones.index(f)] = 1
        tmp_ptdf[zones.index(t)] = -1
        tmp_data = [f, t, lta.loc[(f,t), "lta"]]
        lta_constraints.append(tmp_data + list(tmp_ptdf))
    return pd.DataFrame(lta_constraints, columns=["from", "to", "lta"] + zones)

    
def process_final_computation(domain_response):
    # file = r"C:\Users\riw\Documents\repositories\fbmc_viewer\data\FinalComputation 2022-09-18 0000 - 2022-09-18 0100.csv"
    # file = r"C:\Users\riw\Documents\repositories\fbmc_viewer\data\FinalComputation 2022-09-18 0400 - 2022-09-18 0500.csv"
    data = pd.DataFrame.from_dict(domain_response.json()["data"])

    zones_dict = {c: c.replace("ptdf_", "") for c in data.columns if "ptdf" in c}
    zones = list(zones_dict.values())
    data = data.rename(columns=zones_dict)
    # df = df[df.Presolved]
    rename_dict = {"dateTimeUtc": "timestep", "cneName": "cb", "contName": "co", "iva": "iva", "ram": "ram"}
    data = data.rename(columns=rename_dict)

    cols = list(rename_dict.values()) + zones
    data["cb"] += data.direction.replace(np.nan, "")

    data = data.loc[data[zones].notna().all(axis=1), cols]
    data.loc[data.co.isna(), "co"] = "basecase"

    data = data[~data.cb.str.contains("Constraint")]
    # df = df[df.ram > 1]
    # df.loc[df.index[:10], "iva"] = 10
    iva_copy = data[data.iva > 0].copy()
    iva_copy.loc[:, "ram"] += iva_copy.iva
    data = pd.concat([data, iva_copy])
    
    return data, zones

def process_mcp(mcp_response, mtu): 
    
    data = pd.DataFrame.from_dict(mcp_response.json()["netPos"])

    zones_dict = {c: c.replace("hub_", "") for c in data.columns if "hub" in c}
    data = data.rename(columns=zones_dict)
    data = data[pd.to_datetime(data.dateTimeUtc) == mtu]
    data = data.set_index(["dateTimeUtc", "id"], drop=True)

    return data.loc[data.index[0]]
    
def process_lta(lta_response, mtu): 
    lta_response
    data = pd.DataFrame.from_dict(lta_response.json()["lta"]).drop("id", axis=1)

    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    lta = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    lta[["from", "to"]] = lta.variable.str.split("_", n=1, expand=True)
    lta = lta[(pd.to_datetime(lta.dateTimeUtc) == mtu)].drop(["variable", "dateTimeUtc"], axis=1)
    lta = lta.rename(columns={"value": "lta"}).set_index(["from", "to"], drop=True)
    return lta
    
def process_ltn(ltn_response, mtu): 
    ltn_response
    data = pd.DataFrame.from_dict(ltn_response.json()["ltn"]).drop("id", axis=1)

    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    ltn = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    ltn[["from", "to"]] = ltn.variable.str.split("_", n=1, expand=True)
    ltn = ltn[(pd.to_datetime(ltn.dateTimeUtc) == mtu)].drop(["variable", "dateTimeUtc"], axis=1)
    ltn = ltn.rename(columns={"value": "ltn"}).set_index(["from", "to"], drop=True)
    return ltn
    
def process_exchange(exchange_response, mtu): 
    
    data = pd.DataFrame.from_dict(exchange_response.json()["scheduledExchanges"]).drop("id", axis=1)

    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    exchange = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    exchange[["from", "to"]] = exchange.variable.str.split("_", n=1, expand=True)
    
    exchange = exchange[pd.to_datetime(exchange.dateTimeUtc) == mtu].drop(["variable", "dateTimeUtc"], axis=1)
    exchange = exchange.rename(columns={"value": "exchange"}).set_index(["from", "to"], drop=True)
    return exchange

