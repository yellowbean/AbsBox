import pandas as pd 



def run_yield_table(api, d, bondName, p_assumps:dict, b_assumps:dict):
    assert isinstance(p_assumps,dict),f"pool assumption should be a map but got {type(p_assumps)}"
    
    rs = api.run(d, poolAssump = p_assumps
                  , runAssump  = [('pricing',b_assumps)]
                  , read=True)

    b_pricing = {k:v['pricing'].loc[bondName] for k,v in rs.items() }
    b_table = pd.concat(b_pricing.values(), axis=1)
    b_table.columns = list(b_pricing.keys())

    return b_table
