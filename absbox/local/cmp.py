import pandas as pd

def compResult(r1:dict, r2:dict, names=("Left", "Right")):
    """ compare first to second result

    :param r1:single run result 1 (with read=True)
    :type r1: dict
    :param r2: single run result 2 (to be compared with r1)
    :type r2: dict
    :param names: name of the results, defaults to ("Left", "Right")
    :type names: tuple, optional
    """

    def compDf(x, y):
        (nameA,nameB) = names
        x, y = x.align(y, fill_value=pd.NA)
        cmp = x.compare(y, result_names=(nameA,nameB))
        result = cmp.copy()
        for column in cmp.columns.levels[0]:
            if pd.api.types.is_numeric_dtype(cmp[column][nameA]) and pd.api.types.is_numeric_dtype(cmp[column][nameB]):
                result[column, 'diff'] = cmp[column][nameA].fillna(0) - cmp[column][nameB].fillna(0)
        return result.reindex(axis=1, level=1, labels=[nameA, nameB, 'diff']).sort_index(axis=1,level=0)

    # r1 -> Left
    # r2 -> Right
    comp_result = {}
    # pool check
    comp_result['pool'] = {}
    for k,v in r1['pool']['flow'].items():
        if not v.equals(r2['pool']['flow'][k]):
            comp_result['pool'][k] = compDf(v, r2['pool']['flow'][k])
        else:
            comp_result['pool'] = True

    # expense check  
    comp_result['fees'] = {}
    for fn, f in r1['fees'].items():
        if not f.equals(r2['fees'][fn]):
            comp_result['fees'][fn] = compDf(f, r2['fees'][fn])
        else:
            comp_result['fees'][fn] = True

    # bond check
    comp_result['bonds'] = {}
    for fn, f in r1['bonds'].items():
        if not f.equals(r2['bonds'][fn]):
            comp_result['bonds'][fn] = compDf(f, r2['bonds'][fn])
        else:
            comp_result['bonds'][fn] = True

    # account check
    comp_result['accounts'] = {}
    for fn, f in r1['accounts'].items():
        if not f.equals(r2['accounts'][fn]):
            comp_result['accounts'][fn] = compDf(f, r2['accounts'][fn])
        else:
            comp_result['accounts'][fn] = True

    # ledger check 
    comp_result['ledgers'] = {}
    if 'ledgers' in r1:
        for fn, f in r1['ledgers'].items():
            if not f.equals(r2['ledgers'][fn]):
                comp_result['ledgers'][fn] = compDf(f, r2['ledgers'][fn])
            else:
                comp_result['ledgers'][fn] = True
    
    comp_result['triggers'] = {}
    if 'triggers' in r1:
        for locName, tMap in r1['triggers'].items() :
            if len(tMap) == 0:
                continue
            comp_result['triggers'][locName] = {}
            for tn, t in tMap.items():
                if not t.equals(r2['triggers'][locName][tn]):
                    comp_result['trigger'][locName][tn] = compDf(t, r2['triggers'][locName][tn])
                else:
                    comp_result['trigger'][locName][tn] = True
    
    return comp_result
