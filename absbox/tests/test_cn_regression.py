import pandas as pd 
from absbox import API,save
from absbox.local.china import 信贷ABS,show,plot_bond,plot_bonds
import os,requests,re
import numpy as np
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', -1)
pd.options.display.float_format = '{:,}'.format

def regression_on(server_address, case_folder):
    testAPI = API(server_address)
    local_deals = [ os.path.join(case_folder,x) for x in os.listdir(case_folder) if x.endswith(".py")]
    
    case_names = []
    for f in local_deals:
        with open(f,'r') as input_file:
            fc = input_file.read()
            dname = re.search("(\S+)\s*=\s*信贷ABS",fc).groups(0)[0]
            case_names.append(dname)
            exec(fc)
    
    r_list = []
    for n in case_names:
        print("Running",n)
        r = testAPI.run(eval(n)
                 ,assumptions=[]             
                 ,read=True)
        if isinstance(r,dict):
            r_list.append((True,r))
        else:
            r_list.append((False,n))