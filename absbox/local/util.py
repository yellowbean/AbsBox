import pandas as pd
import functools,json,copy
import logging
import itertools,re
from enum import Enum
import numpy as np
import dataclasses
from functools import reduce
from pyxirr import xirr,xnpv

from absbox.local.base import *

def flat(xss) -> list:
    return reduce(lambda xs, ys: xs + ys, xss)

def mkTag(x) -> dict:
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}

def readTagStr(x:str):
    _x = json.loads(x.replace("'","\""))
    match _x:
        case {"tag":_t,"contents":_c} if isinstance(_c, list):
            _cs = [str(_) for _ in _c]
            return f"<{_t}:{','.join(_cs)}>"
        case {"tag": _t }:
            return f"<{_t}>"
        case _ :
            return f"<{_x}>"


def readTag(x:dict):
    return f"<{x['tag']}:{','.join(x['contents'])}>"

def isDate(x):
    return re.match(r"\d{4}\-\d{2}\-\d{2}",x)

def allList(xs):
    return all([ isinstance(x,list)  for x in xs])

def mkTs(n, vs):
    return mkTag((n, vs))

def unify(xs, ns):
    "union dataframes by stacking up with names provided"
    index_name = xs[0].index.name
    dfs = []
    for x, n in zip(xs, ns):
        dfs.append(pd.concat([x], keys=[n], axis=1))
    r = functools.reduce(lambda acc, x: acc.merge(x
                                                , how='outer'
                                                , on=[index_name])
                        , dfs)
    return r.sort_index()

def unifyTs(xs):
    "unify time-series alike dataframe"
    _index_set = set([x.index.name for x in xs])
    assert len(_index_set)==1,f"Index of dataframes should have same name,got:{_index_set}"

    _index_name = list(_index_set)[0]
    r = functools.reduce(lambda acc, x: acc.merge(x
                                                , how='outer'
                                                , on=[_index_name]), xs)
    
    return r.sort_index()

def consolStmtByDate(s):
    return s.groupby("日期").last()

def aggStmtByDate(s):
    return s.groupby("日期").sum()

def aggCFby(_df, interval, cols):
    df = _df.copy()
    idx = None
    dummy_col = '_index'
    df[dummy_col] = df.index
    _mapping = {"月份":"M"
               ,"Month":"M"
               ,"M":"M"
               ,"month":"M"}
    if df.index.name == "日期":
        idx = "日期"
    else:
        idx = "date"
    df[dummy_col]=pd.to_datetime(df[dummy_col]).dt.to_period(_mapping[interval])
    return df.groupby([dummy_col])[cols].sum().rename_axis(idx)#.drop(columns=[dummy_col])


def irr(flow,init=None):
    def extract_cash_col(_cols):
        if _cols == china_bondflow_fields_s:
            return flow['本息合计']
        elif _cols == english_bondflow_fields_s: 
            return flow['cash']
        else:
            raise RuntimeError("Failed to match",_cols)

    cols = flow.columns.to_list()
    dates = flow.index.to_list()
    amounts = extract_cash_col(cols).to_list()
        
    if init is not None:
        invest_date,invest_amount = init
        dates = [invest_date]+dates
        amounts = [invest_amount]+amounts
    
    return xirr(np.array(dates), np.array(amounts))


def sum_fields_to_field(_df,cols,col):
    df = _df.copy()
    df[col] = df[cols].sum(axis=1)
    return df


def npv(_flow,**p):
    flow = _flow.copy()
    cols = flow.columns.to_list()
    idx_name = flow.index.name
    init_date,_init_amt = p['init']
    init_amt = _init_amt if _init_amt!=0.00 else 0.0001
    def _pv(_af):
        af = flow[_af]
        return xnpv(p['rate'],[init_date]+flow.index.to_list(),[-1*init_amt]+af.to_list())
    match (cols,idx_name):
        case (china_rental_flow,"日期"):
            return _pv("租金")
        case (english_rental_flow,"Date"):
            return _pv("Rental")
        case (english_mortgage_flow_fields,"Date"):
            sum_fields_to_field(flow,["Principal","Interest","Prepayment","Recovery"], "Cash")
            return _pv("Cash")
        case (china_bondflow_fields,"日期"):
            return _pv("本息合计")
        case (english_bondflow_fields,"Date"):
            return _pv("cash")
        case _:
            raise RuntimeError("Failed to match",cols,idx_name)


def update_deal(d,i,c):
    "A patch function to update a deal data component list in immuntable way"
    _d = d.copy()
    _d.pop(i)
    _d.insert(i,c)
    return _d

def mkDealsBy(d, m:dict)->dict:
    return { k:dataclasses.replace(d, **v) 
                for k,v in m.items()} 

class DC(Enum):  # TODO need to check with HS code
    DC_30E_360 = "DC_30E_360"
    DC_30Ep_360 ="DC_30Ep_360"
    DC_ACT_360  = "DC_ACT_360"
    DC_ACT_365A = "DC_ACT_365A"
    DC_ACT_365L = "DC_ACT_365L"
    DC_NL_365 = "DC_NL_365"
    DC_ACT_365F = "DC_ACT_365F"
    DC_ACT_ACT = "DC_ACT_ACT"
    DC_30_360_ISDA = "DC_30_360_ISDA"
    DC_30_360_German = "DC_30_360_German"
    DC_30_360_US  = "DC_30_360_US"

def str2date(x:str):
    return datetime.strptime(x, '%Y-%m-%d').date()

def normDate(x:str):
    if len(x)==8:
        return f"{x[:4]}-{x[4:6]}-{x[6:8]}"

def daysBetween(sd,ed):
    return (ed - sd).days

def guess_locale(x):
    accs = x['accounts']

    assert len(accs)>0,"Failed to identify via deal accounts result"

    acc_cols = set(list(accs.values())[0].columns.to_list())
    locale = None
    if acc_cols == set(["余额", "变动额", "备注"]):
        locale="cn"
    if acc_cols == set(["balance", "change", "memo"]):
        locale="en"
    return locale

def guess_pool_locale(x):
    if "cutoffDate" in x:
        return "english"
    elif '封包日' in x:
        return "chinese"
    else:
        raise RuntimeError("Failed to match {x} in guess pool locale")

def renameKs(m:dict,mapping,opt_key=False):
    '''
    rename keys in a map with from a mapping tuple passed in 
    `opt_key` = True, allow skipping mapping tuple not exist in the map
    '''
    for (o,n) in mapping:
        if opt_key and o not in m:
            continue
        m[n] = m[o]
        del m[o]
    return m

def subMap(m:dict,ks:list):
    ''' get a map subset by keys,if keys not found, supplied with default value '''
    return {k:m.get(k,defaultVal) for (k,defaultVal) in ks}

def subMap2(m:dict,ks:list):
    fieldNames = [ fName for (fName,fTargetName,fDefaultValue) in ks]
    _m = {k:m.get(k,defaultVal) for (k,_,defaultVal) in ks}
    _mapping = [ _[:2] for _ in ks ]
    return renameKs(_m,_mapping)

def mapValsBy(m:dict, f):
    ''' Given a map and apply function to every vals'''
    assert isinstance(m, dict),f"M is not a map but a {type(m)},{m}"
    return {k: f(v) for k,v in m.items()}

def mapListValBy(m:dict, f):
    ''' Given a map, whose vals are list,  apply function to every element in each list of each val'''
    assert isinstance(m, dict),"M is not a map"
    return {k: [f(_v) for _v in v] for k,v in m.items()}

def applyFnToKey(m:dict, f, k, applyNone=False):
    assert isinstance(m, dict),f"{m} is not a map"
    assert k in m, f"{k} is not in map {m}"
    match (m[k],applyNone):
        case (None,True):
            m[k] = f(m[k])
        case (None,False):
            pass
        case (_, _):
            m[k] = f(m[k])
    return m

def renameKs2(m:dict,kmapping):
    ''' Given a map, rename ks from a key-mapping '''
    assert isinstance(m, dict), "M is not a map"
    assert isinstance(kmapping, dict), f"Mapping is not a map: {kmapping}"
    assert set(m.keys()).issubset(set(kmapping.keys())), f"{m.keys()} not in {kmapping.keys()}"
    return {kmapping[k]:v for k, v in m.items()}

def ensure100(xs,msg=""):
    assert sum(xs)==1.0,f"Doesn't not sum up 100%: {msg}"

def guess_pool_flow_header(x,l):
    assert isinstance(x, dict), f"x is not a map but {x}, type:{type(x)}"
    match (x['tag'],l):
        case ('MortgageDelinqFlow','chinese'):
            return (china_mortgage_delinq_flow_fields_d,"日期")
        case ('MortgageDelinqFlow','english'):
            return (english_mortgage_delinq_flow_fields_d,"Date")
        case ('MortgageFlow','chinese'):
            return (china_mortgage_flow_fields_d,"日期")
        case ('MortgageFlow','english'):
            return (english_mortgage_flow_fields_d,"Date")
        case ('LoanFlow','chinese'):
            return (china_loan_flow_d,"日期")
        case ('LoanFlow','english'):
            return (english_loan_flow_d,"Date")
        case ('LeaseFlow','chinese'):
            return (china_rental_flow_d,"日期")
        case ('LeaseFlow','english'):
            return (english_rental_flow_d,"Date")
        case _:
            raise RuntimeError(f"Failed to match pool header with {x['tag']}{l}")

def uplift_m_list(l:list):
    return {k:v
            for m in l
            for k,v in m.items()}

def getValWithKs(m:dict,ks:list,defaultReturn=None):
    ''' Get first available key/value in m'''
    if isinstance(m, dict):
        for k in ks:
            if k in m:
                return m[k]
    else:
        for k in ks:
            if hasattr(m, k):
                return getattr(m, k)
    return defaultReturn

def _read_cf(x, lang):
    ''' read cashflow from a list , and set index to date'''
    if x == []:
        return []
    flow_header,idx = guess_pool_flow_header(x[0],lang)
    try:
        result = pd.DataFrame([_['contents'] for _ in x] , columns=flow_header)
    except ValueError as e:
        logging.error(f"Failed to match header:{flow_header} with {result[0]['contents']}")
    result.set_index(idx, inplace=True)
    result.index.rename(idx, inplace=True)
    result.sort_index(inplace=True)
    return result

def _read_asset_pricing(xs, lang):
    header = assetPricingHeader[lang]
    data = [ x['contents'] for x in xs]
    return pd.DataFrame(data, columns = header)

def mergeStrWithDict(s:str,m:dict) -> str:
    t = json.loads(s)
    t = t | m 
    return json.dumps(t)

def flow_by_scenario(rs, flowpath, node="col", rtn_df=True, ax = 1, rnd=2):
    "pull flows from multiple scenario"
    r = None
    if node=="col":
        r = {k:query(v,flowpath[:-1])[flowpath[-1]] for k,v  in rs.items()}    
    elif node=="idx":
        r = {k:query(v,flowpath[:-1]).loc[flowpath[-1]] for k,v  in rs.items()}    
    else:
        r = {k:query(v,flowpath) for k,v in rs.items()}
    if rtn_df:
        _vs = list(r.values())
        _ks = list(r.keys())
        r = pd.concat(_vs,keys=_ks,axis=ax) 
    return r

def positionFlow(x,m:dict,facePerPaper=100):
    _,_bflow = list(x['bonds'].items())[0]
    bflowHeader = _bflow.columns.to_list()

    def calcBondFlow(_bflow,factor):
        bflow = copy.deepcopy(_bflow)
        bflow[bflowHeader[0]] *= factor
        bflow[bflowHeader[1]] *= factor
        bflow[bflowHeader[2]] *= factor
        bflow[bflowHeader[4]] *= factor
        return bflow
        
    assert isinstance(m, dict),"Position info must be a map/dict"
    
    bOrignBal = {k:x['_deal']['contents']['bonds'][k]['bndOriginInfo']['originBalance'] for k,v in m.items()}
    bPapersPerBond = {k:v/facePerPaper for k,v in bOrignBal.items()}
    
    bflowFactor = {k:(v/bPapersPerBond[k]) for k,v in m.items()}
    
    return {bn:calcBondFlow(bf,bflowFactor[bn])  for bn,bf in x['bonds'].items() if bn in m}

def tryConvertTupleToDict(xs):
    if isinstance(xs, tuple):
        return {n:v for n,v in xs}
    elif isinstance(xs, dict):
        return xs
    else:
        raise RuntimeError(f"Failed to match <convertTupleToDict> ,either Map or Tuple but got {type(xs)}")

def allKeysAreString(m:dict):
    return all([ isinstance(_, str) for _ in m.keys()])

def earlyReturnNone(fn, v):
    if v is None:
        return None
    else:
        return fn(v)

def searchByFst(xs,v,defaultRtn=None):
    "search by first element in a list, return None if not found"
    for x in xs:
        if x[0] == v:
            return x
    return defaultRtn


