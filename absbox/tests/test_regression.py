import os,pickle,sys,json,csv,logging
from json.decoder import JSONDecodeError
import importlib
import pprint as pp

from absbox import API
from absbox.local.china import show,信贷ABS
from absbox.local.util import mkTag
import requests
import pandas as pd
import rich

from jsondiff import diff
from deepdiff import DeepDiff

import absbox.tests.benchmark.us as us
import absbox.tests.benchmark.china as cn


this_file = os.path.dirname(__file__)
china_folder = os.path.join("absbox","tests","benchmark","china")
us_folder = os.path.join("absbox","tests","benchmark","us")
test_folder = os.path.join("absbox","tests")
config_file = os.path.join(test_folder,"config.json")

with open(config_file,'r') as cfh:
    config = json.load(cfh)
    

def read_test_cases():
    r = {}
    with open(os.path.join(test_folder,"test_case.txt") ,'r') as f:
        rs = f.readlines()
        file_paths = [r.rstrip() for r in rs if not r.startswith("#") ]
        for file_path in file_paths:
            country,test_num,deal_var_name = file_path.split(",")

            deal_path = os.path.join(test_folder,"benchmark",country,test_num)
            spec = importlib.util.spec_from_file_location("runner", deal_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            deal = getattr(module,deal_var_name)
            r[file_path] = deal
    return r


def translate(d,folder,o):
    print(f"Translating>>{d}>>{o}")
    benchfile =  os.path.join(this_file,"benchmark",folder,"out",o)
    if not os.path.exists(benchfile) or os.stat(benchfile).st_size < 10 :
        print(f"Skipping:{benchfile}")
        with open(benchfile,'w',encoding='utf8') as newbench:
            try:
                print(f"Writing new bench out case -> size {len(d.json)}")
            except Exception as e:
                print(f"Error in build deal json:{e}")
            assert d.json is not None, f"None: Failed to generate Deal JSON file:{d.json}"
            assert d.json != "", f"Empty: Failed to generate Deal JSON file:{d.json}"
            json.dump(d.json,newbench,indent=2)
        logging.info(f"Create new case for {o}")
    else:
        with open(benchfile ,'r') as ofile:
            try:
                benchmark_out = json.load(ofile)
                if d.json != benchmark_out:
                    print(f"Failed with benchmark file:{benchfile} ")
                    diff_result = DeepDiff(d.json,benchmark_out)
                    pp.pprint(diff_result,indent=2)
                    assert d.json == benchmark_out, f"testing fail on {o}"
                else:
                    return True
            except JSONDecodeError as e:
                print(f"Error parsing json format:{benchfile}")


def test_translate():
    cases = read_test_cases()

    for case,v in cases.items():
        output_folder,test_py,deal_obj = case.split(",")
        translate(v, output_folder, test_py.replace(".py",".json"))

   # case_out = os.path.join(china_folder, "out")
   # pair = cn.translate_pair
   # translate(pair, case_out)
   # case_out = os.path.join(us_folder, "out")
   # pair = us.translate_pair
   # translate(pair, case_out)

def run_deal(input_folder, pair):
    input_req_folder = os.path.join(input_folder,"out")
    input_scen_folder = os.path.join(input_folder,"scenario")
    input_resp_folder = os.path.join(input_folder,"resp")
    print("Select server to run")
    test_server = config["test_server"] #https://deal-bench.xyz/api/run_deal2" 
    if 'TEST_RUN_SERVER' in os.environ and os.environ['TEST_RUN_SERVER'] != "" :
        print("Using Custom Server")
        logging.info(f"Using Env Server {os.environ['TEST_RUN_SERVER']}")
        test_server = os.environ['TEST_RUN_SERVER']
    else:
        print(f"Using Config Server => {test_server}")
        logging.info(f"Using Server from Config {test_server}")
    #test_server = "https://absbox.org/api/dev" # config["test_server"] #https://deal-bench.xyz/api/run_deal2" 
    
    for dinput, sinput, nonPinput, eoutput in pair:
        print(f"Comparing:{dinput},{sinput},{eoutput}")
        with open(os.path.join(input_req_folder,dinput), 'r') as dq:  # deal request
            with open(os.path.join(input_scen_folder,sinput), 'r') as sq: # scenario request 
                print(f"With deal request=> {dinput}, scenario => {sinput}")
                nonPerfInput = None
                if nonPinput:
                    nonPerfInput = json.load(open(os.path.join(input_scen_folder,nonPinput)))
                    print(nonPerfInput)
                else:
                    nonPerfInput = {}
                req = mkTag(("SingleRunReq", [json.load(dq) 
                                              , json.load(sq)
                                              , nonPerfInput])) 
                print("build req done")
                hdrs = {'Content-type': 'application/json', 'Accept': '*/*'}
                try:
                    tresp = requests.post(f"{test_server}/runDeal"
                                          , data=json.dumps(req, ensure_ascii=False).encode('utf-8')
                                          , headers=hdrs
                                          , verify=False)
                    if tresp.status_code != 200:
                        print(f"Failed to finish req:{dinput}")
                        print(f"response=>{tresp.status_code}")
                        print(f"response text {tresp.text}")
                        
                    else:
                        print(f"responds received")
                except requests.exceptions.ConnectionError as e:
                    print(f"Failed to get resp from {dinput}")
                try:
                    s_result = json.loads(tresp.text)
                except JSONDecodeError as e:
                    logging.error(f"Error parsing {tresp.text}")
                    #break
                local_bench_file = os.path.join(input_resp_folder,eoutput)
                if not os.path.exists(local_bench_file):
                    print(f"writing to new resp for {local_bench_file}")
                    with open(local_bench_file,'w') as wof: # write output file
                        json.dump(s_result,wof,indent=2)
                    continue
                with open(local_bench_file,'r') as eout: # expected output 
                    print(f"reading resp for {local_bench_file}")
                    local_result = json.load(eout)
                    assert isinstance(local_result, list), f"{dinput}: local result is not list but {local_result.keys()},{local_result['error']}"
                    assert isinstance(s_result, list), f"{dinput}: server result is not list but {s_result}"
                    assert local_result[1]==s_result[1],f"Pool Flow Is not matching => {dinput},deal name => {local_result['contents']['name']}"
                    local_result_content = local_result[0]['contents']
                    s_result_content = s_result[0]['contents']
                    if not local_result_content['waterfall']==s_result_content['waterfall']:
                        local_keys = local_result_content['waterfall'].keys()
                        server_keys = s_result_content['waterfall'].keys()
                        assert local_keys == server_keys,f"Keys are not matched, local keys:{local_keys},server keys:{server_keys}"
                        commonKeys = local_result_content['waterfall'].keys()
                        # for (idx,(local_w,test_w)) in enumerate(zip(local_result_content['waterfall'],s_result_content['waterfall'])):
                        for (idx,actionName) in commonKeys:
                            assert local_result_content['waterfall'][actionName] == s_result_content['waterfall'][actionName], f"diff in waterfall action {actionName},local={local_result_content['waterfall'][actionName]},test={s_result_content['waterfall'][actionName]}"

                        #assert False,f"diff in waterfall: {diff(local_result_content['waterfall'],s_result_content['waterfall'])}"
                    if local_result_content['bonds']!=s_result_content['bonds']:
                        print("Bonds are not matching")
                        for bn,bv in local_result_content['bonds'].items():
                            assert 'bonds' in s_result[0]['contents'],f"No bonds in server resp, with key -> {s_result[0]['contents'].keys()}"
                            if s_result[0]['contents']['bonds'][bn]!=bv:
                                print(f"Bond {bn} is not matching")
                                print(DeepDiff(s_result_content['bonds'][bn], bv))

                    #for i in ['status','dates','pool','fees','bonds','accounts']:
                    #    assert local_result[0][i]==s_result[0][i], f"Deal {i} is not matching"
                    bench_keys = local_result_content.keys()
                    result_keys = s_result_content.keys()
                    assert set(bench_keys) == set(result_keys),f"keys are not matching: bench {bench_keys},result {result_keys}"
                    for i in ['status','dates','pool','fees','bonds','accounts']:
                        assert local_result_content[i]==s_result_content[i], f"Deal {i} is not matching"
                    assert s_result == local_result , f"Server Test Failed {dinput} {sinput} {eoutput} "
                    print("Compare Done")


def test_resp():
    pair = [("test01.json","mortgage_empty.json",None,"test01.out.json")
            ,("test02.json","mortgage_empty.json",None,"test02.out.json")
            ,("test03.json","mortgage_empty.json","rates.json","test03.out.json")
            ,("test04.json","mortgage_empty.json","rates.json","test04.out.json")
            ,("test05.json","mortgage_empty.json","rates.json","test05.out.json")
            ,("test06.json","mortgage_empty.json","rates.json","test06.out.json")
            ,("test07.json","mortgage_empty.json",None,"test07.out.json")
            ,("test08.json","mortgage_empty.json",None,"test08.out.json")
            ,("test09.json","mortgage_empty.json",None,"test09.out.json")
            ,("test10.json","mortgage_empty.json",None,"test10.out.json")
            ,("test11.json","mortgage_empty.json","rates.json","test11.out.json")
            ,("test12.json","mortgage_empty.json","rates.json","test12.out.json")
            ,("test13.json","mortgage_empty.json",None,"test13.out.json")
            ,("test14.json","mortgage_empty.json","rates.json","test14.out.json")
            ,("test15.json","mortgage_empty.json",None,"test15.out.json")
            ,("test16.json","mortgage_empty.json",None,"test16.out.json")
            ,("test17.json","mortgage_empty.json",None,"test17.out.json")
            ,("test18.json","mortgage_empty.json",None,"test18.out.json")
            ,("test19.json","mortgage_empty.json",None,"test19.out.json")
            ,("test20.json","loan_empty.json",None,"test20.out.json")
            ,("test21.json","mortgage_empty.json",None,"test21.out.json")
            #,("test23.json","empty.json","test23.out.json")
            ,("test24.json","mortgage_empty.json","bmwRevolving.json","test24.out.json")
            ,("test25.json","mortgage_empty.json",None,"test25.out.json")
            ]
    print(">>>> Runing China Bench Files")
    run_deal(china_folder, pair)
    
    print(">>>> Runing US Bench Files")
    pair = [("test01.json","empty.json",None,"test01.out.json")
            ,("test02.json","empty.json",None,"test02.out.json")
            ,("test03.json","empty.json",None,"test03.out.json")
            ,("test04.json","empty.json",None,"test04.out.json")
            ,("test05.json","empty.json",None,"test05.out.json")
            ,("test06.json","empty.json",None,"test06.out.json")
            ,("test07.json","empty.json","bmwRevolving.json","test07.out.json")
            ]
    run_deal(us_folder, pair)


