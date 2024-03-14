import pandas as pd
import toolz as tz
from lenses import lens
from functools import reduce
#from itertools import reduce


def readToCf(xs, header=None, idx=None, sort_index=False):
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

def readBondsCf(bMap, keep=[]):
    def filterCols(xs):
        return [ _[keep]  for _ in xs ]
    
    bondNames = list(bMap.keys())
    columns = filter(lambda x: x in set(keep)
                     , bMap[bondNames[0]].columns.to_list())
    header = pd.MultiIndex.from_product([bondNames, columns]
                                        , names=['Bond',"Field"])
    
    df = pd.concat(filterCols(list(bMap.values())),axis=1)
    df.columns = header
    
    return df