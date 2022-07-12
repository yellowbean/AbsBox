import json,datetime
import requests
from dataclasses import dataclass



@dataclass
class client:
    url: str
    server_info = {}
    version:str = "0.0.1"

    def __post_init__(self):
        _r = requests.get(f"{self.url}/info").text
        echo = json.loads(_r)
        self.server_info = echo
        supported_client_versions = echo['support_version']
        print(f"Connect Successfully with engine version {echo['version']},which support client version {supported_client_versions}")
        if self.version not in supported_client_versions:
            print(f"Failed to init the client , pls upgrade your client package by: pip -U pyabs")
            return


    def run(self, deal, assumption=None, custom_endpoint=None):
        url = None
        if custom_endpoint:
            url = f"{self.url}/{custom_endpoint}"
        else:
            url = f"{self.url}/run_deal2"
        _req = {
            "deal":None,
            "assump":None
        }
        r = requests.post(url, json.dumps(_req)).text
        return json.loads(r)


