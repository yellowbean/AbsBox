from dataclasses import dataclass
import functools

from absbox import *
from absbox.local.util import mkTag,mapListValBy,mapValsBy,renameKs2,guess_pool_flow_header
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
    ledgers:dict = None

    @property
    def json(self):
        dists,collects,cleans = [ self.waterfall.get(wn,[]) for wn in ['Normal','PoolCollection','CleanUp']]
        distsAs,collectsAs,cleansAs = [ [ mkWaterfall2(_action) for _action in _actions] for _actions in [dists,collects,cleans] ]
        distsflt,collectsflt,cleanflt = [ itertools.chain.from_iterable(x) for x in [distsAs,collectsAs,cleansAs] ]
        parsedDates = mkDate(self.dates)
        (lastAssetDate,lastCloseDate) = getStartDate(self.dates)
        """
        get the json formatted string
        """
        _r = {
            "dates": parsedDates,
            "name": self.name,
            "status":mkTag((self.status)),
            "pool": {"assets": [mkAsset(x) for x in self.pool.get('assets', [])]
                     , "asOfDate": lastAssetDate
                     , "issuanceStat": self.pool.get("issuanceStat")
                     , "futureCf":mkCf(self.pool.get('cashflow', [])) },
            "bonds": { bn: mkBnd(bn,bo) for (bn,bo) in self.bonds},
            "waterfall": mkWaterfall({},self.waterfall.copy()),  
            "fees": {fn: mkFee(fo|{"name":fn},fsDate = lastCloseDate) 
                                 for (fn,fo) in self.fees},
            "accounts": {an:mkAcc(an,ao) for (an,ao) in self.accounts},
            "collects": [ mkCollection(c) for c in self.collection],
            "rateSwap": { k:mkRateSwap(v) for k,v in self.currencySwap.items()} if self.rateSwap else None,
            "currencySwap":None ,
            "custom": {cn:mkCustom(co) for cn,co in self.custom.items()} if self.custom else None ,
            "triggers": renameKs2(mapListValBy(self.trigger,mkTrigger),englishDealCycle) if self.trigger else None,
            "liqProvider": {ln: mkLiqProvider(ln, lo | {"start":lastCloseDate} ) 
                               for ln,lo in self.liqFacility.items() } if self.liqFacility else None,
            "ledgers": {ln: mkLedger(ln, v) for ln,v in self.ledgers.items()} if self.ledgers else None
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
    
    @staticmethod
    def read(resp):
        read_paths = {'bonds': ('bndStmt' , english_bondflow_fields , "bond")
                     , 'fees': ('feeStmt' , english_fee_flow_fields_d , "fee")
                     , 'accounts': ('accStmt' , english_acc_flow_fields_d , "account")
                     , 'liqProvider': ('liqStmt', english_liq_flow_fields_d, "")
                     , 'rateSwap': ('rsStmt', english_rs_flow_fields_d, "")
                     , 'ledgers': ('ledgStmt', english_ledger_flow_fields_d, "")
                     }
        deal_content = resp[0]['contents']
        output = {}
        for comp_name, comp_v in read_paths.items():
            if deal_content[comp_name] is None:
                continue
            output[comp_name] = {}
            for k, x in deal_content[comp_name].items():
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
        if deal_content['pool']['futureCf'] is None:
            output['pool']['flow'] = None
        else:
            _pool_cf_header,_ = guess_pool_flow_header(deal_content['pool']['futureCf'][0],"english")
            output['pool']['flow'] = pd.DataFrame([_['contents'] for _ in deal_content['pool']['futureCf']]
                                                  , columns=_pool_cf_header)
            pool_idx = 'Date'
            output['pool']['flow'] = output['pool']['flow'].set_index(pool_idx)
            output['pool']['flow'].index.rename(pool_idx, inplace=True)

        output['pricing'] = readPricingResult(resp[3], 'en')
        output['result'] = readRunSummary(resp[2], 'en')

        return output
