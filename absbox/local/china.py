import logging, os, re, itertools
import requests, shutil
from dataclasses import dataclass,field
import functools, pickle, collections
import pandas as pd
import numpy as np
from urllib.request import unquote
from enum import Enum
from functools import reduce 
import matplotlib.pyplot as plt

from absbox import *
from absbox.local.util import mkTag,DC,mkTs,consolStmtByDate,aggStmtByDate
from absbox.local.component import *

from pyspecter import query



def readIssuance(pool):
    if '发行' not in pool.keys():
        return None
    issuanceField = {
        "资产池规模":"IssuanceBalance"
    }
    r = {} 
    for k,v in pool['发行'].items():
        r[issuanceField[k]] = v
    return r

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
    清仓回购: tuple = None
    流动性支持:dict = None
    自定义: dict = None
    触发事件: dict = None
    状态:str = "摊销"

    @classmethod
    def load(cls,p):
        with open(p,'rb') as _f:
            c = _f.read()
        return pickle.loads(c)

    @classmethod
    def pull(cls,_id,p,url=None,pw=None):
        def get_filename_from_cd(cd):
            if not cd:
                return None
            fname = re.findall("filename\*=utf-8''(.+)", cd)
            if len(fname) == 0:
                fname1 = re.findall("filename=\"(.+)\"", cd)
                return fname1[0]
            return unquote(fname[0])
        with requests.get(f"{url}/china/deal/{_id}",stream=True,verify=False) as r:
            filename = get_filename_from_cd(r.headers.get('content-disposition'))
            if filename is None:
                logging.error("Can't not find the Deal Name")
                return None
            with open(os.path.join(p,filename),'wb') as f:
                shutil.copyfileobj(r.raw, f)
            logging.info(f"Download {p} {filename} done ")


    @property
    def json(self):
        stated = False 
        dists,collects,cleans = [ self.分配规则.get(wn,[]) for wn in ['未违约','回款后','清仓回购'] ]
        distsAs,collectsAs,cleansAs = [ [ mkWaterfall2(_action) for _action in _actions] for _actions in [dists,collects,cleans] ]
        distsflt,collectsflt,cleanflt = [ itertools.chain.from_iterable(x) for x in [distsAs,collectsAs,cleansAs] ]
        parsedDates = mkDate(self.日期)
        status = mkStatus(self.状态)
        defaultStartDate = self.日期.get("起息日",None) or self.日期['归集日'][0]
        """
        get the json formatted string
        """
        _r = {
            "dates": parsedDates,
            "name": self.名称,
            "status": status,
            "pool":{"assets": [mkAsset(x) for x in self.资产池.get('清单',[])]
                , "asOfDate": self.日期.get('封包日',None) or self.日期['归集日'][0]
                , "issuanceStat": readIssuance(self.资产池)
                , "futureCf":mkCf(self.资产池.get('归集表', []))},
            "bonds": functools.reduce(lambda result, current: result | current
                                      , [mk(['债券', bn, bo]) for (bn, bo) in self.债券]),
            "waterfall": mkWaterfall({},self.分配规则.copy()),
            "fees": functools.reduce(lambda result, current: result | current
                                     , [mk(["费用", feeName, feeO]) for (feeName, feeO) in self.费用]) if self.费用 else {},
            "accounts": functools.reduce(lambda result, current: result | current
                                         , [mk(["账户", accName, accO]) for (accName, accO) in self.账户]),
            "collects": mkCollection(self.归集规则)
        }
        
        for fn, fo in _r['fees'].items():
            if fo['feeStart'] is None :
                fo['feeStart'] = defaultStartDate

        if hasattr(self, "自定义") and self.自定义 is not None:
            _r["custom"] = {}
            for n,ci in self.自定义.items():
                _r["custom"][n] = mkCustom(ci)
        
        if hasattr(self, "触发事件") and self.触发事件 is  not None:
            _trigger  = self.触发事件
            _trr = {mkWhenTrigger(_loc):
                       [[mkTrigger(_trig),mkTriggerEffect(_effect)] for (_trig,_effect) in _vs ] 
                       for _loc,_vs in _trigger.items()}
            _r["triggers"] = _trr
        
        if hasattr(self, "流动性支持") and self.流动性支持 is not None:
            _providers = {}
            for (_k, _p) in self.流动性支持.items():
                _providers[_k] = mkLiqProvider(_k, ( _p | {"起始日": defaultStartDate}))
            _r["liqProvider"] = _providers

        _dealType = identify_deal_type(_r)

        return mkTag((_dealType,_r))

    def _get_bond(self, bn):
        for _bn,_bo in self.债券:
            if _bn == bn:
                return _bo
        return None
   
    def read_assump(self, assump):
        if assump:
            return [mkAssumption(a) for a in assump]
        return None

    def read_pricing(self, pricing):
        if pricing:
            return mkPricingAssump(pricing)
        return None

    def read(self, resp, position=None):
        read_paths = {'bonds': ('bndStmt', china_bondflow_fields, "债券")
                    , 'fees': ('feeStmt', china_fee_flow_fields_d, "费用")
                    , 'accounts': ('accStmt', china_acc_flow_fields_d , "账户")
                    , 'liqProvider': ('liqStmt', china_liq_flow_fields_d, "流动性支持")
                    }
        output = {}
        for comp_name, comp_v in read_paths.items():
            if (not comp_name in resp[0]) or (resp[0][comp_name] is None):
                continue
            output[comp_name] = {}
            for k, x in resp[0][comp_name].items():
                ir = None
                if x[comp_v[0]]:
                    ir = [_['contents'] for _ in x[comp_v[0]]]
                output[comp_name][k] = pd.DataFrame(ir, columns=comp_v[1]).set_index("日期")
            output[comp_name] = collections.OrderedDict(sorted(output[comp_name].items()))
        # aggregate fees
        output['fees'] = {f: v.groupby('日期').agg({"余额": "min", "支付": "sum", "剩余支付": "min"})
                          for f, v in output['fees'].items()}

        # aggregate accounts
        output['agg_accounts'] = aggAccs(output['accounts'],'cn')

        output['pool'] = {}
        _pool_cf_header,_ = guess_pool_flow_header(resp[0]['pool']['futureCf'][0],"chinese")
        output['pool']['flow'] = pd.DataFrame([_['contents'] for _ in resp[0]['pool']['futureCf']]
                                              , columns=_pool_cf_header)
        pool_idx = "日期"
        output['pool']['flow'] = output['pool']['flow'].set_index(pool_idx)
        output['pool']['flow'].index.rename(pool_idx, inplace=True)

        output['pricing'] = readPricingResult(resp[3], 'cn')
        if position:
            output['position'] = {}
            for k,v in position.items():
                if k in output['bonds']:
                    b = self._get_bond(k)
                    factor = v / b["初始余额"] / 100
                    if factor > 1.0:
                        raise  RuntimeError("持仓系数大于1.0")
                    output['position'][k] = output['bonds'][k][['本金','利息','本息合计']].apply(lambda x:x*factor).round(4)

        output['result'] = readRunSummary(resp[2], 'cn')
        return output

def show(r, x="full"):
    _comps = ['agg_accounts', 'fees', 'bonds']

    dfs = { c:pd.concat(r[c].values(), axis=1, keys=r[c].keys())
                             for c in _comps if r[c] }

    dfs2 = {}
    _m = {"agg_accounts":"账户","fees":"费用","bonds":"债券"}
    for k,v in dfs.items():
        dfs2[_m[k]] = pd.concat([v],keys=[_m[k]],axis=1)

    agg_pool = pd.concat([r['pool']['flow']], axis=1, keys=["资产池"])
    agg_pool = pd.concat([agg_pool], axis=1, keys=["资产池"])

    _full = functools.reduce(lambda acc,x: acc.merge(x,how='outer',on=["日期"]),[agg_pool]+list(dfs2.values()))

    match x:
        case "full":
            return _full.loc[:, ["资产池"]+list(dfs2.keys())].sort_index()
        case "cash":
            return None # ""

def flow_by_scenario(rs, flowpath,annotation=True,aggFunc=None,rnd=2):
    "pull flows from multiple scenario"
    scenario_names = rs.keys()
    dflow = None
    aggFM = {"max":pd.Series.max,"sum":pd.Series.sum,"min":pd.Series.min}
    
    if aggFunc is None:
        dflows = [query(rs,[s]+flowpath) for s in scenario_names]
    else:
        dflows = [query(rs,[s]+flowpath).groupby("日期").aggregate(aggFM.get(aggFunc,aggFunc)) for s in scenario_names]
        
    if annotation:
        dflows = [f.rename(f"{s}({flowpath[-1]})") for (s,f) in zip(scenario_names,dflows)]
    try: 
        return pd.concat(dflows,axis=1).round(rnd)
    except ValueError as e:
        return f"需要传入 aggFunc 函数对重复数据进行 Min/Max/Sum 处理"

信贷ABS = SPV # Legacy ,to be deleted