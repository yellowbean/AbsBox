import logging, os, re, itertools
import requests, shutil
from dataclasses import dataclass, field
import functools, pickle
import pandas as pd
import numpy as np
from functools import reduce 
import toolz as tz
from .base import *
from .util import *
from .component import *
from .readers import readComponentStmts, readPoolFlows
from .interface import mkTag

def readBondStmt(respBond):
    match respBond:
        case {'tag':'BondGroup','contents':bndMap }:
            return {k: pd.DataFrame(list(tz.pluck("contents",[] if v['bndStmt'] is None else v['bndStmt'])), columns=english_bondflow_fields).set_index("date") for k,v in bndMap.items() }
        case {'tag':'Bond', **singleBndMap }:
            bStmt = mapNone(singleBndMap.get('bndStmt',[]),[])
            return pd.DataFrame(list(tz.pluck("contents", bStmt)), columns=english_bondflow_fields).set_index("date")
        case _:
            raise RuntimeError("Failed to read bond flow from resp",respBond)

def readTrgStmt(x):
    tStmt = mapNone(x.get('trgStmt',[]),[])
    return pd.DataFrame(list(tz.pluck("contents", tStmt)), columns=china_trigger_flow_fields_d).set_index("日期")


@dataclass
class SPV:
    名称: str
    日期: dict
    资产池: dict
    账户: tuple
    债券: tuple
    费用: tuple
    分配规则: dict
    归集规则: tuple
    流动性支持: dict | None = None
    利率对冲: dict | None = None
    汇率对冲: dict | None = None
    触发事件: dict | None = None
    状态: str = "摊销"
    自定义: dict | None = None
    科目: dict | None = None

    @property
    def json(self):
        parsedDates = mkDate(self.日期)
        mixedAssetFlag = isMixedDeal(self.资产池)
        (lastAssetDate,lastCloseDate) = getStartDate(self.日期)
        """
        get the json formatted string
        """
        _r = {
            "dates": parsedDates,
            "name": self.名称,
            "status": mkStatus(self.状态),
            "pool":  mkPoolType(lastAssetDate, self.资产池, mixedAssetFlag),
            "bonds": {bn: mkBndComp(bn, bo) for (bn, bo) in self.债券 },
            "waterfall": mkWaterfall({},self.分配规则.copy()),
            "fees": {fn: mkFee(fo|{"名称":fn}) for (fn, fo) in self.费用 },
            "accounts": {an:mkAcc(an,ao) for (an, ao) in self.账户 },
            "collects": [ mkCollection(c) for c in self.归集规则],
            "rateSwap": {k:mkRateSwap(v) for k,v in self.利率对冲.items()} if self.利率对冲 else None,
            "currencySwap": None,
            "custom": {cn:mkCustom(co) for cn,co in self.自定义.items()} if self.自定义 else None,
            "triggers": renameKs2({k: {_k: mkTrigger(_v) for (_k,_v) in v.items()} for (k,v) in self.触发事件.items() },chinaDealCycle) if self.触发事件 else None,
            "liqProvider": {ln: mkLiqProvider(ln, lo) for ln,lo in self.流动性支持.items() } if self.流动性支持 else None,
            "ledgers": {ln: mkLedger(ln, v) for ln,v in self.科目.items()} if self.科目 else None,
            "stats": [{},{},{},{}]
        }
        _dealType = identify_deal_type(_r)

        return mkTag((_dealType,_r))

    def _get_bond(self, bn):
        for _bn,_bo in self.债券:
            if _bn == bn:
                return _bo
        return None

    def read_pricing(self, pricing):
        if pricing:
            return mkPricingAssump(pricing)
        return None
    
    @staticmethod
    def read(resp):
        read_paths = { #'bonds': ('bndStmt', china_bondflow_fields, "债券")
                     'fees': ('feeStmt', china_fee_flow_fields_d, "费用")
                    , 'accounts': ('accStmt', china_acc_flow_fields_d , "账户")
                    , 'liqProvider': ('liqStmt', china_liq_flow_fields_d, "流动性支持")
                    , 'rateSwap': ('rsStmt', china_rs_flow_fields_d, "")
                    , 'ledgers': ('ledgStmt', china_ledger_flow_fields_d, "")
                    }
        assert isinstance(resp,list),f"<read>:resp should be list,but it is {type(resp)} => {resp}"
        deal_content = resp[0]['contents']
        output = {}
        output.update(readComponentStmts(deal_content, read_paths, date_key="日期", handle_none=False))
        # aggregate fees
        output['fees'] = {f: v.groupby('日期').agg({"余额": "min", "支付": "sum", "剩余支付": "min"})
                          for f, v in output['fees'].items()}
        
        # read bonds
        output['bonds'] = {k :readBondStmt(v) for k,v in deal_content['bonds'].items()}

        # trigger 
        if 'triggers' in deal_content and deal_content['triggers']:
            output['triggers'] = deal_content['triggers'] & lens.Values().Values().modify(readTrgStmt)    
        else:
            output['triggers'] = None
        
        # aggregate accounts
        output['agg_accounts'] = aggAccs(output['accounts'], 'chinese')

        output['pool'], output['pool_outstanding'] = readPoolFlows(resp, deal_content)

        output['pricing'] = readPricingResult(resp[3], 'cn')
        output['result'] = readRunSummary(resp[2], 'cn')
        output['_deal'] = resp[0]
        return output



信贷ABS = SPV # Legacy ,to be deleted
