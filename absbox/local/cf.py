import pandas as pd
import toolz as tz
from lenses import lens
import enum
from ..validation import vInt, vDate, vFloat, vBool
from ..validation import vDict, vList, vStr, vNum
from .util import unifyTs,getNumCols


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


# a slice performance gain on this function
def buildDaySeq(_df):
    """  https://stackoverflow.com/questions/23435270/add-a-sequential-counter-column-on-groups-to-a-pandas-dataframe """
    df = _df.reset_index()
    dfGrp = df['date'].ne(df['date'].shift()).cumsum()
    df['daySeq'] = df['date'].groupby(dfGrp).cumcount()
    return df.set_index(["date", "daySeq"])


def buildDaySeq2(_df):
    """  https://stackoverflow.com/questions/23435270/add-a-sequential-counter-column-on-groups-to-a-pandas-dataframe """
    df = _df.reset_index()
    df['daySeq'] = df.groupby(["date"]).cumcount()
    return df.set_index(["date", "daySeq"])


def filterCols(xs, columnsToKeep):
    return [_[columnsToKeep] for _ in xs]


class BondCfHeader(enum.Enum):
    SIMPLE = ['rate','cash','intDue','intOverInt','factor','memo']+["利率","本息合计","应付利息","罚息","本金系数","备注"]
    STANDARD = ['intOverInt','factor','memo']+["罚息","本金系数","备注"]
    FULL = []


def readBondsCf(bMap, popColumns=["factor","memo","本金系数","备注","应付利息","罚息","intDue","intOverInt"]) -> pd.DataFrame:
    def isBondGroup(k, v) -> bool:
        if isinstance(k,str) and isinstance(v,dict):
            return True
        else:
            return False
    def hasBondGroup():
        _r = [ isBondGroup(k, v) for k, v in bMap.items()]
        return any(_r)

    def filterCols(x:dict, columnsToKeep) -> pd.DataFrame:
        return lens.Recur(pd.DataFrame).modify(lambda z: z[columnsToKeep])(x)

    bondNames = list(bMap.keys())
    if not bondNames:
        return pd.DataFrame()

    # colums of bond from resp
    bondColumns = (bMap & lens.Recur(pd.DataFrame).get()).columns.to_list()

    # columns to show for each bond
    columns = list(filter(lambda x: x not in set(popColumns), bondColumns))
    if not hasBondGroup():
        header = pd.MultiIndex.from_product([bondNames,columns])
        yyz = list(filterCols(bMap, columns).values())
        df = pd.concat(yyz,axis=1)
    else:
        bMap = filterCols(bMap, columns)
        indexes = []
        cfFrame = []
        for k,v in bMap.items():
            if isBondGroup(k,v):
                for _k,_v in v.items(): # sub bonds
                    indexes.extend([(k,_k,_) for _ in columns])
                    cfFrame.append(_v)
            else:
                if bMap[k] is not None:
                    indexes.extend([(k,"-",_) for _ in columns])
                    cfFrame.append(v)
                    
        header = pd.MultiIndex.from_tuples(indexes)       
        
        df = pd.concat(cfFrame,axis=1)
    df.columns = header
    return df.sort_index()


def patchMissingIndex(df,idx:set)-> pd.DataFrame:
    curIdx = set(df.index.values.tolist())
    missingIdx = idx - curIdx
    return df.reindex(df.index.values.tolist()+list(missingIdx)).sort_index()

def buildJointCf(m:dict, popColumns=[]) -> pd.DataFrame:
    if len(m)==0:
        return pd.DataFrame()
    fullColumns = list(m.values())[0].columns.to_list()
    columns = list(filter(lambda x: x not in set(popColumns), fullColumns))
    accNames = list(m.keys())
    accVals = [buildDaySeq(av) for av in list(m.values())]

    accIndex = set(tz.concat([ a.index.values.tolist() for a in accVals]))

    accVals2 = [patchMissingIndex(av,accIndex) for av in accVals]
    
    r = pd.concat(accVals2, axis=1, keys=tuple(accNames))
    if popColumns:
        return r.xs(slice(*columns), level=1, axis=1, drop_level=False)
    return r


def readAccsCf(aMap, popColumns=["memo"]) -> pd.DataFrame:
    return buildJointCf(aMap, popColumns=popColumns)


def readFeesCf(fMap, popColumns=["due","剩余支付"]) -> pd.DataFrame:
    return buildJointCf(fMap, popColumns=popColumns)


def readLedgers(lMap, **k) -> pd.DataFrame:
    return buildJointCf(lMap, **k)


def readPoolsCf(pMap) -> pd.DataFrame:
    ''' read a map of pools in dataframes to a single dataframe, with key as 1st level index'''

    if isinstance(pMap, pd.DataFrame):
        return pMap

    pNames = pMap & lens.Keys().collect()
    pFlows = pMap & lens.Values().collect()
    pColumns = pMap & lens.Values().F(lambda x:x.columns.to_list()).collect()
    headers = tz.concat([  [ (k,c) for c in cs]  for k,cs in zip(pNames,pColumns)])
    headerIndex = pd.MultiIndex.from_tuples(headers)
    df = pd.concat(pFlows,axis=1)
    df.columns = headerIndex
    return df

def readTriggers(tMap) -> pd.DataFrame:
    ''' read a map of triggers in dataframes to a single dataframe, with key as 1st level index'''
    if tMap == {} or tMap is None:
        return pd.DataFrame()
    t = tz.pipe({k:v for k,v in tMap.items() if v}
                ,lambda x: tz.valmap(buildJointCf, x)
                ,lambda x: tz.valfilter( lambda y: not y.empty ,x))
    tKeys = t.keys()
    tVals = t.values()
    return pd.concat(list(tVals), axis=1, keys=tuple(tKeys))


def readInspect(r:dict) -> pd.DataFrame:
    """ read inspect result from waterfall and run assumption input , return a joined dataframe ordered by date"""
    if 'inspect' in r:
        i = r['inspect']
        u = unifyTs(i.values())
    else:
        u = pd.DataFrame()

    if not 'waterfallInspect' in r:
        return pd.concat([u],axis=1).sort_index()
    
    if r['waterfallInspect'] is None:
        return pd.concat([u],axis=1).sort_index()
    
    if r['waterfallInspect'].empty:
        return pd.concat([u],axis=1).sort_index()

    w = r['waterfallInspect'].to_records()
    wdf = tz.pipe(tz.groupby(lambda x:tz.nth(2,x), w)
            ,lambda m: tz.valmap(lambda xs: [ (_[1],_[4]) for _ in xs],m)
            ,lambda m: tz.valmap(lambda xs: pd.DataFrame(xs, columns =['Date', 'val']).set_index('Date'),m)
            ,lambda m: {k:v.rename({"val":k},axis=1) for k,v in m.items() }
            )
    return pd.concat([u,*wdf.values()],axis=1).sort_index()


def readFlowsByScenarios(rs:dict, path, fullName=True) -> pd.DataFrame:
    "read time-series balance flow from multi scenario or mult-structs"
    flows = tz.valmap(lambda x: x & path.get(), rs)
    if fullName:
        flows = tz.itemmap(lambda kv: (kv[0],kv[1].rename(f"{kv[0]}:{kv[1].name}"))   ,flows)
    return pd.concat(flows.values(),axis=1)


def readMultiFlowsByScenarios(rs:dict, _path, fullName=True) -> pd.DataFrame:
    "read multi time-series from multi scenario or mult-structs"
    (path,cols) = _path
    vCols = vList(cols, vStr)
    _flows = tz.valmap(lambda x: x & path.get(), rs)
    flows = tz.valmap(lambda df: df[vCols],_flows)
    scenarioNames = list(flows.keys())
    header = pd.MultiIndex.from_product([ scenarioNames ,vCols], names =['Scenario',"Field"])

    df = pd.concat(list(flows.values()), axis=1)
    df.columns = header
    return df


def readFieldsByScenarios(rs:dict, path, extractor, flip=False) -> pd.DataFrame:
    """  
        read fields from multi scenario or mult-structs
        make sure the `path` points to a single value
    """

    # transfrom result map to values of paths
    tbls = tz.valmap(lambda x: x & path.get(), rs)
    if flip:
        r = tz.valmap(lambda x: x.T.loc.__getitem__(extractor), tbls)
    else:
        r = tz.valmap(lambda x: x.loc.__getitem__(extractor), tbls)
    return pd.DataFrame.from_dict(r)
