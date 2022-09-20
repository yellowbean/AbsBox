import pandas as pd 
import functools

def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}
            
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