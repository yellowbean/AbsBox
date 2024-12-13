import importlib 
import os,json
from lenses import lens
import toolz as tz
from deepdiff import DeepDiff
from absbox import Generic,SPV,API
#from benchmark.us import *
#from benchmark.china import *

def read_test_cases():
    r = {}
    with open("test_case.txt") as f:
        rs = f.readlines()
        file_paths = [r.rstrip() for r in rs if not r.startswith("#") ]
        for file_path in file_paths:
            country,test_num,deal_var_name = file_path.split(",")
            deal_path = os.path.join("benchmark",country,test_num)
            spec = importlib.util.spec_from_file_location("runner", deal_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            deal = getattr(module,deal_var_name)
            r[file_path] = deal
    return r


def setupEngines(benchmarkApiUrl, testApiUrl, check=False):
    benchmarkApi,testApi = API(benchmarkApiUrl,check=check), API(testApiUrl,check=check)
    return benchmarkApi,testApi

def testByEngines(benchmarkApi, testApi, deal, scenario=(None,None)):

    poolAssump,runAssump = scenario

    rb,rt = None,None

    rb = benchmarkApi.run(deal, poolAssump, runAssump, read=True)
    rt = testApi.run(deal, poolAssump, runAssump, read=True)

    def compareResult(x,y):
        diag = {}
        if x == y:
            return diag
        if x['pool']['flow'] != y['pool']['flow']:
            diag['pool'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                         , x['pool']['flow'], y['pool']['flow'])
        if x['fees'] != y['fees']:
            diag['fees'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                         , x['fees'], y['fees'])
        if x['accounts'] != y['accounts']:
            diag['account'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                         , x['accounts'], y['accounts'])
        if x['bonds'] != y['bonds']:
            diag['bonds'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                         , x['bonds'], y['bonds'])        
        if 'triggers' in x:
            if x['triggers'] != y['triggers']:
                diag['triggers'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                         , x['triggers'], y['triggers'])  
        if 'ledgers' in x:
            if x['ledgers'] != y['ledgers']:
                diag['ledgers'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                            , x['ledgers'], y['ledgers']) 
        if 'liqProvider' in x:
            if x['liqProvider'] != y['liqProvider']:
                diag['liqProvider'] = tz.merge_with(lambda xs: xs[0].compare(xs[1],result_names=("benchmark","test"))
                                            , x['liqProvider'], y['liqProvider'])
        
        diag &= lens.Values().Values().modify(lambda x: x if not x.empty else x)

        return diag         

    return compareResult(rb,rt)

