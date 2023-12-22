import pandas as pd
import numpy as np
import functools,json,copy,logging,re,itertools
from enum import Enum
from functools import reduce
from absbox.local.base import *
from pyspecter import query, S
from datetime import datetime
import rich
from rich.console import Console
from rich.json import JSON
from lenses import lens, ui, optics

console = Console()

def mapNone(x, v):
    if x is None:
        return v
    else:
        return x


def flat(xss) -> list:
    return reduce(lambda xs, ys: xs + ys, xss)


def mkTag(x: tuple) -> dict:
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}


def readTagStr(x: str) -> str:
    x = json.loads(x.replace("'", "\"").replace("True", "true").replace("False", "false").replace("None","null"))
    match x:
        case {"tag": _t, "contents": None}:
            return f"<{_t}>"
        case {"tag": _t, "contents": _c} if isinstance(_c, list):
            _cs = [str(_) for _ in _c]
            return f"<{_t}:{','.join(_cs)}>"
        case {"tag": _t}:
            return f"<{_t}>"
        case _ :
            return f"<{x}>"


def readTag(x: dict):
    return f"<{x['tag']}:{','.join(x['contents'])}>"


def isDate(x):
    return re.match(r"\d{4}\-\d{2}\-\d{2}", x)


def allList(xs):
    return all([isinstance(x, list) for x in xs])


def mkTs(n, vs):
    return mkTag((n, vs))


def mkTbl(n, vs):
    return mkTag((n, vs))


mkRatioTs = functools.partial(mkTs, "RatioCurve")

mkRateTs = functools.partial(mkTs, "RateCurve")

mkBalTs = functools.partial(mkTs, "BalanceCurve")

mkFloatTs = functools.partial(mkTs, "FloatCurve")


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
    _mapping = {"月份": "M", "Month": "M", "M": "M", "month": "M"}
    if df.index.name == "日期":
        idx = "日期"
    else:
        idx = "date"
    df[dummy_col]=pd.to_datetime(df[dummy_col]).dt.to_period(_mapping[interval])
    return df.groupby([dummy_col])[cols].sum().rename_axis(idx)


def update_deal(d, i, c):
    "A patch function to update a deal data component list in immuntable way"
    _d = d.copy()
    _d.pop(i)
    _d.insert(i, c)
    return _d


def str2date(x: str):
    return datetime.strptime(x, '%Y-%m-%d').date()


def normDate(x: str):
    if len(x) == 8:
        return f"{x[:4]}-{x[4:6]}-{x[6:8]}"


def daysBetween(sd, ed):
    return (ed - sd).days


def guess_locale(x):
    accs = x['accounts']

    assert len(accs) > 0, "Failed to identify via deal accounts result"

    acc_cols = set(list(accs.values())[0].columns.to_list())
    locale = None
    if acc_cols == set(["余额", "变动额", "备注"]):
        locale = "cn"
    if acc_cols == set(["balance", "change", "memo"]):
        locale = "en"
    return locale


def guess_pool_locale(x):
    if "cutoffDate" in x:
        return "english"
    elif '封包日' in x:
        return "chinese"
    else:
        raise RuntimeError("Failed to match {x} in guess pool locale")


def renameKs(m: dict, mapping, opt_key=False):
    '''
    rename keys in a map with from a mapping tuple passed in 
    `opt_key` = True, allow skipping mapping tuple not exist in the map
    '''
    for (o, n) in mapping:
        if opt_key and o not in m:
            continue
        m[n] = m[o]
        del m[o]
    return m


def subMap(m: dict, ks: list):
    ''' get a map subset by keys,if keys not found, supplied with default value '''
    return {k: m.get(k, defaultVal) for (k, defaultVal) in ks}


def subMap2(m: dict, ks: list):
    _m = {k: m.get(k, defaultVal) for (k, _, defaultVal) in ks}
    _mapping = [_[:2] for _ in ks]
    return renameKs(_m, _mapping)


def mapValsBy(m: dict, f):
    ''' Given a map and apply function to every vals'''
    assert isinstance(m, dict), f"M is not a map but a {type(m)}, {m}"
    return {k: f(v) for k, v in m.items()}


def mapListValBy(m: dict, f):
    ''' Given a map, whose vals are list,  apply function to every element in each list of each val'''
    assert isinstance(m, dict), "M is not a map"
    return {k: [f(_v) for _v in v] for k,v in m.items()}


def applyFnToKey(m: dict, f, k, applyNone=False):
    assert isinstance(m, dict), f"{m} is not a map"
    assert k in m, f"{k} is not in map {m}"
    match (m[k], applyNone):
        case (None, True):
            m[k] = f(m[k])
        case (None, False):
            pass
        case (_, _):
            m[k] = f(m[k])
    return m


def renameKs2(m: dict, kmapping):
    ''' Given a map, rename ks from a key-mapping '''
    assert isinstance(m, dict), "M is not a map"
    assert isinstance(kmapping, dict), f"Mapping is not a map: {kmapping}"
    assert set(m.keys()).issubset(set(kmapping.keys())), f"{m.keys()} not in {kmapping.keys()}"
    return {kmapping[k]: v for k, v in m.items()}


def ensure100(xs, msg=""):
    assert sum(xs) == 1.0, f"Doesn't not sum up 100%: {msg}"


def guess_pool_flow_header(x, l):
    assert isinstance(x, dict), f"x is not a map but {x}, type:{type(x)}"
    match (x['tag'], len(x['contents']), l):
        case ('MortgageDelinqFlow', 12, 'chinese'):
            return (china_mortgage_delinq_flow_fields_d, "日期", False)
        case ('MortgageDelinqFlow', 13, 'chinese'):
            return (china_mortgage_delinq_flow_fields_d+china_cumStats, "日期", True)
        case ('MortgageDelinqFlow', 12, 'english'):
            return (english_mortgage_delinq_flow_fields_d, "Date", False)
        case ('MortgageDelinqFlow', 13, 'english'):
            return (english_mortgage_delinq_flow_fields_d+english_cumStats, "Date", True)
        case ('MortgageFlow', 11, 'chinese'):
            return (china_mortgage_flow_fields_d, "日期", False)
        case ('MortgageFlow', 12, 'chinese'):
            return (china_mortgage_flow_fields_d+china_cumStats, "日期", True)
        case ('MortgageFlow', 11, 'english'):
            return (english_mortgage_flow_fields_d, "Date", False)
        case ('MortgageFlow', 12, 'english'):
            return (english_mortgage_flow_fields_d+english_cumStats, "Date", True)
        case ('LoanFlow', 9, 'chinese'):
            return (china_loan_flow_d, "日期", False)
        case ('LoanFlow', 10, 'chinese'):
            return (china_loan_flow_d+china_cumStats, "日期", True)
        case ('LoanFlow', 9, 'english'):
            return (english_loan_flow_d, "Date", False)
        case ('LoanFlow', 10, 'english'):
            return (english_loan_flow_d+english_cumStats, "Date", True)
        case ('LeaseFlow', 3, 'chinese'):
            return (china_rental_flow_d, "日期", False)
        case ('LeaseFlow', 3, 'english'):
            return (english_rental_flow_d, "Date", False)
        case ('FixedFlow', 6, 'chinese'):
            return (china_fixed_flow_d, "日期", False)
        case ('FixedFlow', 6, 'english'):
            return (english_fixed_flow_d, "Date", False)
        case _:
            raise RuntimeError(f"Failed to match pool header with {x['tag']}{l}")


def uplift_m_list(l: list):
    return {k: v for m in l for k, v in m.items()}


def getValWithKs(m: dict, ks: list, defaultReturn=None, mapping=None):
    ''' Get first available key/value in m, with optional mapping function to result if found '''
    r = defaultReturn
    if isinstance(m, dict):
        for k in ks:
            if k in m:
                r = m[k]
                break
    else:  # object instead of dict
        for k in ks:
            if hasattr(m, k):
                r = getattr(m, k)
                break
    if (r is not None) and (mapping is not None):
        return mapping(r)
    return r


def _read_cf(x, lang):
    ''' read cashflow from a list , and set index to date'''
    if x == []:
        return []
    flow_header, idx, expandFlag = guess_pool_flow_header(x[0], lang)
    try:
        if not expandFlag:
            result = pd.DataFrame([_['contents'] for _ in x], columns=flow_header)
        else:
            result = pd.DataFrame([_['contents'][:-1]+_['contents'][-1] for _ in x], columns=flow_header)
    except ValueError as e:
        print(e)
        logging.error(f"Failed to match header:{flow_header} with {result[0]['contents']}")
        return False
    result.set_index(idx, inplace=True)
    result.index.rename(idx, inplace=True)
    result.sort_index(inplace=True)
    return result


def _read_asset_pricing(xs, lang):
    header = assetPricingHeader[lang]
    data = [x['contents'] for x in xs]
    return pd.DataFrame(data, columns=header)


def mergeStrWithDict(s: str, m: dict) -> str:
    t = json.loads(s)
    t = t | m
    return json.dumps(t)


def flow_by_scenario(rs, flowpath, node="col", rtn_df=True, ax=1, rnd=2):
    "pull flows from multiple scenario"
    r = None
    if node == "col":
        r = {k: query(v, flowpath[:-1])[flowpath[-1]] for k, v in rs.items()}    
    elif node == "idx":
        r = {k: query(v, flowpath[:-1]).loc[flowpath[-1]] for k, v in rs.items()}    
    else:
        r = {k: query(v, flowpath) for k, v in rs.items()}
    if rtn_df:
        _vs = list(r.values())
        _ks = list(r.keys())
        r = pd.concat(_vs, keys=_ks, axis=ax) 
    return r


def positionFlow(x, m: dict, facePerPaper=100):
    ''' Get a position bond cashflow from a run result '''
    _, _bflow = list(x['bonds'].items())[0]
    bflowHeader = _bflow.columns.to_list()

    def calcBondFlow(_bflow: pd.DataFrame, factor):
        ''' input: (bond cashflow : dataframe, factor: float) '''
        bflow = copy.deepcopy(_bflow)
        bflow[bflowHeader[0]] *= factor
        bflow[bflowHeader[1]] *= factor
        bflow[bflowHeader[2]] *= factor
        bflow[bflowHeader[4]] *= factor
        return bflow
        
    assert isinstance(m, dict), "Position info must be a map/dict"
    
    bOrignBal = {bondName: x['_deal']['contents']['bonds'][bondName]['bndOriginInfo']['originBalance'] for bondName, bondPos in m.items()}
    bPapersPerBond = {bondName: bondOrigBal/facePerPaper for (bondName, bondOrigBal) in bOrignBal.items()}
    bflowFactor = {bondName: (bondPos/bPapersPerBond[bondName]) for (bondName, bondPos) in m.items()}
    return {bn: calcBondFlow(bf, bflowFactor[bn]) for bn, bf in x['bonds'].items() if bn in m}


def tryConvertTupleToDict(xs):
    "build a dictionary from a tuple"
    if isinstance(xs, tuple):
        return {n: v for n, v in xs}
    elif isinstance(xs, dict):
        return xs
    else:
        raise RuntimeError(f"Failed to match <convertTupleToDict> ,either Map or Tuple but got {type(xs)}")


def allKeysAreString(m: dict):
    return all([isinstance(_, str) for _ in m.keys()])


def earlyReturnNone(fn: callable, v):
    "return None if passed in a None, otherwise apply fn and return"
    if v is None:
        return None
    else:
        return fn(v)


def searchByFst(xs, v, defaultRtn=None):
    "search by first element in a list, return None if not found"
    for x in xs:
        if x[0] == v:
            return x
    return defaultRtn


def isMixedDeal(x: dict) -> bool :
    if 'assets' in x or 'cashflow' in x:
        return False
    assetTags = query(x, [S.MVALS, S.ALL, 'assets', S.FIRST, S.FIRST])
    if len(set(assetTags)) > 1:
        return True
    return False


def strFromPath(xs: list) -> str:
    ps = [strFromLens(_)+f":{v}" for (_,v) in xs]
    return "/".join(ps)


def strFromLens(x) -> str: 
    if isinstance(x, ui.UnboundLens) and not hasattr(x._optic, "lenses"):
        if isinstance(x._optic, optics.true_lenses.GetitemLens):
            return str(x._optic.key)
        return x._optic.name
    elif isinstance(x, ui.UnboundLens) and hasattr(x._optic, "lenses"):
        return "-".join([strFromLens(_) for _ in x._optic.lenses])
    elif isinstance(x, optics.true_lenses.GetitemLens):
        return str(x.key)
    elif isinstance(x, optics.traversals.GetZoomAttrTraversal):
        return x.name   
    else:
        return str(x)