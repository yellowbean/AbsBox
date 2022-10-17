import pandas as pd 
import functools
from enum import Enum

def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}

#"{\"tag\":\"PrepaymentFactors\"
#  ,\"contents\":{\"tag\":\"FactorCurveClosed\"
#                ,\"contents\":[[\"2022-01-01\",{\"numerator\":33,\"denominator\":25}]]}}"

def mkTs(n,vs):
    return mkTag((n,vs))
    
def unify(xs,ns):
    index_name = xs[0].index.name
    dfs = []
    for x,n in zip(xs,ns):
        dfs.append(pd.concat([x],keys=[n],axis=1))
    r = functools.reduce(lambda acc,x: acc.merge(x
                                                ,how='outer'
                                                ,on=[index_name])
                        ,dfs)
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

def peekAtDates(x,ds):
    x_consol = x.groupby(["日期"]).last()

    if x_consol.index.get_indexer(ds,method='pad').min()==-1:
        raise RuntimeError("<查看日期>早于当前DataFrame")

    keep_idx = [ x_consol.index.asof(d) for d in ds ]
    y = x_consol.loc[keep_idx]
    y.reset_index("日期")
    y["日期"] = ds
    return y.set_index("日期")

def balanceSheetView(r,ds=None):
    bv = bondView(r, flow="余额")
    av = accView(r, flow="余额")
    pv = r['pool']['flow'][["未偿余额"]]
    
    #validation
    #bv.index

    try:
        pvCol,avCol,bvCol = [ peekAtDates(_, ds)  for _ in [pv,av,bv] ]

        for k,_ in [("资产池",pvCol),("账户",avCol), ("债券",bvCol)]:
            _[f'{k}-合计'] = _.sum(axis=1)

        asset_cols = (len(pvCol.columns)+len(avCol.columns))*["资产"]
        liability_cols = len(bvCol.columns)*["负债"]
        header = asset_cols + liability_cols

        bs = pd.concat([pvCol,avCol,bvCol],axis=1)
        bs.columns = pd.MultiIndex.from_arrays([header,list(bs.columns)])
        bs["资产","合计"] = bs["资产","资产池-合计"]+bs["资产","账户-合计"]
        bs["负债","合计"] = bs["负债","债券-合计"]


    except RuntimeError as e:
        print(f"Error: 其他错误=>{e}")
    
    return bs # unify([pvCol,avCol,bvCol],["资产-资产池","资产-账户","负债"])


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
