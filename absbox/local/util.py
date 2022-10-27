import pandas as pd 
import functools
from enum import Enum
import numpy as np


def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}


def mkTs(n, vs):
    return mkTag((n, vs))

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

def bondView(r,flow=None):
    bnds = r['bonds']
    bndNames = list(bnds.keys())
    bndVals = list(bnds.values())
    if flow is None:
        return unify(bndVals,bndNames)
    else:
        newBnds = [ _b[flow] for _b in bndVals] 
        return unify(newBnds,bndNames)

def accView(r,flow=None):
    accs = r['accounts']
    accNames = list(accs.keys())
    accVals = list(accs.values())
    if flow is None:
        return unify(accVals, accNames)
    else:
        newAccs = [ _a[flow] for _a in accVals]
        return unify(newAccs,accNames)

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

    keep_idx = [ x_consol.index.asof(d) for d in ds ]
    y = x_consol.loc[keep_idx]
    y.reset_index("日期")
    y["日期"] = ds
    return y.set_index("日期")


def balanceSheetView(r, ds=None, equity=None, rnd=2):
    bv = bondView(r, flow="余额")
    av = accView(r, flow="余额")
    pv = r['pool']['flow'][["未偿余额"]]
    if equity:
        equityFlow = bondView(r, flow="本息合计")[equity]
        equityFlow.columns = pd.MultiIndex.from_arrays([["权益"]*len(equity), list(equityFlow.columns)])
        equityFlow["权益", f"合计分配{equity}"] = equityFlow.sum(axis=1)
    if ds is None:
        ds = list(bv.index)

    if equity:
        bv.drop(columns=equity, inplace=True)

    try:
        pvCol, avCol, bvCol = [ peekAtDates(_, ds) for _ in [pv, av, bv] ]
        # need to add cutoff amount for equity tranche
        for k, _ in [("资产池", pvCol), ("账户", avCol), ("债券", bvCol)]:
            _[f'{k}-合计'] = _.sum(axis=1)

        asset_cols = (len(pvCol.columns)+len(avCol.columns))*["资产"]
        liability_cols = len(bvCol.columns)*["负债"]
        header = asset_cols + liability_cols

        bs = pd.concat([pvCol, avCol, bvCol], axis=1)
        bs.columns = pd.MultiIndex.from_arrays([header, list(bs.columns)])
        bs["资产", "合计"] = bs["资产", "资产池-合计"]+bs["资产", "账户-合计"]
        bs["负债", "合计"] = bs["负债", "债券-合计"]
        if equity:
            bs["权益", "累计分配"] = equityFlow["权益", f"合计分配{equity}"].cumsum()
            bs["权益", "合计"] = bs["资产", "合计"] - bs["负债", "合计"] + bs["权益", "累计分配"]
        else:
            bs["权益", "合计"] = bs["资产", "合计"] - bs["负债", "合计"] 

    # build PnL
        pool_index = r['pool']['flow'].index
        agg_flag = bs.index.get_indexer(list(pool_index),method='ffill')
        pool_cpy = r['pool']['flow'].copy(deep=True)
        pool_cpy['flag'] = agg_flag
        pool_cpy = pool_cpy.groupby("flag", sort=False).aggregate(np.sum)
        new_index_length = min(len(pool_cpy.index), len(bs.index))
        #pool_cpy.index = bs.index[:len(pool_cpy.index)]
        print(pool_cpy)
        print(bs)
        pool_cpy.index = bs.index[:new_index_length]

        poolIntflow = pool_cpy['利息']
        poolPrinflow = pool_cpy['本金']
        poolPpyflow = pool_cpy['早偿金额']
        poolRecflow = pool_cpy['回收金额']

        feeFlow = feeView(r,flow="支付")
        feeFlow["合计"] = feeFlow.sum(axis=1)
        agg_flag = bs.index.get_indexer(list(feeFlow.index),method='bfill')
        feeFlow['flag'] = agg_flag
        feeFlow.groupby("flag").aggregate(np.sum)
        feeFlow.index = bs.index
        
        liability_p_v = bondView(r,flow="本金")
        liability_p_v['合计'] = liability_p_v.sum(axis=1)
        liability_i_v = bondView(r,flow="利息")
        liability_i_v['合计'] = liability_i_v.sum(axis=1)

        bs["收入","本金"] = poolPrinflow
        bs["收入","利息"] = poolIntflow
        bs["收入","早偿"] = poolPpyflow
        bs["收入","回收"] = poolRecflow

        bs["支出","负债-本金"] = liability_p_v['合计']
        bs["支出","负债-利息"] = liability_i_v['合计']
        bs["支出","负债-费用"] = feeFlow['合计']
        
        bs["利润","合计"] = bs["收入","本金"] + bs["收入","利息"] + bs["收入","早偿"] + bs["收入","回收"]
        bs["利润","合计"] = bs["利润","合计"] - bs["支出","负债-本金"] - bs["支出","负债-利息"] - bs["支出","负债-费用"]

    except RuntimeError as e:              
        print(f"Error: 其他错误=>{e}")      
    
    return bs.round(rnd) # unify([pvCol,avCol,bvCol],["资产-资产池","资产-账户","负债"])

def PnLView(r,ds=None):
    pv = r['pool']['flow'][["利息"]]
    ev = feeView(r, flow='支付')


def consolStmtByDate(s):
    return s.groupby("日期").last()

def aggStmtByDate(s):
    return s.groupby("日期").sum()

def query(d,p):
    if len(p)==1:
        return d[p[0]]
    else:
        return query(d[p[0]],p[1:])


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
