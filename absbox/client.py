import json, datetime, pickle, re, urllib3
from importlib.metadata import version
from json.decoder import JSONDecodeError
from dataclasses import dataclass,field

import rich
from rich.console import Console
from rich.json import JSON
import requests
from requests.exceptions import ConnectionError,ReadTimeout
import pandas as pd
from pyspecter import query

from absbox.local.util import mkTag, isDate, flat, guess_pool_locale, mapValsBy, guess_pool_flow_header, _read_cf, _read_asset_pricing
from absbox.local.component import mkPool, mkAssumption, mkAssumption2, mkPricingAssump,mkLiqMethod,mkAssetUnion
from absbox.local.base import *
from absbox.validation import valReq,valAssumption

from absbox.local.china import SPV
from absbox.local.generic import Generic


VERSION_NUM = version("absbox")
urllib3.disable_warnings()
console = Console()

@dataclass
class API:
    url: str
    lang: str = "chinese"
    check: bool = True
    server_info = {}
    version = VERSION_NUM.split(".")
    hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain','Accept':'*/*' ,'Accept-Encoding':'gzip'}
    session = None

    def __post_init__(self):
        self.url = self.url.rstrip("/")
        with console.status(f"[magenta]Connecting engine server -> {self.url}") as status:
            try:
                _r = requests.get(f"{self.url}/version",verify=False, timeout=5).text
            except (ConnectionRefusedError, ConnectionError):
                console.print(f"❌[bold red]Error: Can't not connect to API server {self.url}")
                self.url = None
                return

            self.server_info = self.server_info | json.loads(_r)
            engine_version = self.server_info['_version'].split(".")
            if self.check and (self.version[1] != engine_version[1]):
                console.print(f"❌[bold red]Failed to init the api instance, lib support={self.version} but server version={self.server_info['_version']} , pls upgrade your api package by: pip -U absbox")
                return
        console.print(f"✅[bold green]Connected, local lib:{'.'.join(self.version)}, server:{'.'.join(engine_version)}")
        self.session = requests.Session() 

    def build_req(self, deal, assumptions=None, pricing=None) -> str:
        r = None
        _assump = None 
        _deal = deal.json if not isinstance(deal,str) else deal
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
            console.print(f"❕[bold yellow]Warning in model :{warning}")
        if len(error)>0:
            console.print(f"❌[bold red]Error in model :{error}")
            return False,error,warning
        else:
            return True,error,warning

    def run(self, deal,
            assumptions=None,
            pricing=None,
            read=True,
            position=None):

        # if run req is a multi-scenario run
        multi_run_flag = True if isinstance(assumptions, dict) else False
        url = f"{self.url}/runDealByScenarios"  if multi_run_flag  else f"{self.url}/runDeal"

        # construct request
        req = self.build_req(deal, assumptions, pricing)
        #validate deal
        val_result, err, warn = self.validate(req)
        if not val_result:
            return val_result, err, warn
        if pricing is None:
            result = self._send_req(req,url)
        else:
            result = self._send_req(req,url,timeout=30)
        if result is None:
            console.print("❌[bold red]Failed to get response from run")
            return None
        if read and multi_run_flag:
            return {n:deal.read(_r) for (n,_r) in result.items()}
        elif read :
            return deal.read(result)
        else:
            return result

    def runPool(self, pool, assumptions,read=True):
        def read_single(pool_resp):
            flow_header,idx = guess_pool_flow_header(pool_resp[0],pool_lang)
            try:
                result = pd.DataFrame([_['contents'] for _ in pool_resp] , columns=flow_header)
            except ValueError as e:
                console.print(f"❌[bold red]Failed to match header:{flow_header} with {result[0]['contents']}")
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

    def runAsset(self, date, _assets, assumptions=None, pricing=None, read=True):
        assert isinstance(_assets, list),f"Assets passed in must be a list"
        def readResult(x):
            (cfs,pr) = x
            cfs = _read_cf(cfs, self.lang)
            pricingResult = _read_asset_pricing(pr, self.lang) if pr else None
            return (cfs,pricingResult)
        url = f"{self.url}/runAsset"
        _assumptions = mkAssumption2(assumptions) 
        _pricing =  mkLiqMethod(pricing) if pricing else None
        assets = [ mkAssetUnion(_) for _ in _assets] 
        req = json.dumps([date ,assets ,_assumptions ,_pricing]
                         ,ensure_ascii=False)
        result = self._send_req(req,url)
        if read :
            return readResult(result)
        else:
            return result

    def loginLibrary(self, user, pw, **q):
        deal_library_url = q['deal_library']+"/token"
        cred = {"user":user,"password":pw}
        r = self._send_req(json.dumps(cred), deal_library_url)
        if 'token' in r:
            console.print(f"✅[bold green] login successfully")
            self.token = r['token']
        else:
            console.print(f"❌[bold red]Failed to login")
            return None
            
    
    def queryLibrary(self,ks,**q):
        deal_library_url = q['deal_library']+"/query"
        d = {"bond_id": [k for k in ks] }
        q = {"read":True} | q
        result = self._send_req(json.dumps(d|q), deal_library_url,headers= {"Authorization":f"Bearer {self.token}"})
        console.print(f"✅[bold green] query success")
        if q['read'] == True:
            if 'data' in result:
                return pd.DataFrame(result['data'],columns=result['header'])
            elif 'error' in result:
                return pd.DataFrame([result["error"]],columns=["error"])
        else:
            return result

    def listLibrary(self,**q):
        deal_library_url = q['deal_library']+"/list"
        result = self._send_req(json.dumps({}), deal_library_url)
        console.print(f"✅[bold green]list success")
        if ('read' in q) and (q['read'] == True):
            return pd.DataFrame(result['data'],columns=result['header'])
        else:
            return result

    def runLibrary(self,_id,**p):
        deal_library_url = p['deal_library']+"/run"
        read = p.get("read",True)
        pricingAssump = p.get("pricing",None)
        dealAssump = p.get("assump",None)
        runReq = self.build_req(_id, dealAssump, pricingAssump) # {"production":p.get("production",True)}
        if not hasattr(self,"token"):
            console.print(f"❌[bold red] No token found , please call loginLibrary() to login")
            return 
        result = self._send_req(runReq, deal_library_url, headers={"Authorization":f"Bearer {self.token}"})
        def lookupReader(x):
            match x:
                case "china.SPV":
                    return SPV
                case "generic.Generic":
                    return Generic
                case _:
                    raise RuntimeError(f"Failed to match reader:{x}")
        try:
            result = json.loads(result)
               
            classReader = lookupReader(p['reader'])
            console.print(f"✅[bold green]run success")
            if read and isinstance(result,list):
                return classReader.read(result)
            elif read and isinstance(result, dict):
                return {k:classReader.read(v) for k,v in result.items()}
            else:
                return result
        except Exception as e:
            console.print(f"❌[bold red]message from API server:{result}")
            console.print(f"❌[bold red]{e}")

    def _send_req(self,_req,_url,timeout=10,headers={})->dict:
        with console.status("") as status:
            try:
                hdrs = self.hdrs | headers
                r = self.session.post(_url, data=_req.encode('utf-8'), headers=hdrs, verify=False, timeout=timeout)
            except (ConnectionRefusedError, ConnectionError):
                console.print(f"❌[bold red] Failed to talk to server {_url}")
                console.rule()
                return None
            except ReadTimeout:
                console.print(f"❌[bold red] Failed to get response from server")
                console.rule()
                return None
            if r.status_code != 200:
                console.print_json(_req)
                console.rule()
                print(">>>",r.text)
                console.print_json(r.text)
                console.rule()
                return None
            try:
                return json.loads(r.text)
            except JSONDecodeError as e:
                console.print(e)
                console.rule()
                return None
    


def save(deal,p:str):
    def save_to(b):
        with open(p,'wb') as _f:
            pickle.dump(b,_f)

    match deal:
        case _:
            save_to(deal)
