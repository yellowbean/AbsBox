import pandas as pd
import functools,json,copy,logging,re,itertools
from functools import reduce
from absbox.local.base import *
from datetime import datetime
from lenses import lens,ui, optics
import toolz as tz


def mapNone(x, v):
    ''' return a default value if x is None, other wise, return x '''
    if x is None:
        return v
    else:
        return x


def lmap(f, xs):
    ''' just make it looks more functional '''
    return list(map(f, xs))


def flat(xss) -> list:
    return reduce(lambda xs, ys: xs + ys, xss)


def mkTag(x: tuple | str) -> dict:
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}


def filter_by_tags(xs: list, tags: list) -> list:
    ''' fiter a list of maps by tags'''
    tags_set = set(tags)
    return [x for x in xs if x['tag'] in tags_set]


def readTagStr(x: str) -> str:
    x = json.loads(x.replace("'", "\"").replace("True", "true").replace("False", "false").replace("None","null"))
    return readTagMap(x)

def readTagMap(x:dict) -> str:
    match x:
        case {"tag": _t, "contents": None}:
            return f"<{_t}>"
        case {"tag": _t, "contents": _c} if isinstance(_c, list):
            return f"<{_t}:{','.join([ readTagMap(_) for _ in _c])}>"
        case {"tag": _t,"contents":_c} if isinstance(_c, str):
            return f"<{_t}:{_c}>"
        case {"tag": _t,"contents":_c} if isinstance(_c, dict):
            return f"<{_t}:{readTagMap(_c)}>"
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
mkRateTs = functools.partial(mkTs, "IRateCurve")
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
    df[dummy_col] = pd.to_datetime(df[dummy_col]).dt.to_period(_mapping[interval])
    return df.groupby([dummy_col])[cols].sum().rename_axis(idx)


def update_deal(d, i, c): #Deprecated ,to be replace with Lens
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
    ''' Guess local from deal map'''
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


def mapValsBy(m: dict, f: callable):
    ''' Given a map and apply function to every vals'''
    assert isinstance(m, dict), f"M is not a map but a {type(m)}, {m}"
    return {k: f(v) for k, v in m.items()}


def mapListValBy(m: dict, f: callable):
    ''' Given a map, whose vals are list,  apply function to every element in each list of each val'''
    assert isinstance(m, dict), "M is not a map"
    return {k: [f(_v) for _v in v] for k,v in m.items()}


def applyFnToKey(m: dict, f, k, applyNone=False):
    assert isinstance(m, dict), f"{m} is not a map"
    assert k in m, f"{k} is not in map {m}"
    assert callable(f), "funciton passed in is not callable"
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
        case ('ReceivableFlow', 9, 'chinese'):
            return (china_receivable_flow_d+china_cumStats, "日期", True)
        case ('ReceivableFlow', 9, 'english'):
            return (english_receivable_flow_d+english_cumStats, "Date", True)
        case ('BondFlow', 4, 'chinese'):
            return (china_uBond_flow_d, "日期", False)
        case ('BondFlow', 4, 'english'):
            return (english_uBond_flow_d, "Date", False)
        case _:
            raise RuntimeError(f"Failed to match pool header with {x['tag']},{len(x['contents'])},{l}")


def inferPoolTypeFromAst(x:dict) -> str:
    match x:
        case {"assets":[["Mortgage",*fields],*ast]} | {"assets":[["AdjustRateMortgage",*fields],*ast]} | {'清单': [['按揭贷款', *fields], *ast]}:
            return "MPool"
        case {"assets":[["Loan",*fields],*ast]} | {'清单': [['贷款', *fields], *ast]}:
            return "LPool"
        case {"assets":[["Installment",*fields],*ast]} | {'清单': [['分期', *fields], *ast]}:
            return "IPool"
        case {"assets":[["Lease",*fields],*ast]} | {'清单': [['租赁', *fields], *ast]}:
            return "RPool"
        case {"assets":[["FixedAsset",*fields],*ast]}:
            return "FPool"
        case {"assets":[["Invoice",*fields],*ast]} | {'清单': [['应收账款', *fields], *ast]}:
            return "VPool"
        case {"assets":[["ProjectedFlowMix",*fields],*ast]} | {"assets":[["ProjectedFlowFix",*fields],*ast]} :
            return "PPool"
        case _:
            raise RuntimeError(f"Failed to find pool type from assets:{x}")
    


def uplift_m_list(l: list):
    """ input a list of dictionary, reduce the maps into a big map """
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
    result = None
    try:
        if expandFlag:
            result = pd.DataFrame([_['contents'][:-1]+mapNone(_['contents'][-1],[0,0,0,0,0,0]) for _ in x], columns=flow_header)
        else:
            result = pd.DataFrame([_['contents'] for _ in x], columns=flow_header)
    except ValueError as e:
        print(e)
        logging.error(f"Failed to match header:{flow_header} with {result}")
        return False
    result.set_index(idx, inplace=True)
    result.index.rename(idx, inplace=True)
    result.sort_index(inplace=True)
    return result


def _read_asset_pricing(xs, lang) -> pd.DataFrame:
    return pd.DataFrame(tz.pluck("contents", xs)
            , columns=assetPricingHeader[lang])


def mergeStrWithDict(s: str, m: dict) -> str:
    ''' merge a map to a string'''
    t = json.loads(s)
    return json.dumps(t | m)


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


def searchByFst(xs:list, v, defaultRtn=None):
    "search by first element in a list, return None if not found"
    for x in xs:
        if x[0] == v:
            return x
    return defaultRtn


def isMixedDeal(x: dict) -> bool:
    ''' check if pool of deals has mixed asset types'''    
    if 'assets' in x or 'cashflow' in x:
        return False
    if '清单' in x or '归集表' in x:
        return False
    if 'deals' in x:
        return False
    assetTags = x & lens.Values().Each()[1][0][0].collect()
    if len(set(assetTags)) > 1:
        return True
    return False


def strFromPath(xs: list) -> str:
    ps = [strFromLens(_)+f":{v}" for (_, v) in xs]
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


def enumVals(e) -> list:
    ''' return a list of enum values '''
    return [_.value for _ in [*e]]

def readCfFromLst(lst:list)-> pd.DataFrame:
    return None

def tupleToDictWithKey(xs,key="name"):
    return dict([ (n,x|{key:n}) for (n,x) in xs ])


def patchDicts(dict1:dict,dict2:dict)-> dict:
    """
    Merge two dictionaries, if a key exists in both dictionaries,use the value from dict2
    if key only exists in either one, use the only one value
    """
    return tz.merge_with(lambda xs: xs[1] if len(xs)==2 else xs[0]
                         ,dict1
                         ,dict2)
