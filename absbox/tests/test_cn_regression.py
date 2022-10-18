import pandas as pd
import os,pickle,sys
from absbox import API
from absbox.local.china import show,信贷ABS
import requests
import json
import jsondiff as jd
from jsondiff import diff
import logging

from absbox.tests.benchmark.china import *

import csv,logging


china_folder = os.path.join("absbox","tests","benchmark","china")

def test_translate():
    case_out = os.path.join(china_folder,"out")
    pair = [(t1.test01,"test01.json")
            ,(t2.test02,"test02.json")
            ,(t3.test03,"test03.json")
            ,(t4.JY_RMBS_01,"test04.json")
            ,(t5.gy,"test05.json")
            ,(t6.JY_RMBS_2017_5,"test06.json")
            ,(t7.BYD_AUTO_2021_2,"test07.json")
            ,(t8.JSD_AUTO_2022_3,"test08.json")
            ,(t9.test09,"test09.json")
            ,(t10.test01,"test10.json")
            ,(t11.test01,"test11.json")
            ,(t12.JY_RMBS_2019_11,"test12.json")
            ,(t13.test01,"test13.json")
            ]
    result = []
    for d,o in pair:
        benchfile =  os.path.join(case_out,o)
        if not os.path.exists(benchfile):
            print(f"Skipping:{benchfile}")
            with open(benchfile,'w',encoding='utf8') as newbench:
                json.dump(d.json,newbench)
            logging.info(f"Create new case for {o}")
            continue
        with open(benchfile ,'r') as ofile:
            benchmark_out = json.load(ofile)
            assert d.json == benchmark_out, f"testing on {o}"


def test_resp():
    input_req_folder = os.path.join(china_folder,"out")
    input_scen_folder = os.path.join(china_folder,"scenario")
    input_resp_folder = os.path.join(china_folder,"resp")
    test_server = "https://deal-bench.xyz/api" 
    #test_server = "http://localhost:8081/run_deal2" 
    pair = [("test01.json","empty.json","test01.out.json")
            ,("test02.json","empty.json","test02.out.json")
            ,("test03.json","empty.json","test03.out.json")
            ,("test04.json","empty.json","test04.out.json")
            ,("test05.json","empty.json","test05.out.json")
            ,("test06.json","empty.json","test06.out.json")
            ,("test07.json","empty.json","test07.out.json")
            ,("test08.json","empty.json","test08.out.json")
            ,("test09.json","empty.json","test09.out.json")
            ,("test10.json","empty.json","test10.out.json")
            ,("test11.json","empty.json","test11.out.json")
            ,("test12.json","empty.json","test12.out.json")
            ,("test13.json","empty.json","test13.out.json")
            ]
    for dinput,sinput,eoutput in pair:
        print("Comparing")
        print(dinput,sinput,eoutput)
        with open(os.path.join(input_req_folder,dinput),'r') as dq:  # deal request
            with open(os.path.join(input_scen_folder,sinput),'r') as sq: # scenario request 
                req = {"deal":json.load(dq),"assump":json.load(sq),"bondPricing":None}
                hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                tresp = requests.post(test_server
                                 , data=json.dumps(req).encode('utf-8')
                                 , headers=hdrs
                                , verify=False)
                if tresp.status_code != 200:
                    print(tresp.text)

                s_result = json.loads(tresp.text)
                local_bench_file = os.path.join(input_resp_folder,eoutput)
                if not os.path.exists(local_bench_file):
                    with open(local_bench_file,'w') as wof: # write output file
                        json.dump(s_result,wof)
                    continue
                with open(local_bench_file,'r') as eout: # expected output 
                    local_result = json.load(eout)
                    #_diff = diff(s_result, local_result)
                    #print(_diff)
                    assert s_result == local_result , f"Server Test Failed {dinput} {sinput} {eoutput} "



