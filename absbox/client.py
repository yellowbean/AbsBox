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
from absbox.validation import valReq,valAssumption

from importlib.metadata import version

VERSION_NUM = version("absbox")
urllib3.disable_warnings()


@dataclass
class API:
    url: str
    lang: str = "chinese"
    server_info = {}
    version = VERSION_NUM.split(".")
    hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain','Accept':'*/*'
            ,'Accept-Encoding':'gzip'}
    session = None

    def __post_init__(self):
        try:
            _r = requests.get(f"{self.url}/version",verify=False, timeout=5).text
        except (ConnectionRefusedError, ConnectionError):
            logging.error(f"Error: Can't not connect to API server {self.url}")
            self.url = None
            return

        echo = json.loads(_r)
        self.server_info = echo
        engine_version = echo['_version'].split(".")
        logging.info(f"Connect with engine {self.url} version {echo['_version']} successfully")
        
        if self.version[1] != engine_version[1]:
            logging.error(f"Failed to init the api instance, lib support={self.version} but server version={echo['version']} , pls upgrade your api package by: pip -U absbox")
            return
        else:
            self.session = requests.Session() 

    def build_req(self, deal, assumptions=None, pricing=None) -> str:
        r = None
        _assump = None 
        _deal = deal.json
        _pricing = mkPricingAssump(pricing) if pricing else None
        if isinstance(assumptions, dict):
            _assump = mapValsBy(assumptions, mkAssumption2)
            r = mkTag(("MultiScenarioRunReq",[_deal, _assump, _pricing]))
        elif isinstance(assumptions, list) :   
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

    def validate(self, _r) -> list:
        # validatin waterfall
        error, warning = valReq(_r)

        if warning:
            logging.warning(f"Warning in model :{warning}")

        if len(error)>0:
            logging.error(f"Error in model :{error}")
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
        val_result, err, warn = self.validate(req)
        if not val_result:
            return val_result, err, warn

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
            r = self.session.post(_url, data=_req.encode('utf-8'), headers=self.hdrs, verify=False, timeout=10)
        except (ConnectionRefusedError, ConnectionError):
            return None

        if r.status_code != 200:
            print(json.loads(_req))
            error_resp = json.loads(r.text)
            raise RuntimeError(error_resp.get("error","Empty Error Body"))
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
