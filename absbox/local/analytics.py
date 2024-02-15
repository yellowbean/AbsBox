import pandas as pd 
from pyxirr import xirr, xnpv
from absbox.local.base import china_bondflow_fields_s, english_bondflow_fields_s
from absbox.validation import vStr
import numpy as np
from toolz import get_in

def runYieldTable(api, d, bondName, p_assumps: dict, b_assumps: dict):
    assert isinstance(p_assumps, dict), f"pool assumption should be a map but got {type(p_assumps)}"
    
    rs = api.run(d, poolAssump=p_assumps
                  , runAssump=[('pricing', b_assumps)]
                  , read=True)

    b_pricing = {k: v['pricing'].loc[ vStr(bondName)] for k, v in rs.items()}
    b_table = pd.concat(b_pricing.values(), axis=1)
    b_table.columns = list(b_pricing.keys())

    return b_table

run_yield_table = runYieldTable

def irr(flow: pd.DataFrame, init):
    def extract_cash_col(_cols):
        if _cols == china_bondflow_fields_s:
            return flow['本息合计']
        elif _cols == english_bondflow_fields_s: 
            return flow['cash']
        else:
            raise RuntimeError("Failed to match", _cols)

    cols = flow.columns.to_list()
    dates = flow.index.to_list()
    amounts = extract_cash_col(cols).to_list()
        
    assert init is not None, f"inti:{init} shouldn't be None"
    assert len(init) == 2, f"init: should be a tuple with length of 2, but got {init}"
    invest_date, invest_amount = init
    dates = [invest_date]+dates
    amounts = [invest_amount]+amounts
    
    return xirr(np.array(dates), np.array(amounts))


def sum_fields_to_field(_df: pd.DataFrame, cols: list, col: str):
    """ Sum up a list of columns and attach to dataframe, reutrn with a copy """
    assert isinstance(cols, list), "columns to be sum up must be a list"
    assert isinstance(col, str), "result column must be a string"
    df = _df.copy()
    df[col] = df[cols].sum(axis=1)
    return df


def npv(_flow: pd.DataFrame, **p):
    flow = _flow.copy()
    cols = flow.columns.to_list()
    idx_name = flow.index.name
    init_date, _init_amt = p['init']
    init_amt = _init_amt if _init_amt != 0.00 else 0.0001

    def _pv(_af):
        af = flow[_af]
        return xnpv(p['rate']
                    , [init_date] + flow.index.to_list()
                    , [-1 * init_amt] + af.to_list())
    match (cols, idx_name):
        case (china_rental_flow, "日期"):
            return _pv("租金")
        case (english_rental_flow, "Date"):
            return _pv("Rental")
        case (english_mortgage_flow_fields, "Date"):
            sum_fields_to_field(flow, ["Principal", "Interest", "Prepayment", "Recovery"], "Cash")
            return _pv("Cash")
        case (china_bondflow_fields, "日期"):
            return _pv("本息合计")
        case (english_bondflow_fields, "Date"):
            return _pv("cash")
        case _:
            raise RuntimeError("Failed to match", cols, idx_name)


def flow_by_scenario(rs, flowpath, node="col", rtn_df=True, ax=1, rnd=2):
    "pull flows from multiple scenario"
    r = None
    if node == "col":
        r = {k: get_in(flowpath[:-1], v)[flowpath[-1]] for k, v in rs.items()}    
    elif node == "idx":
        r = {k: get_in(flowpath[:-1], v).loc[flowpath[-1]] for k, v in rs.items()}    
    else:
        r = {k: get_in(flowpath, v) for k, v in rs.items()}
    if rtn_df:
        _vs = list(r.values())
        _ks = list(r.keys())
        r = pd.concat(_vs, keys=_ks, axis=ax)
    return r