import pandas as pd 
import functools
import itertools,re
from enum import Enum
import numpy as np
from functools import reduce

def query(d,p):
    if len(p)==1:
        return d[p[0]]
    else:
        if p[0] in d:
            return query(d[p[0]],p[1:])
        else:
            return None

def flat(xss) -> list:
    return reduce(lambda xs, ys: xs + ys, xss)


def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}


def isDate(x):
    return re.match(r"\d{4}\-\d{2}\-\d{2}",x)


def mkTs(n, vs):
    return mkTag((n, vs))


def backFillBal(x,ds):
    b = pd.DataFrame({"日期":ds})
    b.set_index("日期",inplace=True)
    base = pd.concat([b,x],axis=1).sort_index()
    paidOffDate = base[base['余额']==0].index[0]
    base['flag'] = (base.index >= paidOffDate)
    base.loc[base['flag']==True,"余额"]=0
    base.loc[base['flag']==False,"余额"]= (base["余额"] + base["本金"]).shift(-1).fillna(method='bfill')
    return base


def unify(xs, ns):
    index_name = xs[0].index.name
    dfs = []
    for x, n in zip(xs, ns):
        dfs.append(pd.concat([x], keys=[n], axis=1))
    r = functools.reduce(lambda acc, x: acc.merge(x
                                                , how='outer'
                                                , on=[index_name])
                        , dfs)
    return r.sort_index()

def backFillBal(x,ds):
    b = pd.DataFrame({"日期": ds})
    b.set_index("日期", inplace=True)
    base = pd.concat([b, x], axis=1).sort_index()
    paidOffDate = base[base['余额']==0].index[0]
    base['flag'] = (base.index >= paidOffDate)
    base.loc[base['flag']==True, "余额"] = 0
    base.loc[base['flag']==False, "余额"] = (base["余额"] + base["本金"]).shift(-1).fillna(method='bfill')
    return base.drop(["flag"], axis=1)


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

    # build PnL
     #   pool_index = r['pool']['flow'].index
     #   agg_flag = bs.index.get_indexer(list(pool_index),method='ffill')
     #   pool_cpy = r['pool']['flow'].copy(deep=True)
     #   pool_cpy['flag'] = agg_flag
     #   pool_cpy = pool_cpy.groupby("flag", sort=False).aggregate(np.sum)
     #   new_index_length = min(len(pool_cpy.index), len(bs.index))
     #   #pool_cpy.index = bs.index[:len(pool_cpy.index)]
     #   print(pool_cpy)
     #   print(bs)
     #   pool_cpy.index = bs.index[:new_index_length]

     #   poolIntflow = pool_cpy['利息']
     #   poolPrinflow = pool_cpy['本金']
     #   poolPpyflow = pool_cpy['早偿金额']
     #   poolRecflow = pool_cpy['回收金额']

     #   feeFlow = feeView(r,flow="支付")
     #   feeFlow["合计"] = feeFlow.sum(axis=1)
     #   agg_flag = bs.index.get_indexer(list(feeFlow.index),method='bfill')
     #   feeFlow['flag'] = agg_flag
     #   feeFlow.groupby("flag").aggregate(np.sum)
     #   feeFlow.index = bs.index
     #   
     #   liability_p_v = bondView(r,flow="本金")
     #   liability_p_v['合计'] = liability_p_v.sum(axis=1)
     #   liability_i_v = bondView(r,flow="利息")
     #   liability_i_v['合计'] = liability_i_v.sum(axis=1)

     #   bs["收入","本金"] = poolPrinflow
     #   bs["收入","利息"] = poolIntflow
     #   bs["收入","早偿"] = poolPpyflow
     #   bs["收入","回收"] = poolRecflow

     #   bs["支出","负债-本金"] = liability_p_v['合计']
     #   bs["支出","负债-利息"] = liability_i_v['合计']
     #   bs["支出","负债-费用"] = feeFlow['合计']
     #   
     #   bs["利润","合计"] = bs["收入","本金"] + bs["收入","利息"] + bs["收入","早偿"] + bs["收入","回收"]
     #   bs["利润","合计"] = bs["利润","合计"] - bs["支出","负债-本金"] - bs["支出","负债-利息"] - bs["支出","负债-费用"]

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
