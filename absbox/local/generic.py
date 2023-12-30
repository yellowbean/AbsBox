from dataclasses import dataclass
import functools

from absbox import *
from absbox.local.util import mkTag,mapListValBy,mapValsBy,renameKs2\
                              ,guess_pool_flow_header,positionFlow,mapNone\
                              ,isMixedDeal
from absbox.local.util import earlyReturnNone                              
from absbox.local.component import *
from absbox.local.base import * 
import pandas as pd
import collections
from absbox.validation import vStr,vDate,vNum,vList,vBool,vFloat,vInt


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
    liqFacility: dict = None
    rateSwap: dict = None
    currencySwap: dict = None
    trigger: dict = None
    status: str = "Amortizing"
    custom: dict = None
    ledgers: dict = None
    rateCap: dict = None

    @property
    def json(self):
        dists,collects,cleans = [self.waterfall.get(wn,[]) for wn in ['Normal','PoolCollection','CleanUp']]
        distsAs,collectsAs,cleansAs = [[ mkWaterfall2(_action) for _action in _actions] for _actions in [dists,collects,cleans]]
        distsflt,collectsflt,cleanflt = [itertools.chain.from_iterable(x) for x in [distsAs,collectsAs,cleansAs]]
        parsedDates = mkDate(self.dates)
        (lastAssetDate, lastCloseDate) = getStartDate(self.dates)
        mixedAssetFlag = isMixedDeal(self.pool)
        """
        get the json formatted string
        """
        _r = {
            "dates": parsedDates,
            "name": vStr(self.name),
            "status":mkStatus(self.status),
            "pool":mkPoolType(lastAssetDate, self.pool, mixedAssetFlag),
            "bonds": {bn: mkBnd(bn, bo) for (bn, bo) in self.bonds},
            "waterfall": mkWaterfall({},self.waterfall.copy()),  
            "fees": {fn: mkFee(fo|{"name":fn},fsDate = lastCloseDate) 
                                 for (fn,fo) in self.fees},
            "accounts": {an:mkAcc(an,ao) for (an,ao) in self.accounts},
            "collects": [mkCollection(c) for c in self.collection],
            "rateSwap": {k: mkRateSwap(v) for k, v in self.rateSwap.items()} if self.rateSwap else None,
            "rateCap": {k:mkRateCap(v) for k, v in self.rateCap.items()} if self.rateCap else None,
            "currencySwap":None ,
            "custom": {cn: mkCustom(co) for cn,co in self.custom.items()} if self.custom else None,
            "triggers": renameKs2({k: {_k: mkTrigger(_v) for (_k,_v) in v.items() } for (k, v) in self.trigger.items()},englishDealCycle) if self.trigger else None,
            "liqProvider": {ln: mkLiqProvider(ln, lo | {"start":lastCloseDate} ) 
                               for ln,lo in self.liqFacility.items() } if self.liqFacility else None,
            "ledgers": {ln: mkLedger(ln, v) for ln,v in self.ledgers.items()} if self.ledgers else None
        }

        _dealType = identify_deal_type(_r)

        return mkTag((_dealType, _r))

    def read_assump(self, assump):
        if assump:
            return [mkAssumption(a) for a in assump]
        return None

    def read_pricing(self, pricing):
        return earlyReturnNone(mkPricingAssump, pricing)
    
    @staticmethod
    def read(resp):
        read_paths = {'bonds': ('bndStmt', english_bondflow_fields, "bond")
                     , 'fees': ('feeStmt', english_fee_flow_fields_d, "fee")
                     , 'accounts': ('accStmt', english_acc_flow_fields_d, "account")
                     , 'liqProvider': ('liqStmt', english_liq_flow_fields_d, "")
                     , 'rateSwap': ('rsStmt', english_rs_flow_fields_d, "")
                     , 'rateCap': ('rcStmt', english_rs_flow_fields_d, "")
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
        output['agg_accounts'] = aggAccs(output['accounts'], 'english')

        output['pool'] = {}
        
        if deal_content['pool']['tag']=='SoloPool':
            if deal_content['pool']['contents']['futureCf'] is None:
                output['pool']['flow'] = None
            else:
                output['pool']['flow'] = readPoolCf(deal_content['pool']['contents']['futureCf']['contents'])
        elif deal_content['pool']['tag']=='MultiPool':
            poolMap = deal_content['pool']['contents']
            output['pool']['flow'] = {k: readPoolCf(v['futureCf']['contents']) for (k,v) in poolMap.items() }

        output['pricing'] = readPricingResult(resp[3], 'en')
        output['result'] = readRunSummary(resp[2], 'en')
        output['_deal'] = resp[0]
        return output
    
    def __str__(self):
        ''' Return a simplified string representation of deal object '''
        return f"{self.name}"
