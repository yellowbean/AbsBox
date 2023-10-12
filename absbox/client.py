import json, datetime, pickle, re, urllib3, getpass, copy
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

from absbox.local.util import mkTag, isDate, flat, guess_pool_locale, mapValsBy, guess_pool_flow_header, _read_cf, _read_asset_pricing, mergeStrWithDict, earlyReturnNone, searchByFst
from absbox.local.component import mkPool,mkAssumpType,mkNonPerfAssumps, mkPricingAssump,mkLiqMethod,mkAssetUnion,mkRateAssumption
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
    hdrs = {'Content-type': 'application/json', 'Accept': '*/*'
            , 'Accept-Encoding': 'gzip'}
    session = None
    debug = False

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

    def build_run_deal_req(self, run_type, deal, perfAssump=None, nonPerfAssump=[]) -> str:
        ''' build run deal requests: (single run, multi-scenario run, multi-struct run) '''
        r = None
        _nonPerfAssump = mkNonPerfAssumps({}, nonPerfAssump)

        match run_type:
            case "Single" | "S":
                _deal = deal.json if hasattr(deal,"json") else deal
                _perfAssump = earlyReturnNone(mkAssumpType,perfAssump)
                r = mkTag(("SingleRunReq",[_deal, _perfAssump, _nonPerfAssump]))
            case "MultiScenarios" | "MS":
                _deal = deal.json if hasattr(deal,"json") else deal
                mAssump = mapValsBy(perfAssump, mkAssumpType)
                r = mkTag(("MultiScenarioRunReq",[_deal, mAssump, _nonPerfAssump]))
            case "MultiStructs" | "MD" :
                mDeal = {k: v.json if hasattr(v,"json") else v for k,v in deal.items() }
                _perfAssump = mkAssumpType(perfAssump)
                r = mkTag(("MultiDealRunReq",[mDeal, _perfAssump, _nonPerfAssump]))
            case _:
                raise RuntimeError(f"Failed to match run type:{run_type}")
        return json.dumps(r, ensure_ascii=False)

    def build_pool_req(self, pool, poolAssump, rateAssumps, read=None) -> str:
        r = None
        if isinstance(poolAssump, tuple):
            r = mkTag(("SingleRunPoolReq"
                       ,[mkPool(pool)
                         ,mkAssumpType(poolAssump)
                         ,[mkRateAssumption(rateAssump) for rateAssump in rateAssumps] if rateAssumps else None]
                        ))
        elif isinstance(poolAssump, dict):
            r = mkTag(("MultiScenarioRunPoolReq"
                       ,[mkPool(pool)
                         ,mapValsBy(poolAssump, mkAssumpType)
                         ,[mkRateAssumption(rateAssump) for rateAssump in rateAssumps] if rateAssumps else None]
                        )) 
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
            poolAssump=None,
            runAssump=[],
            read=True):

        assert isinstance(runAssump, list),f"runAssump must be a list ,but got {type(runAssump)}"


        # if run req is a multi-scenario run
        multi_run_flag = True if isinstance(poolAssump, dict) else False
        url = f"{self.url}/runDealByScenarios" if multi_run_flag else f"{self.url}/runDeal"

        # construct request
        runType = "MultiScenarios" if multi_run_flag else "Single"
        req = self.build_run_deal_req(runType, deal, poolAssump, runAssump)
        #validate deal
        val_result, err, warn = self.validate(req)
        if not val_result:
            return val_result, err, warn
        # branching with pricing
        if runAssump is None or searchByFst(runAssump, "pricing") is None:
            result = self._send_req(req, url)
        else:
            result = self._send_req(req, url, timeout=30)

        if result is None:
            console.print("❌[bold red]Failed to get response from run")
            return None
        if 'error' in result:
            rich.print_json(result)
            return None
        # load deal if it is a multi scenario
        if read and multi_run_flag:
            return mapValsBy(result, deal.read)
        elif read:
            return deal.read(result)
        else:
            return result

    def runPool(self, pool, poolAssump=None, rateAssump=None, read=True):
        def read_single(pool_resp):
            (pool_flow, pool_bals) = pool_resp
            flow_header, idx = guess_pool_flow_header(pool_flow[0],pool_lang)
            try:
                result = pd.DataFrame([_['contents'] for _ in pool_flow], columns=flow_header)
            except ValueError as _:
                console.print(f"❌[bold red]Failed to match header:{flow_header} with {result[0]['contents']}")

            result = result.set_index(idx)
            result.index.rename(idx, inplace=True)
            result.sort_index(inplace=True)
            return (result, pool_bals)
            
        multi_scenario = True if isinstance(poolAssump, dict) else False 
        url = f"{self.url}/runPoolByScenarios" if multi_scenario else f"{self.url}/runPool"
        pool_lang = guess_pool_locale(pool)
        req = self.build_pool_req(pool, poolAssump, rateAssump)
        result = self._send_req(req, url)

        if read and (not multi_scenario):
            return read_single(result)
        elif read and multi_scenario: 
            return mapValsBy(result, read_single)
        else:
            return result
    
    def runStructs(self, deals, poolAssump=None, nonPoolAssump=None, read=True):
        assert isinstance(deals, dict),f"Deals should be a dict but got {deals}"
        url = f"{self.url}/runMultiDeals" 
        _poolAssump = mkAssumpType(poolAssump) if poolAssump else None 
        _nonPerfAssump = mkNonPerfAssumps({}, nonPoolAssump)
        req = json.dumps(mkTag(("MultiDealRunReq"
                                 ,[{k:v.json for k,v in deals.items()}
                                   ,_poolAssump
                                   ,_nonPerfAssump]))
                        ,ensure_ascii=False)

        result = self._send_req(req, url)
        if read:
            return {k: deals[k].read(v) for k, v in result.items()}    
        else:
            return result

    def runAsset(self, date, _assets, poolAssump=None, rateAssump=None, pricing=None, read=True):
        assert isinstance(_assets, list),f"Assets passed in must be a list"
        def readResult(x):
            try:
                ((cfs,cfBalance),pr) = x
                cfs = _read_cf(cfs, self.lang)
                pricingResult = _read_asset_pricing(pr, self.lang) if pr else None
            except Exception as e:
                print(f"Failed to read result {x}")
            return (cfs,cfBalance,pricingResult)
        url = f"{self.url}/runAsset"
        _assumptions = mkAssumpType(poolAssump) if poolAssump else None
        _pricing = mkLiqMethod(pricing) if pricing else None
        _rate = mkRateAssumption(rateAssump) if rateAssump else None
        assets = [ mkAssetUnion(_) for _ in _assets ]
        req = json.dumps([date
                          ,assets
                          ,_assumptions
                          ,_rate
                          ,_pricing]
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
            console.print(f"✅[bold green] login successfully,{r['msg']}")
            self.token = r['token']
        else:
            if hasattr(self,'token'):
                delattr(self,'token')
            console.print(f"❌[bold red]Failed to login,{r['msg']}")
            return None
    
    def safeLogin(self, user, **q):
        try:
            pw = getpass.getpass()
            self.loginLibrary(user, pw, **q)
        except Exception as e:
            console.print(f"❌[bold red]{e}")
    
    def queryLibrary(self,ks,**q):
        if not hasattr(self,"token"):
            console.print(f"❌[bold red] No token found , please call loginLibrary() to login")
            return 
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
        result = self._send_req(json.dumps(q), deal_library_url)
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
        prod_flag = {"production":p.get("production",True)}
        runReq = mergeStrWithDict (self.build_req(_id, dealAssump, pricingAssump), prod_flag )
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
            ri = result['run_info']
            result = result['run_result']
            console.print(f"✅[bold green]run success with deal id={ri['deal_id']}/report num={ri['report_num']},doc_id={ri['doc_id']}")
        except Exception as e:
            console.print(f"❌[bold red]message from API server:{result}")
            return None
        try:       
            classReader = lookupReader(p['reader'])
            if read and isinstance(result,list):
                return classReader.read(result)
            elif read and isinstance(result, dict):
                return {k:classReader.read(v) for k,v in result.items()}
            else:
                return result
        except Exception as e:
            console.print(f"❌[bold red]{e}")
            return None

    def _send_req(self,_req,_url,timeout=10,headers={})->dict:
        with console.status("") as status:
            try:
                hdrs = self.hdrs | headers
                r = self.session.post(_url, data=_req.encode('utf-8'), headers=hdrs, verify=False, timeout=timeout)
            except (ConnectionRefusedError, ConnectionError):
                console.print(f"❌[bold red] Failed to talk to server {_url}")
                return None
            except ReadTimeout:
                console.print(f"❌[bold red] Failed to get response from server")
                return None
            if r.status_code != 200:
                console.print_json(_req)
                console.print_json(r.text)
                return None
            try:
                return json.loads(r.text)
            except JSONDecodeError as e:
                console.print(e)
                return None
    
