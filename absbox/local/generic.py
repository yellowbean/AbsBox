from dataclasses import dataclass
import functools

from absbox import *
from absbox.local.util import mkTag
from absbox.local.component import *
from absbox.local.base import * 
import pandas as pd
import collections


@dataclass
class Generic:
    name: str
    dates: dict
    pool: dict
    accounts: tuple
    bonds: tuple
    fees: tuple
    waterfall: dict
    collection: list
    call: tuple = None 
    liqFacility :dict = None
    custom: dict = None 
    trigger:dict = None
    status:str = "Amortizing"

    @property
    def json(self):
        dists,collects,cleans = [ self.waterfall.get(wn,[]) for wn in ['Normal','PoolCollection','CleanUp']]
        distsAs,collectsAs,cleansAs = [ [ mkWaterfall2(_action) for _action in _actions] for _actions in [dists,collects,cleans] ]
        distsflt,collectsflt,cleanflt = [ itertools.chain.from_iterable(x) for x in [distsAs,collectsAs,cleansAs] ]
        parsedDates = mkDate(self.dates)
        """
        get the json formatted string
        """
        _r = {
            "dates": parsedDates,
            "name": self.name,
            "status":mkTag((self.status)),
            "pool": {"assets": [mkAsset(x) for x in self.pool.get('assets', [])]
                     , "asOfDate": self.dates['cutoff']
                     , "issuanceStat": self.pool.get("issuanceStat")
                     , "futureCf":mkCf(self.pool.get('cashflow', [])) },
            "bonds": functools.reduce(lambda result, current: result | current
                                      , [mk(['bond', bn, bo]) for (bn, bo) in self.bonds]),
            "waterfall": mkWaterfall({},self.waterfall.copy()),  
            "fees": functools.reduce(lambda result, current: result | current
                                     , [mk(["fee", feeName, feeO]) for (feeName, feeO) in self.fees]) if self.fees else {},
            "accounts": functools.reduce(lambda result, current: result | current
                                         , [mk(["account", accName, accO]) for (accName, accO) in self.accounts]),
            "collects": self.collection
        }
        for fn, fo in _r['fees'].items():
            if fo['feeStart'] is None:
                fo['feeStart'] = self.dates['closing']

        if hasattr(self, "custom") and self.custom is not None:
            _r["custom"] = {}
            for n,ci in self.custom.items():
                _r["custom"][n] = mkCustom(ci)
        
        if hasattr(self, "trigger") and self.trigger is not None:
            _trigger  = self.trigger
            _trr = {mkWhenTrigger(_loc):
                       [[mkTrigger(_trig),mkTriggerEffect(_effect)] for (_trig,_effect) in _vs ] 
                       for _loc,_vs in _trigger.items()}
            _r["triggers"] = _trr
        
        if hasattr(self, "liqFacility") and self.liqFacility is not None:
            _providers = {}
            for (_k, _p) in self.liqFacility.items():
                _providers[_k] = mkLiqProvider(_k, ( _p | {"start": self.dates['closing']}))
            _r["liqProvider"] = _providers

        _dealType = identify_deal_type(_r)

        return mkTag((_dealType,_r))

    def read_assump(self, assump):
        if assump:
            return [mkAssumption(a) for a in assump]
        return None

    def read_pricing(self, pricing):
        if pricing:
            return mkPricingAssump(pricing)
        return None

    def read(self, resp, position=None):
        read_paths = {'bonds': ('bndStmt' , english_bondflow_fields , "bond")
                     , 'fees': ('feeStmt' , english_fee_flow_fields_d , "fee")
                     , 'accounts': ('accStmt' , english_acc_flow_fields_d , "account")}
        output = {}
        for comp_name, comp_v in read_paths.items():
            output[comp_name] = {}
            for k, x in resp[0][comp_name].items():
                ir = None
                if x[comp_v[0]]:
                    ir = [_['contents'] for _ in x[comp_v[0]]]
                output[comp_name][k] = pd.DataFrame(ir, columns=comp_v[1]).set_index("date")
            output[comp_name] = collections.OrderedDict(sorted(output[comp_name].items()))
        # aggregate fees
        output['fees'] = {f: v.groupby('date').agg({"balance": "min", "payment": "sum", "due": "min"})
                          for f, v in output['fees'].items()}

        # aggregate accounts
        output['agg_accounts'] = aggAccs(output['accounts'], 'en')

        output['pool'] = {}
        _pool_cf_header,_ = guess_pool_flow_header(resp[0]['pool']['futureCf'][0],"english")
        output['pool']['flow'] = pd.DataFrame([_['contents'] for _ in resp[0]['pool']['futureCf']]
                                              , columns=_pool_cf_header)
        pool_idx = 'Date'
        output['pool']['flow'] = output['pool']['flow'].set_index(pool_idx)
        output['pool']['flow'].index.rename(pool_idx, inplace=True)

        output['pricing'] = readPricingResult(resp[3], 'en')
        output['result'] = readRunSummary(resp[2], 'en')

        return output
