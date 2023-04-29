import logging, json, datetime, pickle, re
from json.decoder import JSONDecodeError
import requests
from requests.exceptions import ConnectionError
import urllib3
from dataclasses import dataclass,field
from absbox.local.util import mkTag, isDate, flat, guess_pool_locale, mapValsBy, guess_pool_flow_header
from absbox.local.component import mkPool, mkAssumption, mkAssumption2, mkPricingAssump
from absbox.local.base import *
import pandas as pd
from pyspecter import query

from importlib.metadata import version

VERSION_NUM = version("absbox")
urllib3.disable_warnings()


@dataclass
class API:
    url: str
    lang: str = "chinese"
    server_info = {}
    #version = "0","14","1"
    version = VERSION_NUM.split(".")
    hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain','Accept':'*/*'}

    def __post_init__(self):
        try:
            _r = requests.get(f"{self.url}/version",verify=False).text
        except (ConnectionRefusedError, ConnectionError):
            logging.error(f"Error: Can't not connect to API server {self.url}")
            self.url = None
            return

        echo = json.loads(_r)
        self.server_info = echo
        x,y,z = echo['_version'].split(".")
        logging.info(f"Connect with engine {self.url} version {echo['_version']} successfully")
        if self.version[1] != y:
            logging.error(f"Failed to init the api instance, lib support={self.version} but server version={echo['version']} , pls upgrade your api package by: pip -U absbox")
            return

    def build_req(self, deal, assumptions=None, pricing=None) -> str:
        r = None
        _assump = None 
        _deal = deal.json
        _pricing = mkPricingAssump(pricing) if pricing else None
        if isinstance(assumptions, dict):
            # _assump = { scenarioName:mkAssumption2(a) for (scenarioName,a) in assumptions.items()}
            _assump = mapValsBy(assumptions, mkAssumption2)
            r = mkTag(("MultiScenarioRunReq",[_deal, _assump, _pricing]))
        elif isinstance(assumptions, list) :   
            # _assump = mkTag(("Single",mkAssumption2(assumptions)))
            _assump = mkAssumption2(assumptions)
            r = mkTag(("SingleRunReq",[_deal, _assump, _pricing]))
        elif assumptions is None:
            r = mkTag(("SingleRunReq",[_deal, None, _pricing]))
        return json.dumps(r , ensure_ascii=False)

    def build_pool_req(self, pool, assumptions, read=None) -> str:
        r = None
        if isinstance(assumptions, list):
            r = mkTag(("SingleRunPoolReq"
                      ,[mkPool(pool)
                        ,mkAssumption2(assumptions)])) 
        elif isinstance(assumptions, dict):
            r = mkTag(("MultiScenarioRunPoolReq"
                      ,[mkPool(pool)
                        ,mapValsBy(assumptions, mkAssumption2)])) 
        else:
            raise RuntimeError("Error in build pool req")
        return json.dumps(r , ensure_ascii=False)

    def _validate_assump(self, x, e, w):
        def asset_check(_e, _w):
            return _e, _w
        def _validate_single_assump(z):
            match z:
                case {'tag': 'PoolLevel'}:
                    return [True, e, w]
                case {'tag':'ByIndex', 'contents':(assumps, _)}:
                    _ids = set(flat([ assump[0] for assump in assumps ]))
                    if not _ids.issubset(asset_ids):
                        e.append(f"Not Valid Asset ID:{_ids - asset_ids}")
                    if len(missing_asset_id := asset_ids - _ids) > 0:
                        w.append(f"Missing Asset to set assumption:{missing_asset_id}")            
                case None:
                    return [True, e, w]
                case _:
                    raise RuntimeError(f"Failed to match:{a}")
        a = x['contents'][1]
        asset_ids = set(range(len(query(x['contents'][0], ['contents', 'pool', 'assets']))))
        match x:
            case {"tag":"SingleRunReq","contents":[d,ma,_]}:
                _validate_single_assump(ma)
            case {"tag":"MultiScenarioRunReq","contents":[d,mam,_]}:
                mapValsBy(mam, _validate_single_assump)
            case {"tag":"MultiDealRunReq","contents":[dm,ma,_]}:
                _validate_single_assump(ma)

        if len(e) > 0:
            return [False, e, w]
        return [True, e, w]

    def validate(self, _r) -> list:
        error = []
        warning = []
        _r = json.loads(_r)
        __d = _r['contents'][0]
        _d = __d['contents']
        valid_acc = set(_d['accounts'].keys())
        valid_bnd = set(_d['bonds'].keys())
        valid_fee = set(_d['fees'].keys())
        _w = _d['waterfall']
        #print("Waterfall",_w)

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
            read=True,
            position=None,
            timing=False):

        if isinstance(assumptions,str):
            assumptions = pickle.load(assumptions)

        # if run req is a multi-scenario run
        multi_run_flag = True if isinstance(assumptions, dict) else False
        url = f"{self.url}/runDealByScenarios"  if multi_run_flag  else f"{self.url}/runDeal"

        if isinstance(deal, str):
            with open(deal,'rb') as _f:
                c = _f.read()
                deal = pickle.loads(c)

        # construct request
        req = self.build_req(deal, assumptions, pricing)

        #validate deal
        deal_validate,err,warn = self.validate(req)
        if not deal_validate:
            return deal_validate,err,warn

        result = self._send_req(req,url)

        if read and multi_run_flag:
                return { n:deal.read(_r,position=position) for (n,_r) in result.items()}
        elif read :
                return deal.read(result,position=position)
        else:
            return result

    def runPool(self, pool, assumptions,read=True):
        def read_single(pool_resp):
            flow_header,idx = guess_pool_flow_header(pool_resp[0],pool_lang)
            try:
                result = pd.DataFrame([_['contents'] for _ in pool_resp] , columns=flow_header)
            except ValueError as e:
                logging.error(f"Failed to match header:{flow_header} with {result[0]['contents']}")
            result = result.set_index(idx)
            result.index.rename(idx, inplace=True)
            result.sort_index(inplace=True)
            return result
            
        multi_scenario = True if isinstance(assumptions, dict) else False 
        url = f"{self.url}/runPoolByScenarios" if multi_scenario else f"{self.url}/runPool"
        pool_lang = guess_pool_locale(pool)
        req = self.build_pool_req(pool, assumptions=assumptions)
        result = self._send_req(req, url)

        if read and (not multi_scenario):
            return read_single(result)
        elif read and multi_scenario : 
            return mapValsBy(result, read_single)
        else:
            return result

    
    def runStructs(self, deals, assumptions=None, pricing=None, read=True ):
        assert isinstance(deals, dict),f"Deals should be a dict but got {deals}"
        url = f"{self.url}/runMultiDeals" 
        _assumptions = mkAssumption2(assumptions) if assumptions else None 
        _pricing = mkPricingAssump(pricing) if pricing else None
        req = json.dumps(mkTag(("MultiDealRunReq"
                                ,[{k:v.json for k,v in deals.items()}
                                  ,_assumptions
                                  ,_pricing]))
                        ,ensure_ascii=False)

        result = self._send_req(req,url)
        if read :
            return {k:deals[k].read(v) for k,v in result.items()}    
        else:
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




def save(deal,p:str):
    def save_to(b):
        with open(p,'wb') as _f:
            pickle.dump(b,_f)

    match deal:
        case _:
            save_to(deal)
