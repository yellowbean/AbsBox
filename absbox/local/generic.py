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
    liqFacility :dict = None
    rateSwap:dict = None
    currencySwap:dict = None
    trigger:dict = None
    status:str = "Amortizing"
    custom: dict = None

    @property
    def json(self):
        dists,collects,cleans = [ self.waterfall.get(wn,[]) for wn in ['Normal','PoolCollection','CleanUp']]
        distsAs,collectsAs,cleansAs = [ [ mkWaterfall2(_action) for _action in _actions] for _actions in [dists,collects,cleans] ]
        distsflt,collectsflt,cleanflt = [ itertools.chain.from_iterable(x) for x in [distsAs,collectsAs,cleansAs] ]
        parsedDates = mkDate(self.dates)
        closingDate = self.dates['closing']
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
            "bonds": { bn: mkBnd(bn,bo) for (bn,bo) in self.bonds},
            "waterfall": mkWaterfall({},self.waterfall.copy()),  
            "fees": {fn: mkFee(fo|{"name":fn},fsDate = closingDate) 
                                 for (fn,fo) in self.fees},
            "accounts": {an:mkAcc(an,ao) for (an,ao) in self.accounts},
            "collects": self.collection,
            "rateSwap": { k:mkRateSwap(v) for k,v in self.currencySwap.items()} if self.rateSwap else None,
            "currencySwap":None ,
            "custom": {cn:mkCustom(co) for cn,co in self.custom.items()} if self.custom else None ,
            "triggers": {mkWhenTrigger(tWhen):[[mkTrigger(_trg),mkTriggerEffect(_effect)] 
                                                 for (_trg,_effect) in trgs ]
                            for tWhen,trgs in self.trigger.items()} if self.trigger else None,
            "liqProvider": {ln: mkLiqProvider(ln, lo | {"start":closingDate} ) 
                               for ln,lo in self.liqFacility.items() } if self.liqFacility else None
        }

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
                     , 'accounts': ('accStmt' , english_acc_flow_fields_d , "account")
                     , 'liqProvider': ('liqStmt', english_liq_flow_fields_d, "")
                     , 'rateSwap': ('rsStmt', english_rs_flow_fields_d, "")
                     }
        output = {}
        for comp_name, comp_v in read_paths.items():
            if resp[0][comp_name] is None:
                continue
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
