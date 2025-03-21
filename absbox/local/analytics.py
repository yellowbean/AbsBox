import pandas as pd 
from .base import china_bondflow_fields_s, english_bondflow_fields_s,english_bondflow_cash,china_bondflow_cash
from ..validation import vStr
from toolz import get_in

def runYieldTable(api, d, bondName:str, p_assumps: dict, b_assumps: dict):
    """ a shortcut function to run a 'yield table' for a bond, with different pool assumptions

    :param api: the api object
    :type api: _type_
    :param d: the deal object
    :type d: _type_
    :param bondName: the bond name
    :type bondName: str
    :param p_assumps: a map of pool assumptions
    :type p_assumps: dict
    :param b_assumps: pricing assumption for bond
    :type b_assumps: tuple
    :return: _description_
    :rtype: _type_
    """
    assert isinstance(p_assumps, dict), f"pool assumption should be a map but got {type(p_assumps)}"
    
    rs = api.runByScenarios(d, poolAssump=p_assumps
                            , runAssump=[('pricing', b_assumps)]
                            , read=True)

    b_pricing = {k: v['pricing'].loc[ vStr(bondName)] for k, v in rs.items()}
    b_table = pd.concat(b_pricing.values(), axis=1)
    b_table.columns = list(b_pricing.keys())

    return b_table

run_yield_table = runYieldTable


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