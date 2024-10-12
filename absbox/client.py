import json, urllib3, getpass, enum, os, pickle
from importlib.metadata import version
from json.decoder import JSONDecodeError
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.exceptions import ConnectionError, ReadTimeout
import pandas as pd
from rich.console import Console
from schema import Schema
import toolz as tz
from lenses import lens


from absbox.validation import isValidUrl, vStr
from absbox.local.util import mkTag,mapValsBy \
                              , _read_cf, _read_asset_pricing, mergeStrWithDict \
                              , earlyReturnNone, searchByFst, filter_by_tags \
                              , enumVals, lmap, inferPoolTypeFromAst, getValWithKs, mapNone
from absbox.local.component import mkPool, mkAssumpType, mkNonPerfAssumps, mkLiqMethod \
                                   , mkAssetUnion, mkRateAssumption, mkDatePattern, mkPoolType

from absbox.local.base import ValidationMsg
from absbox.local.china import SPV
from absbox.local.generic import Generic


VERSION_NUM = version("absbox")
urllib3.disable_warnings()
console = Console()

__all__ = ["API", "Endpoints", "RunReqType", "RunResp", "MsgColor", "LibraryEndpoints","EnginePath"]


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
    RunDealByRunScenarios = "runDealByRunScenarios"
    """Run a single deal with multiple deal run scenarios endpoint"""
    RunByCombo = "runByCombo"
    """Run mulitple sensitivities"""
    RunDate = "runDate"
    """Run Dates from a datepattern """
    Version = "version"
    """Get version of engine server endpoint"""


class RunReqType(str, enum.Enum):
    """Request run type
    """
    Single = "SingleRunReq"
    """ Single Deal With A Single Assumption """
    MultiScenarios = "MultiScenarioRunReq"
    """ Single Deal With Multiple Assumptions """
    MultiRunScenarios = "MultiRunAssumpReq"
    """ Single Deal With Multiple Assumptions """
    MultiStructs = "MultiDealRunReq"
    """ Multiple Deals With Single Assumption """
    SinglePool = "SingleRunPoolReq"
    """ Single Pool With Single Assumption """
    MultiPoolScenarios = "MultiScenarioRunPoolReq"
    """ Single Pool With Multiple Assumptions """
    ComboSensitivity = "MultiComboReq"
    """ Multiple sensitivities """


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
    Data = "data"
    DataList = "data/list"
    DealFetch = "deal/fetch"
    ReportFetch = "data/report"



class LibraryPath(str, enum.Enum):
    """ Enum class representing shortcut to deal library and data service """
    CHINA = "http://absbox.org......."


class EnginePath(str, enum.Enum):
    """ Enum class representing shortcut engine paths for the client.
    """
    LOCAL = "http://localhost:8081"
    """ Use local default server """
    PROD = "https://absbox.org/api/latest"
    DEV = "https://absbox.org/api/dev"
    NY_DEV = "https://spv.run/api/dev"
    NY_PROD = "https://spv.run/api/latest"
    LDN_DEV = "https://ldn.spv.run/api/dev"
    LDN_PROD = "https://ldn.spv.run/api/latest"
    USE_ENV = "USE_ENV"
    """ USE_ENV (str): Use environment variable (`ABSBOX_SERVER`) for engine path """


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


def PickApiFrom(Apilist:list,**kwargs):
    """ Auto init API instance from a list of API urls with version check

    :param Apilist: list of API urls
    :type Apilist: list
    """
    def pingApi(x):
        try:
            r = requests.get(f"{x.value}/{Endpoints.Version.value}", verify=False, timeout=5 ,headers={"Origin":"http://localhost:8001"}).text 
            return json.loads(r) 
        except Exception as e:
            return ("Error",e)

    _,libVersion,_ = VERSION_NUM.split(".")
    
    apiResps = [{"url":api,"resp":pingApi(api)} for api in Apilist ]
    validApis = tz.pipe(apiResps
                    ,lambda apis: list(filter(lambda x:"Error" not in x['resp'],apis))
                    ,lambda apis: lens.Each()['resp']['_version'].modify(lambda x: x.split("."))(apis)
                    ,lambda apis: filter(lambda x:x['resp']['_version'][1]==libVersion, apis) 
                    ,lambda apis: sorted(apis,key=lambda x: x['resp']['_version'][2])
    )

    r = list(validApis)

    if len(r)>0: 
        return API(r[0],**kwargs)
    else:
        raise AbsboxError(f"❌{MsgColor.Error.value}No valid API found in list match current lib version {libVersion}, from list:{apiResps}")


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
        if self.url == EnginePath.USE_ENV.value:
            urlInEnv = os.environ.get("ABSBOX_SERVER")
            if urlInEnv is None:
                raise AbsboxError(f"❌{MsgColor.Error.value}No ABSBOX_SERVER found in environment variable")
            else:
                self.url = isValidUrl(urlInEnv).rstrip("/")
        else:
            self.url = isValidUrl(self.url).rstrip("/")
            
        console.print(f"{MsgColor.Info.value}Connecting engine server -> {self.url}")
        
        if self.lang not in ["chinese", "english"]:
            raise AbsboxError(f"❌{MsgColor.Error.value}Invalid language:{self.lang}, only support 'chinese' or 'english' ")

        try:
            _r = requests.get(f"{self.url}/{Endpoints.Version.value}", verify=False, timeout=5, headers = {"Origin":"http://localhost:8001"}).text
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

        match Schema(str).validate(run_type):
            case "Single" | "S":
                _nonPerfAssump = mkNonPerfAssumps({}, nonPerfAssump)
                _deal = deal.json if hasattr(deal, "json") else deal
                _perfAssump = earlyReturnNone(mkAssumpType, perfAssump)
                r = mkTag((RunReqType.Single.value, [_deal, _perfAssump, _nonPerfAssump]))
            case "MultiScenarios" | "MS":
                _nonPerfAssump = mkNonPerfAssumps({}, nonPerfAssump)
                _deal = deal.json if hasattr(deal, "json") else deal
                mAssump = mapValsBy(perfAssump, mkAssumpType)
                r = mkTag((RunReqType.MultiScenarios.value, [_deal, mAssump, _nonPerfAssump]))
            case "MultiStructs" | "MD" :
                _nonPerfAssump = mkNonPerfAssumps({}, nonPerfAssump)
                mDeal = {k: v.json if hasattr(v, "json") else v for k, v in deal.items()}
                _perfAssump = mkAssumpType(perfAssump)
                r = mkTag((RunReqType.MultiStructs.value, [mDeal, _perfAssump, _nonPerfAssump]))
            case "MultiRunScenarios" | "MRS" if isinstance(nonPerfAssump,dict):
                _deal = deal.json if hasattr(deal, "json") else deal
                _perfAssump = earlyReturnNone(mkAssumpType, perfAssump)
                mRunAssump = mapValsBy(nonPerfAssump, lambda x: mkNonPerfAssumps({}, x))
                r = mkTag((RunReqType.MultiRunScenarios.value, [_deal, _perfAssump, mRunAssump]))
            case "ComboSensitivity" | "CS" if isinstance(nonPerfAssump,dict) and isinstance(perfAssump,dict) and isinstance(deal,dict):
                mDeal = {k: v.json if hasattr(v, "json") else v for k, v in deal.items()}
                mAssump = mapValsBy(perfAssump, mkAssumpType)
                if mAssump == {}:
                    mAssump = {"Empty": None}
                mRunAssump = mapValsBy(nonPerfAssump, lambda x: mkNonPerfAssumps({}, x))
                if mRunAssump == {}:
                    mRunAssump = {"Empty":{}}
                r = mkTag((RunReqType.ComboSensitivity.value, [mDeal, mAssump, mRunAssump]))
            case _:
                raise RuntimeError(f"Failed to match run type:{run_type}")
        try:
            return json.dumps(r, ensure_ascii=False)
        except TypeError as e:
            raise AbsboxError(f"❌Failed to convert request to json:{e}")

    def build_pool_req(self, pool, poolAssump, rateAssumps, isMultiScenario=False) -> str:
        """build pool run request: (single run, multi-scenario run)

        :meta private:
        :param pool: a pool object, could be a single pool or a pool map
        :type pool: _type_
        :param poolAssump: a tuple of pool level assumption(Default/Prepayment/Recovery) for single run. a map indicates multi-scenario run
        :type poolAssump: _type_
        :param rateAssumps: a list of rate assumptions
        :type rateAssumps: _type_
        :raises RuntimeError: _description_
        :return: a string of request body to be sent out to engine
        :rtype: str

        """
        r = None
        _rateAssump = lmap(mkRateAssumption, rateAssumps) if rateAssumps else None
        assetDate = getValWithKs(pool, ['cutoffDate', '封包日'])

        def buildPoolType(p) -> dict:
            """ build type for `PoolTypeWrap` """
            assetTag = inferPoolTypeFromAst(p) if (('assets' in p) or ('清单' in p)) else "UPool"
            _p = tz.dissoc(p, 'cutoffDate')
            if assetTag == "UPool":
                return mkTag((assetTag, mkPoolType(assetDate, _p, True)))
            else:
                return mkTag((assetTag, mkPoolType(assetDate, _p, False)))

        if not isMultiScenario:
            r = mkTag((RunReqType.SinglePool.value, [buildPoolType(pool), mkAssumpType(poolAssump), _rateAssump]))
        else:
            r = mkTag((RunReqType.MultiPoolScenarios.value, [buildPoolType(pool), mapValsBy(poolAssump, mkAssumpType), _rateAssump]))

        return json.dumps(r, ensure_ascii=False)

    def run(self, deal,
            poolAssump=None,
            runAssump=[],
            read=True,
            showWarning=True,
            debug=False) -> dict :
        """ run deal with pool and deal run assumptions

        :param deal: a deal object
        :type deal: Generic | SPV
        :param poolAssump: pool performance assumption, a tuple for single run/ a dict for multi-sceanrio run, defaults to None
        :type poolAssump: tuple, optional
        :param runAssump: deal level assumption, defaults to []
        :type runAssump: list, optional
        :param read: flag to convert result to pandas dataframe, defaults to True
        :type read: bool, optional
        :param showWarning: flag to show warnings, defaults to True
        :type showWarning: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: result of run, a dict of dataframe if `read` is True.
        :rtype: dict

        """        

        if (not isinstance(poolAssump, tuple)) and (poolAssump is not None):
            raise AbsboxError(f"❌{MsgColor.Error.value} poolAssump should be a tuple but got {type(poolAssump)}")


        # if run req is a multi-scenario run
        url = f"{self.url}/{Endpoints.RunDeal.value}"

        # construct request
        req = self.build_run_deal_req("Single", deal, poolAssump, runAssump)
        if debug:
            return req
        # branching with pricing
        if runAssump is None or searchByFst(runAssump, "pricing") is None:
            result = self._send_req(req, url)
        else:
            result = self._send_req(req, url, timeout=30)

        if result is None or 'error' in result:
            raise AbsboxError(f"❌{MsgColor.Error.value}Failed to get response from run")

        rawWarnMsg = map( lambda x:f"{MsgColor.Warning.value}{x['contents']}", filter_by_tags(result[RunResp.LogResp.value], enumVals(ValidationMsg)))
        if rawWarnMsg and showWarning:
            console.print("Warning Message from server:\n"+"\n".join(list(rawWarnMsg)))

        if read:
            return deal.read(result)
        else:
            return result

    def runByScenarios(self, deal,
                    poolAssump=None,
                    runAssump=[],
                    read=True,
                    showWarning=True,
                    debug=False) -> dict :
        """ run deal with multiple scenarios, return a map

        :param deal: _description_
        :type deal: _type_
        :param poolAssump: _description_, defaults to None
        :type poolAssump: dict, optional
        :param runAssump: _description_, defaults to []
        :type runAssump: list, optional
        :param read: if read response into dataframe, defaults to True
        :type read: bool, optional
        :param showWarning: if show warning messages from server, defaults to True
        :type showWarning: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: a dict with scenario names as keys
        :rtype: dict        
        """

        url = f"{self.url}/{Endpoints.RunDealByScnearios.value}"
        req = self.build_run_deal_req("MultiScenarios", deal, poolAssump, runAssump)

        if debug:
            return req

        if runAssump is None or searchByFst(runAssump, "pricing") is None:
            result = self._send_req(req, url)
        else:
            result = self._send_req(req, url, timeout=30)

        if result is None or 'error' in result:
            raise AbsboxError(f"❌{MsgColor.Error.value}Failed to get response from run")

        rawWarnMsgByScen = {k: [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(v[RunResp.LogResp.value], enumVals(ValidationMsg))] for k, v in result.items()}
        rawWarnMsg = list(tz.concat(rawWarnMsgByScen.values()))
        
        if showWarning and len(rawWarnMsg)>0:
            console.print("Warning Message from server:\n"+"\n".join(rawWarnMsg))

        if read:
            return tz.valmap(deal.read, result)
        else:
            return result

    def read_single(self, pool_resp) -> tuple:
        """ read pool run response from engine and convert to dataframe

        :param pool_resp: (pool raw cashflow, pool statistics)
        :type pool_resp: tuple
        :return: (pool Cashflow in dataFrame, pool statistics)
        :rtype: tuple
        """
        (pool_flow, pool_bals) = pool_resp
        result = _read_cf(pool_flow['contents'][1], self.lang)
        return (result, pool_bals)


    def runPoolByScenarios(self, pool, poolAssump, rateAssump=None, read=True, debug=False) -> dict :
        """ run a pool with multiple scenario ,return result as map , with key same to pool assumption map

        :param pool: pool map
        :type pool: dict
        :param poolAssump: assumption map
        :type poolAssump: dict
        :param rateAssump: _description_, defaults to None
        :type rateAssump: _type_, optional
        :param read: if read response into dataframe, defaults to True
        :type read: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: a dict with scenario names as keys
        :rtype: dict
        """

        url = f"{self.url}/{Endpoints.RunPoolByScenarios.value}"
        req = self.build_pool_req(pool, poolAssump, rateAssump, isMultiScenario=True)

        if debug:
            return req

        result = self._send_req(req, url)

        if read:
            return result & lens.Values().Values().modify(self.read_single)
        return result

    def runPool(self, pool, poolAssump=None, rateAssump=None, read=True, debug=False, **kwargs) -> tuple:
        """perform pool run with pool and rate assumptions

        :param pool: a pool object
        :type pool: object
        :param poolAssump: pool performance assumption, a tuple for single run and a map for multi-scenario run, defaults to None
        :type poolAssump: tuple
        :param rateAssump: a list of interest rate assumptions, default to None
        :type rateAssump: tuple, optional
        :param read: flag to convert result to pandas dataframe, default to True
        :type read: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: tuple of cashflow and pool statistics
        :rtype: tuple
        """

        if (not isinstance(poolAssump, tuple)) and (poolAssump is not None):
            raise AbsboxError(f"❌{MsgColor.Error.value} poolAssump should be a tuple but got {type(poolAssump)}")

        url = f"{self.url}/{Endpoints.RunPool.value}"

        req = self.build_pool_req(pool, poolAssump, rateAssump, isMultiScenario=False)

        if debug:
            return req

        result = self._send_req(req, url, **kwargs)

        if read:
            return result & lens.Values().modify(self.read_single)
        else:
            return result

    def runStructs(self, deals, poolAssump=None, nonPoolAssump=None, runAssump=None, read=True, debug=False) -> dict:
        """run multiple deals with same assumption

        :param deals: a dict of deals
        :type deals: dict
        :param poolAssump: _description_, defaults to None
        :type poolAssump: _type_, optional
        :param nonPoolAssump: _description_, defaults to None
        :type nonPoolAssump: _type_, optional
        :param runAssump: _description_, defaults to None
        :type runAssump: _type_, optional
        :param read: _description_, defaults to True
        :type read: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: a map of results
        :rtype: dict
        """
        assert isinstance(deals, dict), f"Deals should be a dict but got {type(deals)}"

        url = f"{self.url}/{Endpoints.RunMultiDeal.value}" 
        _poolAssump = mkAssumpType(poolAssump) if poolAssump else None 
        _nonPerfAssump = mkNonPerfAssumps({}, mapNone(nonPoolAssump,[]) + mapNone(runAssump,[]))
        req = json.dumps(mkTag(("MultiDealRunReq"
                                 ,[ tz.valmap(lambda x:x.json, deals)
                                   ,_poolAssump
                                   ,_nonPerfAssump]))
                         ,ensure_ascii=False)

        if debug:
            return req
        result = self._send_req(req, url)
        if read:
            return {k: deals[k].read(v) for k, v in result.items()}    
        else:
            return result

    def runByDealScenarios(self, deal,
                    poolAssump=None,
                    runAssump={},
                    read=True,
                    showWarning=True,
                    debug=False) -> dict :
        """ run deal with multiple run assumption, return a map

        :param deal: _description_
        :type deal: _type_
        :param poolAssump: _description_, defaults to None
        :type poolAssump: dict, optional
        :param runAssump: _description_, defaults to {}
        :type runAssump: dict
        :param read: if read response into dataframe, defaults to True
        :type read: bool, optional
        :param showWarning: if show warning messages from server, defaults to True
        :type showWarning: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: a dict with scenario names as keys
        :rtype: dict        
        """

        url = f"{self.url}/{Endpoints.RunDealByRunScenarios.value}"
        req = self.build_run_deal_req("MRS", deal, poolAssump, runAssump)

        if debug:
            return req

        result = self._send_req(req, url, timeout=30)

        if result is None or 'error' in result:
            raise AbsboxError(f"❌{MsgColor.Error.value}Failed to get response from run")

        rawWarnMsgByScen = {k: [f"{MsgColor.Warning.value}{_['contents']}" for _ in filter_by_tags(v[RunResp.LogResp.value], enumVals(ValidationMsg))] for k, v in result.items()}
        rawWarnMsg = list(tz.concat(rawWarnMsgByScen.values()))
        
        if showWarning and len(rawWarnMsg)>0:
            console.print("Warning Message from server:\n"+"\n".join(rawWarnMsg))

        if read:
            return tz.valmap(deal.read, result)
        else:
            return result

    def runByCombo(self, 
                    dealMap, 
                    poolAssump={}, 
                    runAssump={}, 
                    read=True, showWarning=True, debug=False) -> dict:
        """ run mulitple deals with multiple pool assumption/ with multiple run assumption, return a map 
        
        :param dealMap: a dict of deals
        :type dealMap: _type_
        :param poolAssump: a dict of pool assumptions, defaults to {}
        :type poolAssump: dict, optional
        :param runAssump: a dict of run assumptions, defaults to {}
        :type runAssump: dict, optional
        :param read: if read response into dataframe, defaults to True
        :type read: bool, optional
        :param showWarning: if show warning messages from server, defaults to True
        :type showWarning: bool, optional
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        """

        url = f"{self.url}/{Endpoints.RunByCombo.value}"

        if len(dealMap) == 0:
            raise AbsboxError(f"❌{MsgColor.Error.value}No deals found in dealMap,at least one deal is required")

        if "^" in " ".join(tz.concatv(dealMap.keys(),poolAssump.keys(),runAssump.keys())):
            raise AbsboxError(f"❌{MsgColor.Error.value}Deal name should not contain '^' ")

        req = self.build_run_deal_req("CS", dealMap, poolAssump, runAssump)

        if debug:
            return req
        
        result = self._send_req(req, url, timeout=30)

        if result is None or 'error' in result or result == []:
            raise AbsboxError(f"❌{MsgColor.Error.value}Failed to get response from run, but got {result}")

        assert isinstance(result, dict), f"Result should be a dict but got {type(result)}, {result}"

        rawWarnMsgByScen = {"^".join(k): [f"{MsgColor.Warning.value}{_['contents']}" 
                                for _ in filter_by_tags(v[RunResp.LogResp.value], enumVals(ValidationMsg))] 
                                    for k, v in result.items()}

        rawWarnMsg = list(tz.concat(rawWarnMsgByScen.values()))
        
        if showWarning and len(rawWarnMsg)>0:
            console.print("Warning Message from server:\n"+"\n".join(rawWarnMsg))

        if read:
            return {
                tuple(k.split("^")): dealMap[k.split("^")[0]].read(v) for k,v in result.items()
            }
        else:
            return result


    def runAsset(self, date, _assets, poolAssump=None, rateAssump=None
                 , pricing=None, read=True, debug=False) -> tuple:
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
        :param debug: return request text instead of sending out such request, defaults to False
        :type debug: bool, optional
        :return: (cashflow, balance, pricing result)
        :rtype: tuple
        """
        assert isinstance(_assets, list), f"Assets passed in must be a list"
        
        def readResult(x):
            try:
                ((cfs, cfBalance), pr) = x
                cfs = _read_cf(cfs['contents'][1], self.lang)
                pricingResult = _read_asset_pricing(pr, self.lang) if pr else None
                return (cfs, cfBalance, pricingResult)
            except Exception as e:
                print(f"Failed to read result {x} \n with error {e}")
                return (None, None, None)
            
        url = f"{self.url}/{Endpoints.RunAsset.value}"
        _assumptions = mkAssumpType(poolAssump) if poolAssump else None
        _rate = lmap(mkRateAssumption, rateAssump) if rateAssump else None
        _pricing = mkLiqMethod(pricing) if pricing else None
        assets = lmap(mkAssetUnion, _assets) 
        req = json.dumps([date, assets, _assumptions, _rate, _pricing]
                         , ensure_ascii=False)
        if debug:
            return req
        
        result = self._send_req(req, url)
        if read:
            return readResult(result)
        else:
            return result

    def runDates(self, d, dp, eDate=None):
        """generate a list of dates from date pattern

        :param d: a starting date
        :type d: date
        :param dp: a date pattern
        :type dp: date pattern
        :return: a list of dates
        :rtype: list[date]
        """
        url = f"{self.url}/{Endpoints.RunDate.value}"
        req = json.dumps([d, mkDatePattern(dp), eDate], ensure_ascii=False)
        result = self._send_req(req, url)
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
                    - {"runAssump":<deal assumptions>}, specify run assumptions;
        :type p: dict
        :raises RuntimeError: _description_
        :return: raw string or dataframe
        :rtype: string | pd.DataFrame
        """
        deal_library_url = p['deal_library']+f"/{LibraryEndpoints.Run.value}"
        read = p.get("read", True)
        dealAssump, poolAssump = tz.get(["runAssump", "poolAssump"], p, None)
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

    def listLibraryData(self, **q):
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.DataList.value}"
        result = self._send_req(json.dumps(q), deal_library_url)
        console.print(f"✅{MsgColor.Success.value} list success")
        if ('read' in q) and (q['read'] == True):
            return pd.DataFrame(result['data'], columns=result['header'])
        else:
            return result


    def fetchLibraryData(self, **q):
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.ReportFetch.value}"
        hdrs = self.hdrs | {"Authorization": f"Bearer {self.token}"}
        # fetch type
        ## by single bond id
        ## by deal id 
        ## by series name

        ## filter ,date range

        result = self._send_req(json.dumps(q), deal_library_url, headers=hdrs)
        console.print(f"✅{MsgColor.Success.value} fetch success")
        
        return result
    
    def fetchLibraryDeal(self, **q):
        deal_library_url = q['deal_library']+f"/{LibraryEndpoints.DealFetch.value}"
        hdrs = self.hdrs | {"Authorization": f"Bearer {self.token}"}
        r = None
        if self.session:
            r = self.session.post(deal_library_url, data=json.dumps(q).encode('utf-8'), headers=hdrs, verify=False, timeout=15)
            if r.status_code != 200:
                raise AbsboxError(f"❌{MsgColor.Error.value}Failed to fetch deal from library")
            return pickle.loads(r.content)


    def _send_req(self, _req, _url: str, timeout=10, headers={})-> dict | None:
        """generic function send request to server

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
