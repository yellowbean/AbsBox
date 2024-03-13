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

__all__ = ["API", "Endpoints", "RunReqType", "RunResp", "MsgColor", "LibraryEndpoints"]


class Endpoints(str, enum.Enum):
    """API endpoints for engine server

    """
    RunAsset = "runAsset"
    """Run single asset endpoint"""
    RunPool = "runPool"
    """Run a pool of asset endpoint"""
    RunPoolByScenarios = "runPoolByScenarios"
    """Run a pool of asset with multiple scenarios endpoint"""
    RunDeal = "runDeal"
    """Run a single deal endpoint"""
    RunDealByScnearios = "runDealByScenarios"
    """Run a single deal with multiple scenarios endpoint"""
    RunMultiDeal = "runMultiDeals"
    """Run multiple deals endpoint"""
    Version = "version"
    """Get version of engine server endpoint"""


class RunReqType(str, enum.Enum):
    """Request run type
    """
    Single = "SingleRunReq"
    """ Single Deal With A Single Assumption """
    MultiScenarios = "MultiScenarioRunReq"
    """ Single Deal With Multiple Assumptions """
    MultiStructs = "MultiDealRunReq"
    """ Multiple Deals With Single Assumption """
    SinglePool = "SingleRunPoolReq"
    """ Single Pool With Single Assumption """
    MultiPoolScenarios = "MultiScenarioRunPoolReq"
    """ Single Pool With Multiple Assumptions """


class RunResp(int, enum.Enum):
    """Internal
    """
    DealResp = 0
    PoolResp = 1
    LogResp = 2


class MsgColor(str, enum.Enum):
    Warning = "[bold yellow]"
    Error = "[bold red]"
    Success = "[bold green]"
    Info = "[bold magenta]"


class LibraryEndpoints(str, enum.Enum):
    """Endpoints for deal library"""
    Token = "token"
    Query = "query"
    List = "list"
    Run = "run"


class VersionMismatch(Exception):
    """Exception for version mismatch between client and server"""
    def __init__(self, libVersion, serverVersion) -> None:
        self.libVersion = libVersion
        self.serverVersion = serverVersion
        super().__init__(f"Failed to match version, lib support={libVersion} but server version={serverVersion}")


class EngineError(Exception):
    """Exception for error from engine server"""
    def __init__(self, engineResp) -> None:
        errorMsg = engineResp.text
        super().__init__(errorMsg)


class AbsboxError(Exception):
    """Exception for error from absbox"""
    def __init__(self, errorMsg) -> None:
        super().__init__(errorMsg)


@dataclass
class API:
    """ API to connect to engine server, handling requests and responses 

    :return: API instance
    :rtype: API
    """
    
    url: str
    """url of engine server"""
    lang: str = "chinese"
    """language of response from server, defaults to 'chinese' """

    check: bool = True
    """ flag to ensure version match between client and server """
    server_info = {}
    """ internal """
    version = VERSION_NUM.split(".")
    """ internal """
    hdrs = {'Content-type': 'application/json', 'Accept': '*/*', 'Accept-Encoding': 'gzip'}
    """ internal """
    session = None
    """ internal """
    debug = False
    """ internal """

    def __post_init__(self) -> None:
        """Init the API instance with url and perform version check

        :raises ConnectionRefusedError: Failed to connect to server
        :raises RuntimeError: Failed to get version info from server
        :raises VersionMismatch: Failed to match version between client and server
        """
        self.url = isValidUrl(self.url).rstrip("/")
        with console.status(f"{MsgColor.Info.value}Connecting engine server -> {self.url}") as status:
            try:
                _r = requests.get(f"{self.url}/{Endpoints.Version.value}", verify=False, timeout=5).text
            except (ConnectionRefusedError, ConnectionError):
                raise AbsboxError(f"❌{MsgColor.Error.value}Error: Can't not connect to API server {self.url}")
            if _r is None:
                raise RuntimeError(f"Failed to get version from url:{self.url}")
            self.server_info = self.server_info | json.loads(_r)
            engine_version = self.server_info['_version'].split(".")
            if self.check and (self.version[1] != engine_version[1]):
                console.print("pls upgrade your api package by: pip -U absbox")
                raise VersionMismatch('.'.join(self.version), '.'.join(engine_version))
        console.print(f"✅{MsgColor.Success.value}Connected, local lib:{'.'.join(self.version)}, server:{'.'.join(engine_version)}")
        self.session = requests.Session()

    def build_run_deal_req(self, run_type: str, deal, perfAssump=None, nonPerfAssump=[]) -> str:
        """build run deal requests: (single run, multi-scenario run, multi-struct run) 2
        
        :meta private:
        :param run_type: type of run request, RunReqType.Single.value, RunReqType.MultiScenarios.value, RunReqType.MultiStructs.value
        :type run_type: str
        :param deal: a deal/transaction object
        :type deal: _type_
        :param perfAssump: a tuple of pool level assumption(Default/Prepayment/Recovery) for single run. a map for multi-scenario run, defaults to None
        :type perfAssump: _type_, optional
        :param nonPerfAssump: a list of deal level assumptions, defaults to []
        :type nonPerfAssump: list, optional
        :raises RuntimeError: _description_
        :return: a string of request body to be sent out to engine
        :rtype: str

        """
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
        try:
            return json.dumps(r, ensure_ascii=False)
        except TypeError as e:
            raise AbsboxError(f"❌Failed to convert request to json:{e}")

    def build_pool_req(self, pool, poolAssump, rateAssumps) -> str:
        """build pool run request: (single run, multi-scenario run)

        :meta private:
        :param pool: a pool object
        :type pool: _type_
        :param poolAssump: a tuple of pool level assumption(Default/Prepayment/Recovery) for single run. a map for multi-scenario run
        :type poolAssump: _type_
        :param rateAssumps: a list of rate assumptions
        :type rateAssumps: _type_
        :raises RuntimeError: _description_
        :return: a string of request body to be sent out to engine
        :rtype: str

        """
        r = None
        _rateAssump = map(mkRateAssumption, rateAssumps) if rateAssumps else None
        if isinstance(poolAssump, tuple):
            r = mkTag((RunReqType.SinglePool.value,
                       [mkPool(pool), mkAssumpType(poolAssump), _rateAssump]))
        elif isinstance(poolAssump, dict):
            r = mkTag((RunReqType.MultiPoolScenarios.value,
                       [mkPool(pool), mapValsBy(poolAssump, mkAssumpType), _rateAssump])) 
        else:
            raise RuntimeError(f"Error in build pool req, pool assumption should be a tuple or a dict, but got {type(poolAssump)}")
        return json.dumps(r, ensure_ascii=False)

    def run(self, deal,
            poolAssump=None,
            runAssump=[],
            read=True,
            preCheck=True,
            showWarning=True):
        """ run deal with pool and deal run assumptions, with option of sensitivity run

        :param deal: a deal object
        :type deal: Generic | SPV
        :param poolAssump: pool performance assumption, a tuple for single run/ a dict for multi-sceanrio run, defaults to None
        :type poolAssump: tuple | dict , optional
        :param runAssump: deal level assumption, defaults to []
        :type runAssump: list, optional
        :param read: flag to convert result to pandas dataframe, defaults to True
        :type read: bool, optional
        :param preCheck: flag to perform a client side validation check, defaults to True
        :type preCheck: bool, optional
        :param showWarning: flag to show warnings, defaults to True
        :type showWarning: bool, optional
        :return: result of run, a dict or dataframe
        :rtype: dict | pd.DataFrame

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
            raise AbsboxError(f"❌{MsgColor.Error.value}Failed to get response from run")

        rawWarnMsg = []
        if multi_run_flag:
            rawWarnMsgByScen = {k: [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(v[RunResp.LogResp.value], enumVals(ValidationMsg))] for k, v in result.items()}
            rawWarnMsg = tz.concat(rawWarnMsgByScen.values())
        else:
            rawWarnMsg = [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(result[RunResp.LogResp.value], enumVals(ValidationMsg))]
        
        if rawWarnMsg and showWarning:
            console.print("Warning Message from server:\n"+"\n".join(rawWarnMsg))

        if read and multi_run_flag:
            return tz.valmap(deal.read, result)
        elif read:
            return deal.read(result)
        else:
            return result

    def runPool(self, pool, poolAssump=None, rateAssump=None, read=True):
        """perform pool run with pool and rate assumptions

        :param pool: a pool object
        :type pool: object
        :param poolAssump: pool performance assumption, a tuple for single run and a map for multi-scenario run, defaults to None
        :type poolAssump: tuple|dict, optional
        :param rateAssump: a list of interest rate assumptions, default to None
        :type rateAssump: tuple, optional
        :param read: flag to convert result to pandas dataframe, default to True
        :type read: bool, optional
        """
        def read_single(pool_resp):
            (pool_flow, pool_bals) = pool_resp
            result = _read_cf(pool_flow['contents'], self.lang)
            return (result, pool_bals)
            
        multi_scenario = True if isinstance(poolAssump, dict) else False
        url = f"{self.url}/{Endpoints.RunPoolByScenarios.value}" if multi_scenario else f"{self.url}/{Endpoints.RunPool.value}"
        req = self.build_pool_req(pool, poolAssump, rateAssump)
        result = self._send_req(req, url)

        if read and (not multi_scenario):
            return read_single(result)
        elif read and multi_scenario: 
            return mapValsBy(result, read_single)
        else:
            return result
    
    def runStructs(self, deals, poolAssump=None, nonPoolAssump=None, read=True):
        """run multiple deals with same assumption

        :param deals: a dict of deals
        :type deals: dict
        :param poolAssump: _description_, defaults to None
        :type poolAssump: _type_, optional
        :param nonPoolAssump: _description_, defaults to None
        :type nonPoolAssump: _type_, optional
        :param read: _description_, defaults to True
        :type read: bool, optional
        :return: a map of results
        :rtype: dict
        """
        assert isinstance(deals, dict), f"Deals should be a dict but got {type(deals)}"
        url = f"{self.url}/{Endpoints.RunMultiDeal.value}" 
        _poolAssump = mkAssumpType(poolAssump) if poolAssump else None 
        _nonPerfAssump = mkNonPerfAssumps({}, nonPoolAssump)
        req = json.dumps(mkTag(("MultiDealRunReq"
                                 ,[ tz.valmap(lambda x:x.json, deals)
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
        """run asset with assumptions

        :param date: date of start projection and pricing day
        :type date: date
        :param _assets: a list of asset objects
        :type _assets: list
        :param poolAssump: asset performance, defaults to None
        :type poolAssump: tuple, optional
        :param rateAssump: interest rate assumption, defaults to None
        :type rateAssump: tuple, optional
        :param pricing:  princing input for asset, defaults to None
        :type pricing: tuple, optional
        :param read: whether convert raw result to dataframe, defaults to True
        :type read: bool, optional
        :return: result of run
        :rtype: dict | pd.DataFrame
        """
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
        """login to deal library with user and password

            update token attribute if login success
            
        :param user: username
        :type user: string
        :param pw: password
        :type pw: string
        :param q: query parameters:

                    - {"deal_library": <deal library url> }, specify the deal library server;
        :return: None 
        :rtype: None
        """
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.Token.value}"
        cred = {"user": vStr(user), "password": pw}
        r = self._send_req(json.dumps(cred), deal_library_url)
        if 'token' in r:
            console.print(f"✅{MsgColor.Success.value} login successfully, {r['msg']}")
            self.token = r['token']
        else:
            if hasattr(self, 'token'):
                delattr(self, 'token')
            console.print(f"❌{MsgColor.Error.value} Failed to login,{r['msg']}")
            return None
    
    def safeLogin(self, user, **q):
        """safe login with user and password in interactive console

        a interactive input is pending after calling this function

        :param user: username
        :type user: string
        """
        try:
            pw = getpass.getpass()
            self.loginLibrary(user, pw, **q)
        except Exception as e:
            raise AbsboxError(f"❌{MsgColor.Error.value} Failed during library login {e}")

    def queryLibrary(self, ks, **q):
        """query deal library with bond ids

        :param ks: bond Ids
        :type ks: list
        :param q: query parameters:

                    - if {"read":True}, return a dataframe, else return raw result;
        :return: a list of bonds found in library
        :rtype: pd.DataFrame or raw result
        
        """
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌{MsgColor.Error.value} No token found , please call loginLibrary() to login")

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
        """list all available bonds in library

        :param q: query parameters:

                    - if {"read":True}, return a dataframe, else return raw result;
                    - {"deal_library": <deal library url> }, specify the deal library server;
        :type q: dict
        :return: a list of available bonds in library
        :rtype: pd.DataFrame or raw result
        """
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.List.value}"
        result = self._send_req(json.dumps(q), deal_library_url)
        console.print(f"✅{MsgColor.Success.value} list success")
        if ('read' in q) and (q['read'] == True):
            return pd.DataFrame(result['data'], columns=result['header'])
        else:
            return result

    def runLibrary(self, _id, **p):
        """send deal id with assumptions to remote server and get result back

        :param _id: dealId
        :type _id: string
        :param p: run parameters:

                    - {"deal_library": <deal library url> }, specify the deal library server;
                    - {"read":True}, return a dataframe, else return raw result;
                    - {"poolAssump":<pool assumptions>}, specify pool assumptions;
                    - {"dealAssump":<deal assumptions>}, specify deal assumptions;
        :type p: dict
        :raises RuntimeError: _description_
        :return: raw string or dataframe
        :rtype: string | pd.DataFrame
        """
        deal_library_url = p['deal_library']+f"/{LibraryEndpoints.Run.value}"
        read = p.get("read", True)
        dealAssump, poolAssump = tz.get(["dealAssump", "poolAssump"], p, None)
        runType = p.get("runType", "S")
        prod_flag = {"production": p.get("production", True)}

        runReq = mergeStrWithDict(self.build_run_deal_req(runType, _id, poolAssump, dealAssump), prod_flag)
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌{MsgColor.Error.value} No token found, please call loginLibrary() to login")
        
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
            raise AbsboxError(f"❌{MsgColor.Error.value} message from API server:{result},\n,{e}")
        try:       
            classReader = lookupReader(p['reader'])
            if read and isinstance(result, list):
                return classReader.read(result)
            elif read and isinstance(result, dict):
                return tz.valmap(classReader.read, result)  # {k: classReader.read(v) for k, v in result.items()}
            else:
                return result
        except Exception as e:
            raise AbsboxError(f"❌{MsgColor.Error.value}: Failed to read result with error = {e}")

    def _send_req(self, _req, _url: str, timeout=10, headers={})-> dict | None:
        """common function send request to server

        :meta private:
        :param _req: request body
        :type _req: string
        :param _url: engine server url
        :type _url: str
        :param timeout: timeout in seconds, defaults to 10
        :type timeout: int, optional
        :param headers: default request header, defaults to {}
        :type headers: dict, optional
        :return: response in dict
        :rtype: dict | None
        """
        with console.status("") as status:
            try:
                hdrs = self.hdrs | headers
                r = None
                if self.session:
                    r = self.session.post(_url, data=_req.encode('utf-8'), headers=hdrs, verify=False, timeout=timeout)
                else:
                    raise AbsboxError(f"❌: None type for session")
            except (ConnectionRefusedError, ConnectionError):
                raise AbsboxError(f"❌ Failed to talk to server {_url}")
            except ReadTimeout:
                raise AbsboxError(f"❌ Failed to get response from server")
            if r.status_code != 200:
                raise EngineError(r)
            try:
                return json.loads(r.text)
            except JSONDecodeError as e:
                raise EngineError(e)