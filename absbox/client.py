import json,datetime,logging
import requests
from dataclasses import dataclass

@dataclass
class API:
    url: str
    server_info = {}
    version:str = "0.0.1"

    def __post_init__(self):
        _r = requests.get(f"{self.url}/version",verify=False).text
        echo = json.loads(_r)
        self.server_info = echo
        supported_client_versions = echo['version']
        logging.info(f"Connect Successfully with engine version {echo['version']},which support client version {supported_client_versions}")
        if self.version != supported_client_versions:
            logging.error(f"Failed to init the api instance, lib support={self.version} but server version={echo['version']} , pls upgrade your api package by: pip -U absbox")
            return


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
        req = json.dumps({"deal": deal.json
                         ,"assump": deal.read_assump(assumptions)
                         ,"bondPricing": deal.read_pricing(pricing)}
                     , ensure_ascii=False)
        r = requests.post(url
                          , data=req.encode('utf-8')
                          , headers=hdrs
                          , verify=False)
        result = json.loads(r.text)
        if read:
            return deal.read(result)
        else:
            return result




