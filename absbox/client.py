import json,datetime,logging,pickle
from json.decoder import JSONDecodeError
import requests
from requests.exceptions import ConnectionError
from dataclasses import dataclass
#from dataclasses_json import dataclass_json

def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName }

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
        if any(isinstance(i, list) for i in assumptions):
        #if isinstance(assumptions,list):
            return json.dumps({"_deal": deal.json
                       ,"_assump": mkTag(("Multiple"
                                          ,[ deal.read_assump(a) for a in assumptions ]))
                       ,"_bondPricing": deal.read_pricing(pricing)}
                   , ensure_ascii=False)

        return json.dumps({"deal": deal.json
                       ,"assump": deal.read_assump(assumptions)
                       ,"bondPricing": deal.read_pricing(pricing)}
                   , ensure_ascii=False)

    def validate(self, _r):
        error = []
        warning = []
        _r = json.loads(_r)
        _d = _r['deal']
        valid_acc = set(_d['accounts'].keys())
        valid_bnd = set(_d['bonds'].keys())
        valid_fee = set(_d['fees'].keys())
        _w = _d['waterfall']
        for wn,wa in _w.items():
            for idx,action in enumerate(wa):
                #print(action)
                match action['tag']:
                    case 'PayFeeBy':
                        if (not set(action['contents'][1]).issubset(valid_acc)) \
                            or (not set(action['contents'][2]).issubset(valid_fee)):
                            error.append(f"{wn},{idx}")
                    case 'PayFee':
                        if (not set(action['contents'][0]).issubset(valid_acc)) \
                            or (not set(action['contents'][1]).issubset(valid_fee)):
                            error.append(f"{wn},{idx}")     
                    case 'PayInt':
                        if (action['contents'][0] not in valid_acc) \
                            or (not set(action['contents'][1]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")  
                    case 'PayPrin':
                        if (action['contents'][0] not in valid_acc) \
                            or (not set(action['contents'][1]).issubset(valid_bnd)):
                            error.append(f"{wn},{idx}")  
                    case 'PayResidual':
                        if (action['contents'][1] not in valid_acc) \
                            or (action['contents'][2] not in valid_bnd):
                            error.append(f"{wn},{idx}")  
                    case 'Transfer':
                        if (action['contents'][0] not in valid_acc) \
                            or (action['contents'][1] not in valid_acc):
                            error.append(f"{wn},{idx}")
                    case 'TransferBy':
                        if (action['contents'][0] not in valid_acc) \
                            or (action['contents'][1] not in valid_acc):
                            error.append(f"{wn},{idx}")
                    case 'PayTillYield':
                        if (action['contents'][0] not in valid_acc) \
                            or (action['contents'][1] not in valid_bnd):
                            error.append(f"{wn},{idx}")
                    case 'PayFeeResidual':
                        if (action['contents'][1] not in valid_acc) \
                            or (action['contents'][2] not in valid_fee):
                            error.append(f"{wn},{idx}")        
        _d = _r['deal']['dates']
        if _d['closing-date'] >= _d['first-pay-date']:
            error.append(f"dates,first pay date/next pay date should be after closing date")
        if _d['cutoff-date'] >= _d['first-pay-date']:
            error.append(f"dates,first pay date/next pay date should be after cutoff date")

        if len(error)>0:
            return False,error,warning
        else:
            return True,error,warning


    def run(self,
            deal,
            assumptions=None,
            pricing=None,
            custom_endpoint=None,
            read=True,
            position=None,
            timing=False):
        multi_run_flag = any(isinstance(i, list) for i in assumptions)
        if custom_endpoint:
            url = f"{self.url}/{custom_endpoint}"
        else:
            if multi_run_flag:
                url = f"{self.url}/run_deal"
            else:
                url = f"{self.url}/run_deal2"

        hdrs = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        if isinstance(deal, str):
            with open(deal,'rb') as _f:
                c = _f.read()
                deal = pickle.loads(c)


        req = self.build_req(deal,assumptions,pricing)

        #validate deal
        deal_validate,err,warn = self.validate(req)
        if not deal_validate:
            return deal_validate,err,warn

        try:
            print("sending req",datetime.datetime.now())
            r = requests.post(url
                              , data=req.encode('utf-8')
                              , headers=hdrs
                              , verify=False)
            print("done req",datetime.datetime.now())
        except (ConnectionRefusedError, ConnectionError):
            return None

        if r.status_code != 200:
            print("Error in response:",r.text)
            return None

        try:
            result = json.loads(r.text)
        except JSONDecodeError as e:
            return e

        t_reading_s = datetime.datetime.now()
        if read:
            if multi_run_flag:
                __r = [ deal.read(_r,position=position) for _r in result ]
            else:
                __r = deal.read(result,position=position)
            t_reading_e = datetime.datetime.now()
            return __r
        else:
            return result


def save(deal,p:str):
    def save_to(b):
        with open(p,'wb') as _f:
            _f.write(b)

    match deal:
        case _:
            save_to(pickle.dumps(deal))


