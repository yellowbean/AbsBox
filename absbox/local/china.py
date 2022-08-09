from dataclasses import dataclass
import functools,pickle,collections
import pandas as pd
from enum import Enum

from absbox import *


class 频率(Enum):
    每月 = 12
    每季度 = 4
    每半年 = 2
    每年 = 1


freqMap = {"每月": "Monthly"
    , "每季度": "Quarterly"
    , "每半年": "SemiAnnually"
    , "每年": "Annually"}

baseMap = {"资产池余额": "CurrentPoolBalance", "资产池当期利息": "PoolCollectionInt"}


def mkTag(x):
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}


class BondType(Enum):
    固定摊还 = "固定摊还"
    过手摊还 = "过手摊还"
    锁定摊还 = "锁定摊还"
    期间收益 = "期间收益"


def mkBondType(x):
    match x:
        case {"固定摊还": schedule}:
            return {
                "tag": "PAC",
                "contents": {
                    "tag": "AmountCurve",
                    "contents": schedule}}
        case {"过手摊还": None}:
            return {"tag": "Sequential"}
        case {"锁定摊还": _after}:
            return {"tag": "Lockout"
                , "contents": _after}
        case {"权益": _}:
            return {"tag": "Equity"}


def mkAccType(x):
    baseMap = {"资产池余额": "CurrentPoolBalance"}
    match x:
        case {"固定储备金额": amt}:
            return {"tag": "FixReserve", "contents": amt}
        case {"目标储备金额": [base, rate]}:
            return {"tag": "PctReserve"
                , "contents": [{"tag": baseMap[base]}, rate]}
        case {"较高": [a, b]}:
            return {"tag": "Max"
                , "contents": [mkAccType(a), mkAccType(b)]}
        case {"较低": [a, b]}:
            return {"tag": "Min"
                , "contents": [mkAccType(a), mkAccType(b)]}


def mkFeeType(x):
    match x:
        case {"年化费率": [base, rate]}:
            return {"tag": "AnnualRateFee"
                , "contents": [{"tag": baseMap[base]}, rate]}
        case {"百分比费率": [base, rate]}:
            return {"tag": "PctFee"
                , "contents": [{"tag": baseMap[base]}, rate]}
        case {"固定费用": amt}:
            return mkTag(("FixFee", amt))
        case {"周期费用": [p, amt]}:
            return mkTag(("RecurFee", [freqMap[p], amt]))


def mkRateReset(x):
    match x:
        case {"重置期间": interval, "起始": sdate}:
            return mkTag(("ByInterval", [freqMap[interval], sdate]))
        case {"重置期间": interval}:
            return mkTag(("ByInterval", [freqMap[interval], None]))
        case {"重置月份": monthOfYear}:
            return mkTag(("MonthOfYear", monthOfYear))


def mkBondRate(x):
    indexMapping = {"LPR5Y": "LPR5Y", "LIBOR1M": "LIBOR1M"}
    match x:
        case {"浮动": [_index, Spread, resetInterval]}:
            return {"tag": "Floater"
                , "contents": [indexMapping[_index]
                    , Spread
                    , mkRateReset(resetInterval)
                    , None
                    , None]}
        case {"固定": _rate}:
            return {"tag": "Fix"
                , "contents": _rate}
        case {"期间收益": _yield}:
            return {"tag": "InterestByYield"
                , "contents": _yield}


def mkFeeCapType(x):
    match x:
        case {"应计费用百分比": pct}:
            return {"tag": "DuePct",
                    "contents": pct}
        case {"应计费用上限": amt}:
            return {"tag": "DueCapAmt",
                    "contents": amt}
def mkFormula(x):
    match x:
        case "A+B+C-D":
            return mkTag(("ABCD"))

def mkWaterfall(x):
    match x:
        case ["账户转移", source, target]:
            return {"tag": "Transfer"
                , "contents": [source, target, ""]}
        case ["按公式账户转移", source, target, formula]:
            return {"tag": "TransferBy"
                , "contents": [source, target, mkFormula(formula)]}
        case ["支付费用", source, target]:
            return {"tag": "PayFee"
                , "contents": [source, target]}
        case ["支付费用限额", source, target, _limit]:
            limit = mkFeeCapType(_limit)
            return {"tag": "PayFeeBy"
                , "contents": [limit, source, target]}
        case ["支付利息", source, target]:
            return {"tag": "PayInt"
                , "contents": [source, target]}
        case ["支付本金", source, target]:
            return {"tag": "PayPrin"
                , "contents": [source, target]}
        case ["支付期间收益", source, target]:
            return {"tag": "PayTillYield"
                , "contents": [source, target]}
        case ["支付收益", source, target]:
            return {"tag": "PayResidual"
                , "contents": [source, target]}
        case ["储备账户转移", source, target, keep]:
            return {"tag": "TransferReserve"
                , "contents": [keep, source, target]}

def mkAssetRate(x):
    match x:
        case ["固定",r]:
            return {"tag": "Fix", "contents": r}
        case ["浮动",r,{"基准":idx,"利差":spd,"重置频率":p}]:
            return {"tag": "Floater", "contents": [idx,spd,r,freqMap[p],None]}
            # Floater Index Spread Rate Period (Maybe Floor) 

def mkAsset(x):
    _typeMapping = {"等额本息" :"Level", "等额本金": "Even"}
    _statusMapping = {"正常":mkTag(("Current")),"违约": mkTag(("Defaulted",None))}
    match x:
        case ["按揭贷款"
            ,{"放款金额": originBalance, "放款利率": originRate, "初始期限": originTerm
                  ,"频率": freq, "类型": _type, "放款日": startDate}
            ,{"当前余额": currentBalance
             ,"当前利率": currentRate
             ,"剩余期限": remainTerms
             ,"状态": status}
              ]:
            return [{"originBalance": originBalance,
                     #"originRate": { "tag": "Fix", "contents": originRate },
                     "originRate": mkAssetRate(originRate),
                     "originTerm": originTerm,
                     "period": freqMap[freq],
                     "startDate": startDate,
                     "prinType": _typeMapping[_type]},
                    currentBalance,
                    currentRate,
                    remainTerms,
                    _statusMapping[status]
                    ]


def mkCollection(xs):
    sourceMapping = {"利息回款": "CollectedInterest", "本金回款": "CollectedPrincipal"
        , "早偿回款": "CollectedPrepayment", "回收回款": "CollectedRecoveries"}
    return [[sourceMapping[x], acc] for (x, acc) in xs]


def mkDate(x):
    match x:
        case {"起息日": d}:
            return {"closing-date": d}
        case {"首次兑付日": d}:
            return {"first-pay-date": d}
        case {"封包日": d}:
            return {"cutoff-date": d}


def mkComponent(x):
    match x:
        case {"贴现日": pricingDay, "贴现曲线": xs}:
            return [pricingDay, {"tag": "FloatCurve", "contents": xs}]
        case _:
            None


def mkLiq(x):
    match x:
        case {"正常余额折价": cf, "违约余额折价": df}:
            return mkTag(("BalanceFactor", [cf, df]))
        case {"贴现计价": df, "违约余额回收率": r}:
            return mkTag(("PV", [df, r]))


def mkCallOptions(x):
    match x:
        case {"资产池余额": bal}:
            return mkTag(("PoolBalance", bal))
        case {"债券余额": bal}:
            return mkTag(("PoolBalance", bal))
        case {"资产池余额剩余比率": factor}:
            return mkTag(("PoolFactor", factor))
        case {"债券余额剩余比率": factor}:
            return mkTag(("PoolFactor", factor))
        case {"指定日之后": d}:
            return mkTag(("AfterDate", d))
        case {"任意满足": xs}:
            return mkTag(("Or", xs))
        case {"全部满足": xs}:
            return mkTag(("And", xs))


def mkAssumption(x):
    match x:
        case {"CPR": cpr}:
            return mkTag(("PrepaymentCPR", cpr))
        case {"CDR": cdr}:
            return mkTag(("DefaultCDR", cdr))
        case {"回收": (rr, rlag)}:
            return mkTag(("Recovery", (rr, rlag)))
        case {"利率": [idx, rate]} if isinstance(rate, float):
            return mkTag(("InterestRateConstant", [idx, rate]))
        case {"利率": [idx, *rateCurve]}:
            return mkTag(("InterestRateCurve", [idx, *rateCurve]))
        case {"清仓": [opts, liq, accName]}:
            return mkTag(("CallWhen",
                          [[mkCallOptions(co) for co in opts]
                              , mkLiq(liq)
                              , accName]
                          ))

def mkAccTxn(xs):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [ mkTag(("AccTxn",x)) for x in xs]

def mk(x):
    match x:
        case ["资产", assets]:
            return {"assets": [mkAsset(a) for a in assets]}
        case ["账户", accName, attrs]:
            match attrs:
                case {"余额": bal, "类型": accType}:
                    return {accName: {"accBalance": bal, "accName": accName
                                      , "accType": mkAccType(accType)
                                      , "accInterest": None
                                      , "accStmt": mkAccTxn(attrs.get("记录",None))}}
                case {"余额": bal}:
                    return { accName: {"accBalance": bal, "accName": accName
                                      , "accType": None, "accInterest": None
                                      , "accStmt": mkAccTxn(attrs.get("记录",None))}}
        case ["费用", feeName, {"类型": feeType}]:
            return {feeName: {"feeName": feeName, "feeType": mkFeeType(feeType), "feeStart": None, "feeDue": 0,
                              "feeArrears": 0, "feeLastPaidDay": None}}
        case ["债券", bndName, {"当前余额": bndBalance
            , "当前利率": bndRate
            , "初始余额": originBalance
            , "初始利率": originRate
            , "起息日": originDate
            , "利率": bndInterestInfo
            , "债券类型": bndType
                              }]:
            return {bndName:
                        {"bndName": bndName
                            , "bndBalance": bndBalance
                            , "bndRate": bndRate
                            , "bndOriginInfo":
                             {"originBalance": originBalance
                                 , "originDate": originDate
                                 , "originRate": originRate}
                            , "bndInterestInfo": mkBondRate(bndInterestInfo)
                            , "bndType": mkBondType(bndType)
                            , "bndDuePrin": 0
                            , "bndDueInt": 0
                         }}
        case ["分配规则", instruction]:
            return mkWaterfall(instruction)
        case ["归集规则", collection]:
            return mkCollection(collection)
        case ["清仓回购", calls]:
            return mkCall(calls)


@dataclass
class 信贷ABS:
    名称: str
    日期: tuple  # 起息日: datetime 封包日: datetime 首次兑付日 : datetime
    兑付频率: 频率
    资产池: dict
    账户: tuple
    债券: tuple
    费用: tuple
    分配规则: tuple
    归集规则: tuple
    清仓回购: tuple


    @classmethod
    def load(cls,p):
        with open(p,'rb') as _f:
            c = _f.read()
        return pickle.loads(c)

    @property
    def json(self):
        cutoff, closing, first_pay = self.日期
        """
        get the json formatted string
        """
        _r = {
            "dates": {
                "closing-date": closing,
                "cutoff-date": cutoff,
                "first-pay-date": first_pay},
            "name": self.名称,
            "pool": {"assets": [mkAsset(x) for x in self.资产池['清单']]
                , "asOfDate": cutoff},
            "bonds": functools.reduce(lambda result, current: result | current
                                      , [mk(['债券', bn, bo]) for (bn, bo) in self.债券]),
            "waterfall": {"DistributionDay": [mkWaterfall(w) for w in self.分配规则['未违约']]
                , "EndOfPoolCollection": [mkWaterfall(w) for w in self.分配规则['回款后']]},
            "fees": functools.reduce(lambda result, current: result | current
                                     , [mk(["费用", feeName, feeO]) for (feeName, feeO) in self.费用]) if self.费用 else {},
            "accounts": functools.reduce(lambda result, current: result | current
                                         , [mk(["账户", accName, accO]) for (accName, accO) in self.账户]),
            "collects": mkCollection(self.归集规则),
            "collectPeriod": freqMap[self.兑付频率],
            "payPeriod": freqMap[self.兑付频率],
        }
        for fn, fo in _r['fees'].items():
            fo['feeStart'] = _r['dates']['closing-date']
        return _r  # ,ensure_ascii=False)

    def read_assump(self, assump):
        if assump:
            return [mkAssumption(a) for a in assump]
        return None

    def read_pricing(self, pricing):
        if pricing:
            return mkComponent(pricing)
        return None

    def read(self, resp):
        read_paths = {'bonds': ('bndStmt', ["日期", "余额", "利息", "本金", "执行利率", "本息合计", "备注"], "债券")
                    , 'fees': ('feeStmt', ["日期", "余额", "支付", "剩余支付", "备注"], "费用")
                    , 'accounts': ('accStmt', ["日期", "余额", "变动额", "备注"], "账户")}
        output = {}
        for comp_name, comp_v in read_paths.items():
            #output[comp_name] = collections.OrderedDict()
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
        agg_acc = {}
        for k,v in output['accounts'].items():
            acc_by_date = v.groupby("日期")
            acc_txn_amt = acc_by_date.agg(变动额=("变动额", sum))
            ending_bal_column = acc_by_date.last()['余额'].rename("期末余额")
            begin_bal_column = ending_bal_column.shift(1).rename("期初余额")
            agg_acc[k] = acc_txn_amt.join([begin_bal_column,ending_bal_column])
            fst_idx = agg_acc[k].index[0]
            agg_acc[k].at[fst_idx,'期初余额'] = round(agg_acc[k].at[fst_idx,'期末余额'] -  agg_acc[k].at[fst_idx,'变动额'],2)
            agg_acc[k] = agg_acc[k][['期初余额',"变动额",'期末余额']]

        output['agg_accounts'] = agg_acc

        output['pool'] = {}
        output['pool']['flow'] = pd.DataFrame([_['contents'] for _ in resp[0]['pool']['futureCf']]
                                              , columns=["日期", "未偿余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失", "利率"])
        output['pool']['flow'] = output['pool']['flow'].set_index("日期")
        output['pool']['flow'].index.rename("日期", inplace=True)

        output['pricing'] = pd.DataFrame.from_dict(resp[3]
                                                   , orient='index'
                                                   , columns=["估值", "票面估值", "WAL", "久期"]) if resp[3] else None
        return output


#    def load(self, path_to_file:str):
#        with open(path_to_file,'b') as of:
#            orjson.load(of, self.json)
#
#    def save(self, path_to_file:str):
#        with open(path_to_file,'w') as of:
#            orjson.dump(of, self.json)

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
