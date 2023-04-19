from pywebio.input import *
from pywebio.output import *

from pywebio import start_server
from deepdiff import DeepDiff

#from benchmark.us import *
#from benchmark.china import *

def read_test_cases():
    with open("test_caes.txt") as f:
        rs = f.readlines()
        return [r.split(",") for r in rs ]

servers = {
    "LOCAL":"http://localhost:8081",
    "DEV":"https://absbox.org/api/dev",
    "LATEST":"https://absbox.org/api/latest",
}

def compareDealFile(d, bench_outfile):
    with open(bench_outfile,'r') as ofile:
        benchmark_out = json.load(ofile)
        r = None
        if d.json == bench_outfile:
            r = {"result":"pass", "detail":""}
        else:
            r = {"result":"failed", "detail":DeepDiff(d.json,benchmark_out)}
        return r | {"deal": benchmark_out}


def compareCf():
    return {}

def app():
    benchmark = {}
    benchmark_deal_jsons = []                    
    benchmark_deal_resp = [] 

    run_server = radio("Run Server", options=["LOCAL","DEV","LATEST"])
    run_type = radio("Run Type",options=["Translate","Cashflow","Translate+Cashflow"])
    test_cases = checkbox("Run Case", options= read_test_cases())

    put_table([
        {"Course":"OS", "Score": "80"},
        {"Course":"DB", "Score": "93"},
    ], header=["Course", "Score"])

    



if __name__ == '__main__':
    start_server(app, port=36535, debug=True)