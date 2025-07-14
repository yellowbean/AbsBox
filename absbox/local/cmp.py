import pandas as pd
from lenses import lens


def compDf(x:pd.DataFrame, y:pd.DataFrame, names) -> pd.DataFrame:
    """ Compare two dataframe ,return the dataframe with difference """ 

    (nameA,nameB) = names
    x, y = x.align(y, fill_value=pd.NA)
    cmp = x.compare(y, result_names=(nameA,nameB))
    result = cmp.copy()
    for column in cmp.columns.levels[0]:
        if pd.api.types.is_numeric_dtype(cmp[column][nameA]) and pd.api.types.is_numeric_dtype(cmp[column][nameB]):
            result[column, 'diff'] = cmp[column][nameA].fillna(0) - cmp[column][nameB].fillna(0)
    return result.reindex(axis=1, level=1, labels=[nameA, nameB, 'diff']).sort_index(axis=1,level=0)


def compResult(r1:dict, r2:dict, names=("Left", "Right")):
    """ compare first to second result

    :param r1:single run result 1 (with read=True)
    :type r1: dict
    :param r2: single run result 2 (to be compared with r1)
    :type r2: dict
    :param names: name of the results, defaults to ("Left", "Right")
    :type names: tuple, optional
    """
    def cmpMap(x:dict, y:dict) -> dict:
        """ compare two map with the same keys """
        assert set(x.keys())==set(y.keys()), f"keys not match {x.keys()} vs {y.keys()}"
        cmp = {}
        for k,v in x.items():
            assert isinstance(v, pd.DataFrame), f"expecting DataFrame, got {type(v)}"
            assert isinstance(y[k], pd.DataFrame), f"expecting DataFrame, got {type(y[k])}"
            if not v.equals(y[k]):
                cmp[k] = compDf(v, y[k], names)
            else:
                cmp[k] = pd.DataFrame()
        return cmp

    # r1 -> Left
    # r2 -> Right
    comp_result = {}
    # pool check
    comp_result['pools'] = cmpMap(r1['pool']['flow'], r2['pool']['flow'])

    # expense check  
    comp_result['fees'] = cmpMap(r1['fees'], r2['fees'])

    # bond check
    if all([ isinstance(_, pd.DataFrame) for _ in r1['bonds'].values()]) and all([ isinstance(_, pd.DataFrame) for _ in r2['bonds'].values()]):
        comp_result['bonds'] = cmpMap(r1['bonds'], r2['bonds'])
    else:
        comp_result['bonds'] = {}
        for k,v in r1['bonds'].items():
            if isinstance(v, pd.DataFrame):
                comp_result['bonds'][k] = compDf(v, r2['bonds'][k])
            elif isinstance(v, dict):
                assert isinstance(r2['bonds'][k], dict), f"expecting dict, got {type(r2['bonds'][k])}"
                comp_result['bonds'][k] = cmpMap(v, r2['bonds'][k])

    # account check
    comp_result['accounts'] = cmpMap(r1['accounts'], r2['accounts'])

    # ledger check 
    comp_result['ledgers'] = cmpMap(r1['ledgers'], r2['ledgers']) if 'ledgers' in r1 else {}
    
    if 'triggers' in r1 and r1['triggers'] is not None:
        comp_result['triggers'] = {}
        for locName, tMap in r1['triggers'].items() :
            if len(tMap) == 0:
                continue
            comp_result['triggers'][locName] = cmpMap(r1['triggers'][locName], r2['triggers'][locName])

    return comp_result


def compTwoEngine(xEngine, yEngine, d, pAssump, rAssump):
    rx = xEngine.run(d, read=True, poolAssump=pAssump, runAssump=rAssump)
    ry = xEngine.run(d, read=True, poolAssump=pAssump, runAssump=rAssump)
    return compResult(rx, ry)


