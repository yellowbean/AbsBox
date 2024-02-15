import pandas as pd


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