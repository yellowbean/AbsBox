import pandas as pd
import os,pickle,sys
from absbox import API
from absbox.local.china import show
import csv,logging

def bench_against(api, deal_p, assump_p, bench_cf_p):
    bench_cf = pd.read_pickle(bench_cf_p)
    with open(deal_p,'rb') as _d:
        deal_obj = pickle.load(_d)
    with open(assump_p,'rb') as _d:
        assump_obj = pickle.load(_d)
    
    test_cf = show(api.run(deal_obj ,assumptions=assump_obj,read=True))
    cmp_df = bench_cf.compare(test_cf)
    if len(cmp_df.dropna()) == 0:
        return (True, None, None, None)
    else:
        return (False,deal_p,assump_p,bench_cf_p)


def regression_on(server_address, input_cases):
    testAPI = API(server_address)
    report = []
    case_folder = os.path.dirname(input_cases)
    with open(input_cases) as _input_cases:
        reader = csv.DictReader(_input_cases)
        for r in reader:
            d,a,f = [ os.path.join(case_folder,_) for _ in (r['deal'],r['assumption'],r['show_cf']) ]
            _r = bench_against(testAPI,d,a,f)
            if _r[0]==False:
                report.append(_r)
    return report

def test_regression():
    cn_regression = regression_on("https://deal-bench.xyz/api", os.path.join("absbox","tests","benchmark","china","regression.csv"))
    #cn_regression = regression_on("http://localhost:8081", os.path.join("tests","benchmark","china","regression.csv"))
    print(cn_regression)
    assert cn_regression == []