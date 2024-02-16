import json, urllib3, getpass, enum
from importlib.metadata import version
from schema import Schema
import toolz as tz
from json.decoder import JSONDecodeError
from dataclasses import dataclass

from rich.console import Console
import requests
from requests.exceptions import ConnectionError, ReadTimeout
import pandas as pd
from absbox.validation import isValidUrl,vStr

from absbox.local.util import mkTag, guess_pool_locale, mapValsBy, guess_pool_flow_header \
                              , _read_cf, _read_asset_pricing, mergeStrWithDict \
                              , earlyReturnNone, searchByFst, filter_by_tags \
                              , enumVals, lmap
from absbox.local.component import mkPool, mkAssumpType, mkNonPerfAssumps, mkLiqMethod \
                                   , mkAssetUnion, mkRateAssumption
from absbox.local.base import ValidationMsg

from absbox.local.china import SPV
from absbox.local.generic import Generic


VERSION_NUM = version("absbox")
urllib3.disable_warnings()
console = Console()


class Endpoints(str, enum.Enum):
    RunAsset = "runAsset"
    RunPool = "runPool"
    RunPoolByScenarios = "runPoolByScenarios"
    RunDeal = "runDeal"
    RunDealByScnearios = "runDealByScenarios"
    RunMultiDeal = "runMultiDeals"
    Version = "version"


class RunReqType(str, enum.Enum):
    Single = "SingleRunReq"
    MultiScenarios = "MultiScenarioRunReq"
    MultiStructs = "MultiDealRunReq"
    SinglePool = "SingleRunPoolReq"
    MultiPoolScenarios = "MultiScenarioRunPoolReq"


class RunResp(int, enum.Enum):
    DealResp = 0
    PoolResp = 1
    LogResp = 2


class MsgColor(str, enum.Enum):
    Warning = "[bold yellow]"
    Error = "[bold red]"
    Success = "[bold green]"
    Info = "[bold magenta]"


class LibraryEndpoints(str, enum.Enum):
    Token = "token"
    Query = "query"
    List = "list"
    Run = "run"


@dataclass
class API:
    """
    API to connect to engine server, handling requests and responses


    """
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
        self.url = isValidUrl(self.url).rstrip("/")
        with console.status(f"{MsgColor.Info.value}Connecting engine server -> {self.url}") as status:
            try:
                _r = requests.get(f"{self.url}/{Endpoints.Version.value}", verify=False, timeout=5).text
            except (ConnectionRefusedError, ConnectionError):
                console.print(f"❌{MsgColor.Error.value}Error: Can't not connect to API server {self.url}")
                self.url = None
                return
            if _r is None:
                raise RuntimeError(f"Failed to get version from url:{self.url}")
            print("self.server_info", self.server_info)
            self.server_info = self.server_info | json.loads(_r)
            engine_version = self.server_info['_version'].split(".")
            if self.check and (self.version[1] != engine_version[1]):
                console.print(f"❌{MsgColor.Error.value}Failed to init the api instance, lib support={self.version} but server version={self.server_info['_version']} , pls upgrade your api package by: pip -U absbox")
                return
        console.print(f"✅{MsgColor.Success.value}Connected, local lib:{'.'.join(self.version)}, server:{'.'.join(engine_version)}")
        self.session = requests.Session()

    def build_run_deal_req(self, run_type: str, deal, perfAssump=None, nonPerfAssump=[]) -> str:
        ''' build run deal requests: (single run, multi-scenario run, multi-struct run)
              perfAssump: tuple or dict
              nonPerfAssump: list of non-performance assumptions 
        '''
        r = None
        _nonPerfAssump = mkNonPerfAssumps({}, nonPerfAssump)

        match Schema(str).validate(run_type):
            case "Single" | "S":
                _deal = deal.json if hasattr(deal, "json") else deal
                _perfAssump = earlyReturnNone(mkAssumpType, perfAssump)
                r = mkTag((RunReqType.Single.value, [_deal, _perfAssump, _nonPerfAssump]))
            case "MultiScenarios" | "MS":
                _deal = deal.json if hasattr(deal, "json") else deal
                mAssump = mapValsBy(perfAssump, mkAssumpType)
                r = mkTag((RunReqType.MultiScenarios.value, [_deal, mAssump, _nonPerfAssump]))
            case "MultiStructs" | "MD" :
                mDeal = {k: v.json if hasattr(v, "json") else v for k, v in deal.items()}
                _perfAssump = mkAssumpType(perfAssump)
                r = mkTag((RunReqType.MultiStructs.value, [mDeal, _perfAssump, _nonPerfAssump]))
            case _:
                raise RuntimeError(f"Failed to match run type:{run_type}")
        return json.dumps(r, ensure_ascii=False)

    def build_pool_req(self, pool, poolAssump, rateAssumps) -> str:
        ''' build run pool requests: (single run, multi-scenario run) 
              poolAssump: tuple or dict
              rateAssumps: list of rate assumptions 
        '''
        r = None
        #_rateAssump = [mkRateAssumption(rateAssump) for rateAssump in rateAssumps] if rateAssumps else None
        _rateAssump = map(mkRateAssumption, rateAssumps) if rateAssumps else None
        if isinstance(poolAssump, tuple):
            r = mkTag((RunReqType.SinglePool.value,
                       [mkPool(pool), mkAssumpType(poolAssump), _rateAssump]))
        elif isinstance(poolAssump, dict):
            r = mkTag((RunReqType.MultiPoolScenarios.value,
                       [mkPool(pool), mapValsBy(poolAssump, mkAssumpType), _rateAssump])) 
        else:
            raise RuntimeError("Error in build pool req")
        return json.dumps(r, ensure_ascii=False)

    def run(self, deal,
            poolAssump=None,
            runAssump=[],
            read=True,
            preCheck=True,
            showWarning=True):
        """ run deal with pool and deal run assumptions, with option of sensitivity run

        :param deal: _description_
        :type deal: _type_
        :param poolAssump: _description_, defaults to None
        :type poolAssump: _type_, optional
        :param runAssump: _description_, defaults to []
        :type runAssump: list, optional
        :param read: _description_, defaults to True
        :type read: bool, optional
        :param preCheck: _description_, defaults to True
        :type preCheck: bool, optional
        :param showWarning: _description_, defaults to True
        :type showWarning: bool, optional
        :return: _description_
        :rtype: _type_
        """        
        # if run req is a multi-scenario run
        multi_run_flag = True if isinstance(poolAssump, dict) else False
        url = f"{self.url}/{Endpoints.RunDealByScnearios.value}" if multi_run_flag else f"{self.url}/{Endpoints.RunDeal.value}"

        # construct request
        runType = "MultiScenarios" if multi_run_flag else "Single"
        req = self.build_run_deal_req(runType, deal, poolAssump, runAssump)
        # branching with pricing
        if runAssump is None or searchByFst(runAssump, "pricing") is None:
            result = self._send_req(req, url)
        else:
            result = self._send_req(req, url, timeout=30)

        if result is None or 'error' in result:
            console.print("❌[bold red]Failed to get response from run")
            return None
        
        rawWarnMsg = []
        if multi_run_flag:
            rawWarnMsgByScen = {k: [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(v[RunResp.LogResp.value], enumVals(ValidationMsg))] for k, v in result.items()}
            rawWarnMsg = [b for a in rawWarnMsgByScen.values() for b in a]
        else:
            rawWarnMsg = [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(result[RunResp.LogResp.value], enumVals(ValidationMsg))]
        
        if rawWarnMsg and showWarning:
            console.print("Warning Message from server:\n"+"\n".join(rawWarnMsg))

        # read multi-scenario run result into dict
        if read and multi_run_flag:
            return tz.valmap(deal.read, result)
        # read single scenario run result into tuple
        elif read:
            return deal.read(result)
        # return raw response
        else:
            return result

    def runPool(self, pool, poolAssump=None, rateAssump=None, read=True):
        def read_single(pool_resp):
            (pool_flow, pool_bals) = pool_resp
            flow_header, idx, expandFlag = guess_pool_flow_header(pool_flow[0], pool_lang)
            result = None
            try:
                if not expandFlag:
                    result = pd.DataFrame(tz.pluck('contents', pool_flow), columns=flow_header)
                else:
                    result = pd.DataFrame([_['contents'][-1]+_['contents'][-1] for _ in pool_flow], columns=flow_header)
            except ValueError as e:
                console.print(f"❌{MsgColor.Error.value}Failed to match header:{flow_header} with {pool_flow[0]['contents']}")
                console.print(f"error:{e}")

            result = result.set_index(idx)
            result.index.rename(idx, inplace=True)
            result.sort_index(inplace=True)
            return (result, pool_bals)
            
        multi_scenario = True if isinstance(poolAssump, dict) else False 
        url = f"{self.url}/{Endpoints.RunPoolByScenarios.value}" if multi_scenario else f"{self.url}/{Endpoints.RunPool.value}"
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
        assert isinstance(deals, dict), f"Deals should be a dict but got {type(deals)}"
        url = f"{self.url}/{Endpoints.RunMultiDeal.value}" 
        _poolAssump = mkAssumpType(poolAssump) if poolAssump else None 
        _nonPerfAssump = mkNonPerfAssumps({}, nonPoolAssump)
        req = json.dumps(mkTag(("MultiDealRunReq"
                                 ,[ tz.valmap(lambda x:x.json, deals)  # {k:v.json for k,v in deals.items()}
                                   ,_poolAssump
                                   ,_nonPerfAssump]))
                         ,ensure_ascii=False)

        result = self._send_req(req, url)
        if read:
            return {k: deals[k].read(v) for k, v in result.items()}    
        else:
            return result

    def runAsset(self, date, _assets, poolAssump=None, rateAssump=None
                 , pricing=None, read=True):
        assert isinstance(_assets, list), f"Assets passed in must be a list"
        
        def readResult(x):
            try:
                ((cfs, cfBalance), pr) = x
                cfs = _read_cf(cfs['contents'], self.lang)
                pricingResult = _read_asset_pricing(pr, self.lang) if pr else None
                return (cfs, cfBalance, pricingResult)
            except Exception as e:
                print(f"Failed to read result {x} \n with error {e}")
                return (None, None, None)
        url = f"{self.url}/{Endpoints.RunAsset.value}"
        _assumptions = mkAssumpType(poolAssump) if poolAssump else None
        _pricing = mkLiqMethod(pricing) if pricing else None
        _rate = lmap(mkRateAssumption, rateAssump) if rateAssump else None
        assets = lmap(mkAssetUnion, _assets)  # [mkAssetUnion(_) for _ in _assets]
        req = json.dumps([date, assets, _assumptions, _rate, _pricing], ensure_ascii=False)
        result = self._send_req(req, url)
        if read:
            return readResult(result)
        else:
            return result

    def loginLibrary(self, user, pw, **q):
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.Token.value}"
        cred = {"user": vStr(user), "password": pw}
        r = self._send_req(json.dumps(cred), deal_library_url)
        if 'token' in r:
            console.print(f"✅{MsgColor.Success.value} login successfully,{r['msg']}")
            self.token = r['token']
        else:
            if hasattr(self, 'token'):
                delattr(self, 'token')
            console.print(f"❌{MsgColor.Error.value} Failed to login,{r['msg']}")
            return None
    
    def safeLogin(self, user, **q):
        try:
            pw = getpass.getpass()
            self.loginLibrary(user, pw, **q)
        except Exception as e:
            console.print(f"❌{MsgColor.Error.value}{e}")
    
    def queryLibrary(self, ks, **q):
        if not hasattr(self, "token"):
            console.print(f"❌{MsgColor.Error.value} No token found , please call loginLibrary() to login")
            return None
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.Query.value}"
        d = {"bond_id": [k for k in ks]}
        q = {"read": True} | q
        result = self._send_req(json.dumps(d|q), deal_library_url, headers={"Authorization": f"Bearer {self.token}"})
        console.print(f"✅{MsgColor.Success.value} query success")
        if q['read']:
            if 'data' in result:
                return pd.DataFrame(result['data'], columns=result['header'])
            elif 'error' in result:
                return pd.DataFrame([result["error"]], columns=["error"])
        else:
            return result

    def listLibrary(self, **q):
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.List.value}"
        result = self._send_req(json.dumps(q), deal_library_url)
        console.print(f"✅{MsgColor.Success.value} list success")
        if ('read' in q) and (q['read'] == True):
            return pd.DataFrame(result['data'], columns=result['header'])
        else:
            return result

    def runLibrary(self, _id, **p):
        deal_library_url = p['deal_library']+f"/{LibraryEndpoints.Run.value}"
        read = p.get("read", True)
        pricingAssump, dealAssump = tz.get(["pricing", "assump"], p, None)
        runType = p.get("runType", "S")
        prod_flag = {"production": p.get("production", True)}

        runReq = mergeStrWithDict(self.build_run_deal_req(runType, _id, dealAssump, pricingAssump), prod_flag)
        if not hasattr(self, "token"):
            console.print(f"❌{MsgColor.Error.value} No token found , please call loginLibrary() to login")
            return 
        result = self._send_req(runReq, deal_library_url, headers={"Authorization": f"Bearer {self.token}"})
        
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
            console.print(f"✅{MsgColor.Success.value}run success with deal id={ri['deal_id']}/report num={ri['report_num']},doc_id={ri['doc_id']}")
        except Exception as e:
            console.print(f"❌{MsgColor.Error.value} message from API server:{result},\n,{e}")
            return None
        try:       
            classReader = lookupReader(p['reader'])
            if read and isinstance(result, list):
                return classReader.read(result)
            elif read and isinstance(result, dict):
                return tz.valmap(classReader.read, result)  # {k: classReader.read(v) for k, v in result.items()}
            else:
                return result
        except Exception as e:
            console.print(f"❌{MsgColor.Error.value}: Failed to read result with error = {e}")
            return None

    def _send_req(self, _req, _url: str, timeout=10, headers={})-> dict | None:
        '''
            send requests to server, raise error if response is not 200
        '''
        with console.status("") as status:
            try:
                hdrs = self.hdrs | headers
                r = None
                if self.session:
                    r = self.session.post(_url, data=_req.encode('utf-8'), headers=hdrs
                                         , verify=False, timeout=timeout)
                else:
                    console.print(f"❌{MsgColor.Error.value} None type for session")
                    return None
            except (ConnectionRefusedError, ConnectionError):
                console.print(f"❌{MsgColor.Error.value} Failed to talk to server {_url}")
                return None
            except ReadTimeout:
                console.print(f"❌{MsgColor.Error.value} Failed to get response from server")
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