import pandas as pd


def comp_df(x, y):
    return pd.merge(x, y, on="日期", how='outer').sort_index().sort_index(axis=1)

def comp_engines(engine1,engine2, d, a=None):
    
    r1 = engine1.run(d,assumptions=a,read=True)
    r2 = engine2.run(d,assumptions=a,read=True)

    comp_result = {}
    # pool check
    if not r1['pool']['flow'].equals(r2['pool']['flow']):
        comp_result['pool'] = comp_df(r1['pool']['flow'],r2['pool']['flow'])
    else:
        comp_result['pool'] = True

    # expense check  
    comp_result['fee'] = {}
    for fn,f in r1['fees'].items():
        if not f.equals(r2['fees'][fn]):
            comp_result['fee'][fn] = comp_df(f,r2['fees'][fn])
        else:
            comp_result['fee'][fn] = True

    # bond check
    comp_result['bond'] = {}
    for fn,f in r1['bonds'].items():
        if not f.equals(r2['bonds'][fn]):
            comp_result['bond'][fn] = comp_df(f,r2['bonds'][fn])
        else:
            comp_result['bond'][fn] = True


    # account check
    comp_result['account'] = {}
    for fn,f in r1['accounts'].items():
        if not f.equals(r2['accounts'][fn]):
            comp_result['account'][fn] = comp_df(f,r2['accounts'][fn])
        else:
            comp_result['account'][fn] = True

    return comp_result
