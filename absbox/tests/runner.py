import importlib 
import os,json


from pywebio.input import *
from pywebio.output import *

from pywebio import start_server
from deepdiff import DeepDiff

from absbox import Generic,SPV
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

servers = {
    "LOCAL":"http://localhost:8081",
    "DEV":"https://absbox.org/api/dev",
    "LATEST":"https://absbox.org/api/latest",
}

def compareDealFile(k, d):
    country,case_num,instance_name = k.split(",")
    benchfile_path = os.path.join("benchmark",country,"out",case_num.replace(".py",".json"))
    with open(benchfile_path,'r') as ofile:
        benchmark_out = json.load(ofile)
        r = None
        if d.json == benchmark_out:
            r = {"result":"pass", "detail":""}
        else:
            r = {"result":"failed", "detail":DeepDiff(d.json,benchmark_out)}
        return r # | {"deal": benchmark_out}

def compareCash(api, k, d):
    country,case_num,instance_name = k.split(",")
    benchfile_path = os.path.join("benchmark",country,"resp",case_num.replace(".py",".json"))
    with open(benchfile_path,'r') as ofile:
        benchmark_out = json.load(ofile)
        test_cf = api.run(d)
        r = None
        if test_cf == benchmark_out:
            r = {"result":"pass", "detail":""}
        else:
            r = {"result":"failed", "detail":DeepDiff(d.json,benchmark_out)}
        return r # | {"deal": benchmark_out}


def compareCf():
    return {}

def app():
    benchmark = {}
    benchmark_deal_jsons = []                    
    benchmark_deal_resp = [] 
    deal_loaded = read_test_cases()
    
    run_input = input_group("Run Params",[
        select("Run Server",name="run_server", options=["LOCAL","DEV","LATEST"])
        ,checkbox("Run Type",name="run_type",options=["Translate","Cashflow"])
        ,checkbox("Run Case",name="run_cases", options= deal_loaded.keys(),value=list(deal_loaded.keys()))
        ]
    )
    selected_run_type = set(run_input['run_type'])
    selected_cases = set(run_input['run_cases'])
    if 'Translate' in selected_run_type :
        compare_result = {k: compareDealFile(k, v) for k,v in deal_loaded.items() 
                            if k in selected_cases }
    if 'Cashflow' in selected_run_type :
        cash_result = {k: compareDealFile(k, v) for k,v in deal_loaded.items() 
                            if k in selected_cases }

    if selected_run_type == {"Translate","Cashflow"}:
        combine_result = [ {"TestCase":k, "cashflow": cash_result[k], "translate":compare_result[k]}  for k in selected_cases ]
    elif selected_run_type == {"Cashflow"}:
        combine_result = [ {"TestCase":k, "cashflow":cash_result[k]} for k in selected_cases ]
    elif selected_run_type == {"Translate"}:
        combine_result = [ {"TestCase":k, "translate": put_code(compare_result[k],language='json')} for k in selected_cases ]
    else:
        pass

    header = list(combine_result[0].keys())
    put_table(combine_result, header=header)

    



if __name__ == '__main__':
    start_server(app, port=36535, debug=True)