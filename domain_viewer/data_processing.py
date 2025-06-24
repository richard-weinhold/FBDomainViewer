
import pandas as pd
import numpy as np
import datetime as dt
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ZONES = [
    'AT', 'BE', 'CZ', 'DE', 'FR', 'HR', 'HU', 
    'NL', 'PL', 'RO', 'SI', 'SK', 'ALBE', 'ALDE'
]

def load_data(mtu, request_session, force_reload=False):
    try:
        df = pd.read_feather("data/domain.db", columns=["mtu"])
        df = df[df["mtu"] == mtu.isoformat()]
    except FileNotFoundError:
        df = pd.DataFrame()
    if df.empty or force_reload:
        print("Download and to DB")
        data = download_and_save_data(mtu, request_session)
    else:
        print("Load from DB")
        data = load_data_from_db(mtu)
    return data

def load_data_from_db(mtu):
    index = {
        "domain": "index",
        "mcp": "mtu",
        "lta": ["from", "to"],
        "ltn": ["from", "to"],
        "exchange": ["from", "to"],
    }
    data = {}
    for k, i in index.items():
        tmp_df = pd.read_feather(f"data/{k}.db")
        tmp_df = tmp_df[tmp_df["mtu"] == mtu.isoformat()]
        data[k] = tmp_df.set_index(i)
    return data

def download_and_save_data(mtu, request_session):
    def get_url(data):
        return f"https://publicationtool.jao.eu/core/api/data/{data}"

    params = {
        "Filter": json.dumps({"Presolved": True}),
        "fromUtc": mtu.tz_convert("UTC").isoformat(),
        "toUtc": (mtu + dt.timedelta(hours=1)).isoformat(),
    }
    data = {}
    domain_response = request_session.get(
        get_url("finalComputation"),
        params=params,
        verify=False,
        proxies=request_session.proxies
    )

    data["domain"] = process_final_computation(domain_response, mtu)
    mcp_response = request_session.get(
        get_url("netPos"),
        params=params,
        verify=False,
        proxies=request_session.proxies
    )
    data["mcp"] = process_mcp(mcp_response, mtu)
    lta_response = request_session.get(
        get_url("lta"),
        params=params,
        verify=False,
        proxies=request_session.proxies
    )
    data["lta"] = process_lta(lta_response, mtu)
    ltn_response = request_session.get(
        get_url("ltn"),
        params=params,
        verify=False,
        proxies=request_session.proxies
    )
    data["ltn"] = process_ltn(ltn_response, mtu)
    
    exchange_response = request_session.get(
        get_url("scheduledExchanges"),
        params=params,
        verify=False,
        proxies=request_session.proxies
    )
    data["exchange"] = process_exchange(exchange_response, mtu)

    for k in data.keys():
        try:
            tmp_df = pd.read_feather(f"data/{k}.db")
        except FileNotFoundError:
            tmp_df = pd.DataFrame()
        df = pd.concat([tmp_df, data[k].reset_index()])
        df.to_feather(f"data/{k}.db")
    return data

def lta_constraints(lta, zones):
    constraints = []
    for (f,t) in lta.index:
        tmp_ptdf = [0 for z in zones]
        tmp_ptdf[zones.index(f)] = 1
        tmp_ptdf[zones.index(t)] = -1
        tmp_data = [f, t, lta.loc[(f,t), "lta"]]
        constraints.append(tmp_data + list(tmp_ptdf))
    return pd.DataFrame(constraints, columns=["from", "to", "lta"] + zones)

def process_final_computation(domain_response, mtu):
    """Process presolved FB Domain from JAO Publication Tool"""
    data = pd.DataFrame.from_dict(domain_response.json()["data"])
    zones_dict = {c: c.replace("ptdf_", "") for c in data.columns if "ptdf" in c}
    zones = list(zones_dict.values())
    data = data.rename(columns=zones_dict)
    rename_dict = {
        "dateTimeUtc": "mtu",
        "cneName": "cb",
        "contName": "co",
        "tso": "tso",
        "presolved": "presolved",
        "iva": "iva",
        "ram": "ram"
    }
    data = data.rename(columns=rename_dict)
    cols = list(rename_dict.values()) + zones
    data["cb"] += data.direction.replace(np.nan, "")
    data = data.loc[data[zones].notna().all(axis=1), cols]
    data.loc[data.co.isna(), "co"] = "basecase"
    data = data[~data.cb.str.contains("Constraint")]
    data["mtu"] = mtu.isoformat()
    iva_copy = data[data.iva > 0].copy()
    iva_copy.loc[:, "ram"] += iva_copy.iva
    data = pd.concat([data, iva_copy])
    return data 

def process_mcp(mcp_response, mtu):
    """Process MCP from JAO Publication Tool"""
    data = pd.DataFrame.from_dict(mcp_response.json()["data"])
    zones_dict = {c: c.replace("hub_", "") for c in data.columns if "hub" in c}
    data = data.rename(columns=zones_dict)
    data = data.loc[pd.to_datetime(data.dateTimeUtc) == mtu, ["dateTimeUtc"] +  list(zones_dict.values())]
    data = data.rename(columns={"dateTimeUtc": "mtu"})
    data["mtu"] = mtu.isoformat()
    data = data.set_index(["mtu"], drop=True)
    return data

def process_lta(lta_response, mtu):
    """Process LTA from JAO Publication Tool"""
    data = pd.DataFrame.from_dict(lta_response.json()["data"]).drop("id", axis=1)
    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    data = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    data[["from", "to"]] = data.variable.str.split("_", n=1, expand=True)
    data = data[(pd.to_datetime(data.dateTimeUtc) == mtu)].drop(["variable"], axis=1)
    data = data.rename(columns={"value": "lta", "dateTimeUtc": "mtu"}).set_index(["from", "to"], drop=True)
    data["mtu"] = mtu.isoformat()
    return data

def process_ltn(ltn_response, mtu):
    """Process LTN from JAO Publication Tool"""
    data = pd.DataFrame.from_dict(ltn_response.json()["data"]).drop("id", axis=1)
    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    data = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    data[["from", "to"]] = data.variable.str.split("_", n=1, expand=True)
    data = data[(pd.to_datetime(data.dateTimeUtc) == mtu)].drop(["variable"], axis=1)
    data = data.rename(columns={"value": "ltn", "dateTimeUtc": "mtu"}).set_index(["from", "to"], drop=True)
    data["mtu"] = mtu.isoformat()
    return data

def process_exchange(exchange_response, mtu):
    """Process Exchange from JAO Publication Tool"""
    data = pd.DataFrame.from_dict(exchange_response.json()["data"]).drop("id", axis=1)
    zones_dict = {c: c.replace("border_", "") for c in data.columns if "border" in c}
    data = data.rename(columns=zones_dict).melt(id_vars="dateTimeUtc")
    data[["from", "to"]] = data.variable.str.split("_", n=1, expand=True)
    data = data[data["from"].isin(ZONES)&(data["to"].isin(ZONES))]
    data = data[pd.to_datetime(data.dateTimeUtc) == mtu].drop(["variable"], axis=1)
    data = data.rename(columns={"value": "exchange", "dateTimeUtc": "mtu"}).set_index(["from", "to"], drop=True)
    data["mtu"] = mtu.isoformat()
    return data

def add_alegro_exchange(exchange, mcp, mtu):
    """Modify Exchange to explicitly include Alegro Exchange"""
    if mcp.loc["ALBE"] > 0:
        index = pd.MultiIndex.from_tuples([("ALBE", "ALDE"), ("ALDE", "ALBE")], names=("from", "to"))
        albe_exchange = pd.DataFrame(
            index=index, 
            data=[
                [mtu.isoformat(), mcp.loc["ALBE"]],
                [mtu.isoformat(), 0],
                ], 
            columns=["mtu", "exchange"]
        )
    else:
        index = pd.MultiIndex.from_tuples([("ALDE", "ALBE"), ("ALBE", "ALDE")], names=("from", "to"))
        albe_exchange = pd.DataFrame(
            index=index, 
            data=[
                [mtu.isoformat(), mcp.loc["ALDE"]],
                [mtu.isoformat(), 0],
                ], 
            columns=["mtu", "exchange"]
        )
    exchange = pd.concat([exchange, albe_exchange])
    return exchange


