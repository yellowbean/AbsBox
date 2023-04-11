import pandas as pd 



def run_yield_table(api, d, bondName, p_assumps:dict, b_assumps:dict):
    
    rs = api.run(d ,assumptions=p_assumps
                   ,pricing = b_assumps
                   ,read=True)

    b_pricing = {k:v['pricing'].loc[bondName] for k,v in rs.items() }
    b_table = pd.concat(b_pricing.values(),axis=1)
    b_table.columns = list(b_pricing.keys())

    return b_table
