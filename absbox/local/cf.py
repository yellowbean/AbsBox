import pandas as pd
import toolz as tz
from lenses import lens
from functools import reduce
#from itertools import reduce


def readToCf(xs, header=None, idx=None, sort_index=False) -> pd.DataFrame:
    ''' input with flow type json, return a dataframe '''
    rows = [_['contents'] for _ in xs]

    if header:
        r = pd.DataFrame(rows, columns=header)
    else:
        r = pd.DataFrame(rows)

    if idx:
        r = r.set_index(idx)

    if sort_index:
        r = r.sort_index()

    return r

def readBondsCf(bMap, popColumns=["factor","memo","本金系数","备注"]) -> pd.DataFrame:
    def filterCols(xs, columnsToKeep):
        return [ _[columnsToKeep] for _ in xs ]
   
    bondNames = list(bMap.keys())
    bondColumns = bMap[bondNames[0]].columns.to_list()
    columns = list(filter(lambda x: x not in set(popColumns), bondColumns))
    header = pd.MultiIndex.from_product([bondNames,columns]
                                        , names=['Bond',"Field"])
    df = pd.concat(filterCols(bMap.values(), columns),axis=1)
    df.columns = header
    return df

def readFeesCf(fMap, popColumns=["due","剩余支付"]) -> pd.DataFrame:
    def filterCols(xs, columnsToKeep):
        return [ _[columnsToKeep]  for _ in xs ]
    
    feeNames = list(fMap.keys())
    feeColumns = list(fMap.values())[0].columns.to_list()
    columns = list(filter(lambda x: x not in set(popColumns), feeColumns))
    header = pd.MultiIndex.from_product([feeNames, columns]
                                        , names=['Fee',"Field"])
    
    df = pd.concat(filterCols(list(fMap.values()),columns),axis=1)
    df.columns = header
    return df

def readAccsCf(aMap, popColumns=["memo"]) -> pd.DataFrame:
    def filterCols(xs, columnsToKeep):
        return [ _[columnsToKeep]  for _ in xs ]
    
    accNames = list(aMap.keys())
    accColumns = list(aMap.values())[0].columns.to_list()
    columns = list(filter(lambda x: x not in set(popColumns) , accColumns))
    header = pd.MultiIndex.from_product([accNames, columns]
                                        , names=['Account',"Field"])

    df = pd.concat(filterCols(list(aMap.values()),columns),axis=1)
    df.columns = header
    return df