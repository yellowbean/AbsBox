import logging, json, datetime, pickle,re
from json.decoder import JSONDecodeError
import requests
from requests.exceptions import ConnectionError
import urllib3
from dataclasses import dataclass,field
from absbox.local.util import mkTag,query,isDate,flat
from absbox.local.component import mkPool,mkAssumption,mkAssumption2
import pandas as pd
#from pyspecter import S,query

urllib3.disable_warnings()

@dataclass
class API:
    url:str
    #lang = field(repr=False, default="chinese")
    lang:str = "chinese"
    server_info = {}
    version:tuple = "0","7","0"
    hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __post_init__(self):
        try:
            _r = requests.get(f"{self.url}/version",verify=False).text
        except (ConnectionRefusedError, ConnectionError):
            logging.error(f"Error: Can't not connect to API server {self.url}")
            self.url = None
            return

        echo = json.loads(_r)
        self.server_info = echo
        x,y,z = echo['version'].split(".")
        logging.info(f"Connect Successfully with engine version {echo['version']}")
        if self.version[1] != y:
            logging.error(f"Failed to init the api instance, lib support={self.version} but server version={echo['version']} , pls upgrade your api package by: pip -U absbox")
            return

    def build_req(self, deal, assumptions=None, pricing=None, read=None) -> str:
        _assump = None 
        if isinstance(assumptions, dict):
            _assump = mkTag(("Multiple", { scenarioName:mkAssumption2(a) for (scenarioName,a) in assumptions.items()}))
        elif isinstance(assumptions, list) or  isinstance(assumptions, tuple):   
            _assump = mkTag(("Single",mkAssumption2(assumptions)))
        else:
            _assump = None
        return json.dumps({"deal": deal.json
                          ,"assump": _assump
                          ,"bondPricing": deal.read_pricing(pricing) if (pricing is not None) else None}
                          , ensure_ascii=False)

    def build_pool_req(self, pool, assumptions=[], read=None) -> str:
        return json.dumps({"pool": mkPool(pool)
                          ,"pAssump": mkAssumption2(assumptions)}
                          ,ensure_ascii=False)

    def _validate_assump(self,x,e,w):
        a = x['assump']
        asset_ids = set(range(len(query(x,['deal','contents','pool','assets']))))
        match a:
            case {'tag':'Single',
                'contents':{'tag':'ByIndex',
                            'contents':(assumps,_)}}:
                _ids = set(flat([ assump[0] for assump in assumps ]))
                if not _ids.issubset(asset_ids):
                    e.append(f"Not Valid Asset ID:{_ids - asset_ids}")
                missing_asset_id = asset_ids - _ids
                if len(missing_asset_id)>0:
                    w.append(f"Missing Asset to set assumption:{missing_asset_id}")            
            case {'tag':'Multiple',
                'contents':scenarioMap}:
                for k,v in scenarioMap.items():
                    _ids = set(flat([ _a[0] for _a in v['contents'][0]]))
                    if not _ids.issubset(asset_ids):
                        e.append(f"Scenario:{k},Not Valid Asset ID:{_ids - asset_ids}")
                    missing_asset_id = asset_ids - _ids
                    if len(missing_asset_id)>0:
                        w.append(f"Scenario:{k},Missing Asset to set assumption:{missing_asset_id}")
            case {'tag':'Single','contents':{'tag':'PoolLevel'}}:
                return [True,e,w]
            case {'tag':'Multiple','contents':{'tag':'PoolLevel'}}:
                return [True,e,w]
            case None:
                return [True,e,w]
            case _ :
                raise RuntimeError(f"Failed to match:{a}")
        if len(e)>0:
            return [False,e,w]
        return [True,e,w]

    def validate(self, _r) -> list:
        error = []
        warning = []
        _r = json.loads(_r)
        __d = _r['deal']
        _d = __d['contents']
        valid_acc = set(_d['accounts'].keys())
        valid_bnd = set(_d['bonds'].keys())
        valid_fee = set(_d['fees'].keys())
        _w = _d['waterfall']

        _,error,warning = self._validate_assump(_r,error,warning)

        if _w is None:
            raise RuntimeError("Waterfall is None")

        # validatin waterfall
        for wn,wa in _w.items():
            for idx,action in enumerate(wa):
                action = action[1]
                match action['tag']:
                    case 'PayFeeBy':
                        if (not set(action['contents'][1]).issubset(valid_acc)) \
                            or (not set(action['contents'][2]).issubset(valid_fee)):
                            error.append(f"{wn},{idx}")
                    case 'PayFee':
                        if (not set(action['contents'][0]).issubset(valid_acc)) \
                            or (not set(action['contents'][1]).issubset(valid_fee)):
                            error.append(f"{wn},{idx}")     
                    case 'PayInt':
                        if (action['contents'][0] not in valid_acc) \
                            or (not set(action['contents'][1]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")  
                    case 'PayPrin':
                        if (action['contents'][0] not in valid_acc) \
                            or (not set(action['contents'][1]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")  
                    case 'PayPrinBy':
                        if (action['contents'][1] not in valid_acc) \
                            or (not set(action['contents'][2]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")  
                    case 'PayResidual':
                        if (action['contents'][1] not in valid_acc) \
                            or (action['contents'][2] not in valid_bnd):
                            error.append(f"{wn},{idx}")  
                    case 'Transfer':
                        if (action['contents'][0] not in valid_acc) \
                            or (action['contents'][1] not in valid_acc):
                            error.append(f"{wn},{idx}")
                    case 'TransferBy':
                        if (action['contents'][1] not in valid_acc) \
                            or (action['contents'][2] not in valid_acc):
                            error.append(f"{wn},{idx}")
                    case 'PayTillYield':
                        if (action['contents'][0] not in valid_acc) \
                            or (not set(action['contents'][1]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")
                    case 'PayFeeResidual':
                        if (action['contents'][1] not in valid_acc) \
                            or (action['contents'][2] not in valid_fee):
                            error.append(f"{wn},{idx}")        

        if warning:
            logging.warning(f"Warning in modelling:{warning}")

        if len(error)>0:
            if error:
                logging.error(f"Error in modelling:{error}")
            return False,error,warning
        else:
            return True,error,warning


    def run(self,
            deal,
            assumptions=None,
            pricing=None,
            custom_endpoint=None,
            read=True,
            position=None,
            timing=False):

        if isinstance(assumptions,str):
            assumptions = pickle.load(assumptions)

        # if run req is a multi-scenario run
        if assumptions:
            multi_run_flag = isinstance(assumptions, dict)
        else:
            multi_run_flag = False 
        
        # overwrite any custom_endpoint
        url = f"{self.url}/run_deal"
        if custom_endpoint:
            url = f"{self.url}/{custom_endpoint}"

        if isinstance(deal, str):
            with open(deal,'rb') as _f:
                c = _f.read()
                deal = pickle.loads(c)

        # construst request
        req = self.build_req(deal, assumptions, pricing)

        #validate deal
        deal_validate,err,warn = self.validate(req)
        if not deal_validate:
            return deal_validate,err,warn

        result = self._send_req(req,url)

        if read:
            if multi_run_flag:
                return { n:deal.read(_r,position=position) for (n,_r) in result.items()}
            else:
                return deal.read(result,position=position)
        else:
            return result

    def runPool(self, pool, assumptions=[],read=True):
        url = f"{self.url}/run_pool"        
        req = self.build_pool_req(pool, assumptions=assumptions)

        result = self._send_req(req,url)

        if read:
            flow_header,idx = guess_pool_flow_header(result,self.lang)
            result = pd.DataFrame([_['contents'] for _ in result] , columns=flow_header)
            result = result.set_index(idx)
            result.index.rename(idx, inplace=True)
            result.sort_index(inplace=True)
        return result
    
    def _send_req(self,_req,_url)->dict:
        try:
            r = requests.post(_url, data=_req.encode('utf-8'), headers=self.hdrs, verify=False)
        except (ConnectionRefusedError, ConnectionError):
            return None

        if r.status_code != 200:
            print(json.loads(_req))
            raise RuntimeError(r.text)
        try:
            result = json.loads(r.text)
            return result
        except JSONDecodeError as e:
            raise RuntimeError(e)        

def guess_pool_flow_header(x,l):
    match (x[0]['tag'],l):
        case ('MortgageFlow','chinese'):
            return (["日期", "未偿余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失", "利率"],"日期")
        case ('MortgageFlow','english'):
            return (["Date", "Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC"],"Date")
        case ('LeaseFlow','chinese'):
            return (["日期", "租金"],"日期")
        case ('LeaseFlow','english'):
            return (["Date", "Rental"],"Date")
        case _:
            raise RuntimeError(f"Failed to match pool header with {x[0]['tag']}{l}")


def save(deal,p:str):
    def save_to(b):
        with open(p,'wb') as _f:
            pickle.dump(b,_f)

    match deal:
        case _:
            save_to(deal)

def init_jupyter():
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.options.display.float_format = '{:,}'.format


def comp_df(x, y):
    return pd.merge(x, y, on="日期", how='outer').sort_index().sort_index(axis=1)

def comp_engines(engine1,engine2, d, a=None):
    
    r1 = engine1.run(d,assumptions=a,read=True)
    r2 = engine2.run(d,assumptions=a,read=True)


    comp_result = {}
    # pool check
    if not r1['pool']['flow'].equals(r2['pool']['flow']):
        comp_result['pool'] = comp_df(r1['pool']['flow'],r2['pool']['flow'])
    else:
        comp_result['pool'] = True

    # expense check  
    comp_result['fee'] = {}
    for fn,f in r1['fees'].items():
        if not f.equals(r2['fees'][fn]):
            comp_result['fee'][fn] = comp_df(f,r2['fees'][fn])
        else:
            comp_result['fee'][fn] = True

    # bond check
    comp_result['bond'] = {}
    for fn,f in r1['bonds'].items():
        if not f.equals(r2['bonds'][fn]):
            comp_result['bond'][fn] = comp_df(f,r2['bonds'][fn])
        else:
            comp_result['bond'][fn] = True


    # account check
    comp_result['account'] = {}
    for fn,f in r1['accounts'].items():
        if not f.equals(r2['accounts'][fn]):
            comp_result['account'][fn] = comp_df(f,r2['accounts'][fn])
        else:
            comp_result['account'][fn] = True

    return comp_result

