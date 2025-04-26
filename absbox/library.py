from dataclasses import dataclass
from datetime import datetime
import pickle
from rich.console import Console
from rich import print_json
import enum
import getpass ,json
import pandas as pd
from .exception import *
import requests
import toolz as tz

from requests.exceptions import ReadTimeout
from json import JSONDecodeError

from .client import VERSION_NUM
from .local.generic import Generic

console = Console()

from .validation import vStr

__all__ = ["LibraryEndpoints",]

class LibraryEndpoints(str, enum.Enum):
    """Endpoints for deal library"""
    Ack = "ack"
    Token = "token"
    Query = "query"
    Run = "run" # run a deal from the library
    Add = "add" # add new deal to library
    Cmd = "cmd" # add new deal to library
    Get = "get" # get deal from library


class LibraryPath(str, enum.Enum):
    """ Enum class representing shortcut to deal library and data service """
    LDN = "https://ldn.spv.run/api"


@dataclass
class LIBRARY:
    """ Deal Library class for deal library operations 
    :return: Deal Library instance
    :rtype: DealLibrary
    """
    url: str = ""
    token = None
    hdrs = {'Content-type': 'application/json', 'Accept': '*/*', 'Accept-Encoding': 'gzip'}
    debug = False
    libraryInfo = None
    session = None

    def __post_init__(self):

        try:
            _r = requests.post(f"{self.url}/ack", verify=False)
        except Exception as e:
            raise AbsboxError(f"❌ Failed to connect to library server:{e}")
        if _r.status_code == 200:
            self.session = requests.Session()
            self.libraryInfo = json.loads(_r.text)
            console.print(f"✅ Connected to library server")
            console.print(f"absbox version:{self.libraryInfo['absbox']}")
            console.print(f"Hastructure:{self.libraryInfo['Hastructure']}")
        else:
            console.print(f"❌ Failed to connect to library server")

    def login(self, user, pw, **q):
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
        deal_library_url = self.url+f"/{LibraryEndpoints.Token.value}"
        cred = {"user": vStr(user), "password": pw}
        r:dict = self._send_req(json.dumps(cred), deal_library_url)
        if 'token' in r:
            console.print(f"✅ login successfully, user -> {r['user']},group -> {r['group']}")
            self.token = r['token']
        else:
            if hasattr(self, 'token'):
                delattr(self, 'token')
            console.print(f"❌ Failed to login,{r['msg']}")
            return None
    
    def ack(self):
        """acknowledge library connection

        :return: library information
        :rtype: dict
        """
        return self._send_req("", f"{self.url}/ack")

    def safeLogin(self, user, **q):
        """safe login with user and password in interactive console

        a interactive input is pending after calling this function

        :param user: username
        :type user: string
        """
        try:
            pw = getpass.getpass(prompt=f"Enter your deal library password for {user}:")
            self.login(user, pw, **q)
        except Exception as e:
            raise AbsboxError(f"❌ Failed during library login {e}")

    def query(self, k = {}, read=True):
        """query deal library with bond ids

        :param ks: bond Ids
        :type ks: list
        :param q: query parameters:

                    - if {"read":True}, return a dataframe, else return raw result;
        :return: a list of bonds found in library
        :rtype: pd.DataFrame or raw result
        
        """
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌ No token found , please call loginLibrary() to login")

        deal_library_url = self.url+f"/{LibraryEndpoints.Query.value}"
        result = self._send_req(json.dumps({"q":k}), deal_library_url, headers={"Authorization": f"Bearer {self.token}"})
        console.print(f"✅ query success")
        if read:
            if 'data' in result:
                return pd.DataFrame(result['data'], columns=result['header'])
            elif 'error' in result:
                return pd.DataFrame([result["error"]], columns=["error"])
        else:
            return result

    def add(self, d, **p):
        """add deal to library"""

        if not hasattr(self, "token"):
            raise AbsboxError(f"❌ No token found, please call login() to login")
        deal_library_url = self.url+f"/{LibraryEndpoints.Add.value}"

        data = {
            "deal":d
            ,"json": d.json
            ,"buildVersion": VERSION_NUM
            ,"name": d.name
            ,"version": p.get("version",0)
            ,"period": p.get("period",0)
            ,"stage": p.get("stage","draft")
            ,"comment": p.get("comment","")
            ,"permission": p.get("permission","700")
            ,"tags": p.get("tags",[])
            ,"group": p.get("group","")
        }

        bData = pickle.dumps(data)

        r = self._send_req(bData, deal_library_url
                            , headers={"Authorization": f"Bearer {self.token}"
                                        ,"Content-Type":"application/octet-stream"})

        console.print(f"✅ add success with deal id={r['dealId']}, name={r['name']}")

    def cmd(self, p):
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌ No token found, please call login() to login")

        deal_library_url = self.url+f"/{LibraryEndpoints.Cmd.value}"

        r = self._send_req(pickle.dumps(p), deal_library_url,headers={"Authorization": f"Bearer {self.token}"} )

        return r

    def get(self, q):
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌ No token found, please call login() to login")
        deal_library_url = self.url+f"/{LibraryEndpoints.Get.value}"

        r = self._send_req(pickle.dumps({"q":q}), deal_library_url
                            , headers={"Authorization": f"Bearer {self.token}"
                                        ,"Content-Type":"application/octet-stream"})
        
        return r
        console.print(f"✅ get deal success")

    def run(self, _id, **p):
        """send deal id with assumptions to remote server and get result back

        :param _id: how to find a deal in library database
        :type _id: dict
        :param p: run parameters:
                    - {"read":True}, return a dataframe, else return raw result;
                    - {"poolAssump":<pool assumptions>}, specify pool assumptions;
                    - {"runAssump":<deal assumptions>}, specify run assumptions;
        :type p: dict
        :raises RuntimeError: _description_
        :return: raw string or dataframe
        :rtype: string | pd.DataFrame
        """
        if not hasattr(self, "token"):
            raise AbsboxError(f"❌ No token found, please call login() to login")

        deal_library_url = self.url+f"/{LibraryEndpoints.Run.value}"
        read = p.get("read", True)
        
        runAssump, poolAssump = tz.get(["runAssump", "poolAssump"], p, None)
        runType = p.get("runType", "S")

        runReq = {"q": _id, "runType": runType 
                ,"runAssump": runAssump, "poolAssump": poolAssump
                ,"engine": p.get("engine",None) }
        
        bRunReq = pickle.dumps(runReq)

        r = self._send_req(bRunReq, deal_library_url
                            , headers={"Authorization": f"Bearer {self.token}"
                                        ,"Content-Type":"application/octet-stream"})
        if 'error' in r:
            raise AbsboxError(f"❌ error from server:{r['error']}")
        try:
            result = r['result']
            runInfo = tz.dissoc(r, 'result')
            console.print(f"✅ run success with deal: {runInfo['deal']['name']}|{runInfo['deal']['id']}")
        except Exception as e:
            raise AbsboxError(f"❌ message from API server:\n,{e}")
        try:       
            if read and isinstance(result, list):
                return (runInfo, Generic.read(result))
            elif read and isinstance(result, dict):
                return (runInfo, tz.valmap(Generic.read, result))
            else:
                return (runInfo, result)
        except Exception as e:
            raise AbsboxError(f"❌ Failed to read result with error = {e}")


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
            if self.session and not isinstance(_req, bytes):
                r = self.session.post(_url, data=_req.encode('utf-8'), headers=hdrs, verify=False, timeout=timeout)
            elif self.session :
                r = self.session.post(_url, data=_req, headers=hdrs, verify=False, timeout=timeout)
            else:
                raise AbsboxError(f"❌ None type for session")
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
