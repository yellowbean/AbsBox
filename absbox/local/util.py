import pandas as pd
import functools,json
import itertools,re
from enum import Enum
import numpy as np
from functools import reduce
from pyxirr import xirr,xnpv

from absbox.local.base import *

def flat(xss) -> list:
    return reduce(lambda xs, ys: xs + ys, xss)


def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}

def readTagStr(x:str):
    _x = json.loads(x.replace("'","\""))
    if 'contents' in _x:
        return f"<{_x['tag']}:{','.join(_x['contents'])}>"
    return f"<{_x['tag']}>"

def readTag(x:dict):
    return f"<{x['tag']}:{','.join(x['contents'])}>"


def isDate(x):
    return re.match(r"\d{4}\-\d{2}\-\d{2}",x)


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


def backFillBal(x,ds):
    b = pd.DataFrame({"日期": ds})
    b.set_index("日期", inplace=True)
    base = pd.concat([b, x], axis=1).sort_index()
    paidOffDate = None
    r = None
    if any(base['余额']==0):
        paidOffDate = base[base['余额']==0].index[0]
        base['flag'] = (base.index >= paidOffDate)
        base.loc[base['flag']==True, "余额"] = 0
        base.loc[base['flag']==False, "余额"] = (base["余额"] + base["本金"]).shift(-1).fillna(method='bfill')
        r = base.drop(["flag"], axis=1)
    else:
        last_index = base.index.to_list()[-1]
        last_keep_balance = base.at[last_index, "余额"]
        base["余额"] = (base["余额"] + base["本金"]).shift(-1).fillna(method='bfill')
        base.at[last_index, "余额"] = last_keep_balance
        r = base
    return r 


def bondView(r,flow=None, flowName=True,flowDates=None,rnd=2):
    result = []
    default_bnd_col_size = 6
    bnd_names = r['bonds'].keys()

    b_dates = [ set(r['bonds'][bn].index.tolist()) for bn in bnd_names ]
    all_b_dates = set()
    for bd in b_dates:
        all_b_dates = all_b_dates | bd
    all_b_dates_s = list(all_b_dates)
    all_b_dates_s.sort()
    if flowDates is None:
        flowDates = all_b_dates_s

    for (bn, bnd) in r['bonds'].items():
        if flow :
            result.append(backFillBal(bnd,flowDates)[flow])
        else:
            result.append(backFillBal(bnd,flowDates))
    
    x = pd.concat(result,axis=1)
    bnd_cols_count = len(flow) if flow else default_bnd_col_size
    headers = [ bnd_cols_count*[bn] for bn in bnd_names]
    if flowName:
        x.columns = [ list(itertools.chain.from_iterable(headers)) ,x.columns]
    else:
        x.columns = list(itertools.chain.from_iterable(headers)) 
    return x.sort_index().round(rnd)


def accView(r, flow=None, flowName=True):
    result = []
    default_acc_col_size = 3
    acc_names = r['accounts'].keys()
    for (an, acc) in r['accounts'].items():
        if flow :
            result.append(acc.groupby("日期").last()[flow])
        else:
            result.append(acc.groupby("日期").last())
        
    x = pd.concat(result,axis=1)
    
    account_cols_count = len(flow) if flow else default_acc_col_size
    headers = [ account_cols_count*[an] for an in acc_names]
    if flowName:
        x.columns = [ list(itertools.chain.from_iterable(headers)) ,x.columns]
    else:
        x.columns = list(itertools.chain.from_iterable(headers)) 
    
    return x.sort_index()

def feeView(r,flow=None):
    fees = r['fees']
    feeNames = list(fees.keys())
    feeVals = list(fees.values())
    if flow is None:
        return unify(feeVals, feeNames)
    else:
        newFees = [ _f[flow] for _f in feeVals]
        return unify(newFees,feeNames)


def peekAtDates(x,ds):
    x_consol = x.groupby(["日期"]).last()

    if x_consol.index.get_indexer(ds,method='pad').min()==-1:
        raise RuntimeError(f"<查看日期:{ds}>早于当前DataFrame")

    keep_idx = [x_consol.index.asof(d) for d in ds]
    y = x_consol.loc[keep_idx]
    y.reset_index("日期")
    y["日期"] = ds
    return y.set_index("日期")


def balanceSheetView(r, ds=None, equity=None, rnd=2):
    bv = bondView(r, flow=["余额"],flowDates=ds,flowName=False)
    av = accView(r, flow=["余额"],flowName=False)

    pv = r['pool']['flow'][["未偿余额"]]
    if "违约金额" in r['pool']['flow'] and "回收金额" in r['pool']['flow']:
        r['pool']["flow"]["不良"] = r['pool']['flow']["违约金额"].cumsum() - r['pool']['flow']["回收金额"].cumsum()
        pv = r['pool']['flow'][["未偿余额","不良"]]
    if equity:
        equityFlow = bondView(r, flow=["本息合计"],flowDates=ds,flowName=False)[equity]
        equityFlow.columns = pd.MultiIndex.from_arrays([["权益"]*len(equity), list(equityFlow.columns)])
        equityFlow["权益", f"合计分配{equity}"] = equityFlow.sum(axis=1)
    if ds is None:
        ds = list(bv.index)

    if equity:
        bv.drop(columns=equity, inplace=True)

    try:
        pvCol, avCol = [ peekAtDates(_, ds) for _ in [pv, av] ]
        # need to add cutoff amount for equity tranche
        for k, _ in [("资产池", pvCol), ("账户", avCol), ("债券", bv)]:
            _[f'{k}-合计'] = _.sum(axis=1)
        

        asset_cols = (len(pvCol.columns)+len(avCol.columns))*["资产"]
        liability_cols = len(bv.columns)*["负债"]
        header = asset_cols + liability_cols

        bs = pd.concat([pvCol, avCol, bv], axis=1)
        bs.columns = pd.MultiIndex.from_arrays([header, list(bs.columns)])
        bs["资产", "合计"] = bs["资产", "资产池-合计"]+bs["资产", "账户-合计"]
        bs["负债", "合计"] = bs["负债", "债券-合计"]
        if equity:
            bs["权益", "累计分配"] = equityFlow["权益", f"合计分配{equity}"].cumsum()
            bs["权益", "合计"] = bs["资产", "合计"] - bs["负债", "合计"] + bs["权益", "累计分配"]
        else:
            bs["权益", "合计"] = bs["资产", "合计"] - bs["负债", "合计"] 

    except RuntimeError as e:              
        print(f"Error: 其他错误=>{e}")      
    
    return bs.round(rnd) # unify([pvCol,avCol,bvCol],["资产-资产池","资产-账户","负债"])


def PnLView(r,ds=None):
    accounts = r['accounts']
    consoleStmts = pd.concat([ acc for acc in accounts ])
    return consoleStmts


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
    "A patch function to update a deal data list in immuntable way"
    _d = d.copy()
    _d.pop(i)
    _d.insert(i,c)
    return _d


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

    
