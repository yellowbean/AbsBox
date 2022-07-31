import json,datetime,logging,pickle
from json.decoder import JSONDecodeError
import requests
from requests.exceptions import ConnectionError
import orjson
from dataclasses import dataclass
#from dataclasses_json import dataclass_json


@dataclass
class API:
    url: str
    server_info = {}
    version:str = "0.0.1"

    def __post_init__(self):
        try:
            _r = requests.get(f"{self.url}/version",verify=False).text
        except (ConnectionRefusedError, ConnectionError):
            print(f"Error: Can't not connect to API server {self.url}")
            self.url = None
            return

        echo = json.loads(_r)
        self.server_info = echo
        supported_client_versions = echo['version']
        logging.info(f"Connect Successfully with engine version {echo['version']},which support client version {supported_client_versions}")
        if self.version != supported_client_versions:
            logging.error(f"Failed to init the api instance, lib support={self.version} but server version={echo['version']} , pls upgrade your api package by: pip -U absbox")
            return

    def build_req(self
                  ,deal
                  ,assumptions
                  ,pricing):
        return json.dumps({"deal": deal.json
                       ,"assump": deal.read_assump(assumptions)
                       ,"bondPricing": deal.read_pricing(pricing)}
                   , ensure_ascii=False)

    def run(self,
            deal,
            assumptions=None,
            pricing=None,
            custom_endpoint=None,
            read=True):
        if custom_endpoint:
            url = f"{self.url}/{custom_endpoint}"
        else:
            url = f"{self.url}/run_deal2"

        hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        if isinstance(deal, str):
            with open( deal ,'rb') as _f:
                c = _f.read()
                deal = pickle.loads(c)

        req = self.build_req(deal,assumptions,pricing)
        try:
            r = requests.post(url
                              , data=req.encode('utf-8')
                              , headers=hdrs
                              , verify=False)
        except (ConnectionRefusedError, ConnectionError):
            return None

        if r.status_code != 200:
            print("Error in response:",r.text)
            return None

        try:
            result = json.loads(r.text)
        except JSONDecodeError as e:
            return e

        if read:
            return deal.read(result)
        else:
            return result

def save(deal,p:str):
    def save_to(b):
        with open(p,'wb') as _f:
            _f.write(b)

    match deal:
        case _:
            save_to(pickle.dumps(deal))


