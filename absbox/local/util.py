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
