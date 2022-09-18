from dataclasses import dataclass
import functools
from absbox.local.util import mkTag
import pandas as pd
import collections



def mkCollection(xs):
    sourceMapping = {"利息回款": "CollectedInterest", "本金回款": "CollectedPrincipal"
        , "早偿回款": "CollectedPrepayment", "回收回款": "CollectedRecoveries"}
    return [[sourceMapping[x], acc] for (x, acc) in xs]


def readIssuance(pool):
    if 'issuance' not in pool.keys():
        return None

    return pool['issuance']

def mkAssetRate(x):
    match x:
        case ["Fix", r]:
            return mkTag(("Fix", r))
        case ["Floater", r, {"bench":idx, "spread":spd, "reset":p}]:
            return mkTag(("Floater", [idx, spd, r, p, None]))


def mkAsset(x):
    _statusMapping = {"current": mkTag(("Current")), "defaulted": mkTag(("Defaulted",None))}
    match x:
        case ["Mortgage"
            ,{"faceValue": originBalance, "originRate": originRate, "originTerm": originTerm
                  ,"frequency": freq, "originDate": startDate}
            ,{ "currentBalance": currentBalance
             , "currentRate": currentRate
             , "remainTerms": remainTerms
             , "status": status}
              ]:
            return mkTag(("Mortgage",[{"originBalance": originBalance,
                     "originRate": mkAssetRate(originRate),
                     "originTerm": originTerm,
                     "period": freq,
                     "startDate": startDate,
                     "prinType": "Level"}
                     ,currentBalance
                     ,currentRate
                     ,remainTerms
                     ,_statusMapping[status]
                    ]))

def mkBondType(x):
    match x:
        case {"PAC": schedule}:
            return mkTag(("PAC", mkTag(("AmountCurve", schedule))))
        case {"Sequential": None}:
            return mkTag(("Sequential"))
        case {"Lockout": _after}:
            return mkTag(("Lockout", _after))
        case {"Equity": _}:
            return mkTag(("Equity"))

def mkAccType(x):
    match x:
        case {"FixReserve": amt}:
            return mkTag(("FixReserve", amt))
        case {"Target": [base, rate]}:
            match base:
                case ["Sum",*q]:
                    return mkTag(("PctReserve"
                                 , [mkTag(("Sum"
                                           ,[mkTag((_b, _ts)) for (_b, _ts) in q]))
                                   , rate ]))
                case _ :
                    return mkTag(("PctReserve", [mkTag((base)), rate]))
        case {"Max": [a, b]}:
            return mkTag(("Max", [mkAccType(a), mkAccType(b)]))
        case {"Min": [a, b]}:
            return mkTag(("Min", [mkAccType(a), mkAccType(b)]))

def mkFeeType(x):
    match x:
        case {"AnnualPctFee": [base, rate]}:
            return mkTag(("AnnualRateFee"
                        ,[ mkTag((base,'1970-01-01')) 
                        , rate]))
        case {"PctFee": [base, rate]}:
            return mkTag(("PctFee" ,[mkTag(base) , rate]))
        case {"FixFee": amt}:
            return mkTag(("FixFee", amt))
        case {"RecurFee": [p, amt]}:
            return mkTag(("RecurFee", [p, amt]))

def mkRateReset(x):
    match x:
        case {"resetInterval": interval, "start": sdate}:
            return mkTag(("ByInterval", [interval, sdate]))
        case {"resetInterval": interval}:
            return mkTag(("ByInterval", [interval, None]))
        case {"resetMonth": monthOfYear}:
            return mkTag(("MonthOfYear", monthOfYear))


def mkBondRate(x):
    indexMapping = {"LPR5Y": "LPR5Y", "LIBOR1M": "LIBOR1M"}
    match x:
        case {"Floater": [_index, Spread, resetInterval]}:
            return {"tag": "Floater"
                , "contents": [indexMapping[_index]
                    , Spread
                    , mkRateReset(resetInterval)
                    , None
                    , None]}
        case {"Fix": _rate}:
            return mkTag(("Fix",_rate))
        case {"InterimYield": _yield}:
            return mkTag(("InterestByYield",_yield))


def mkFeeCapType(x):
    match x:
        case {"DuePct": pct}:
            return mkTag(("DuePct",pct))
        case {"DueCapAmt": amt}:
            return mkTag(("DueCapAmt",amt))

def mkAccountCapType(x):
    match x:
        case {"DuePct": pct}:
            return mkTag(("DuePct",pct))
        case {"DueCapAmt": amt}:
            return mkTag(("DueCapAmt",amt))


def mkLiqMethod(x):
    match x:
        case ["Current|Defaulted",a,b]:
            return mkTag(("BalanceFactor",[a,b]))
        case ["Current|Delinquent|Defaulted",a,b,c]:
            return mkTag(("BalanceFactor2",[a,b,c]))
        case ["Haircut|Defaulted",a,b]:
            return mkTag(("PV",[a,b]))

def mkWaterfall(x):
    match x:
        case ["Transfer", source, target]:
            return mkTag(("Transfer",[source, target, ""]))
        case ["PayFee", source, target]:
            return mkTag(("PayFee",[source, target]))
        case ["PayFeeResidual", source, target, _limit]:
            limit = mkAccountCapType(_limit)
            return mkTag(("PayFeeResidual",[limit, source, target]))
        case ["PayFeeResidual", source, target]:
            return mkTag(("PayFeeResidual",[None, source, target]))
        case ["PayFeeBy", source, target, _limit]:
            limit = mkFeeCapType(_limit)
            return mkTag(("PayFeeBy",[limit, source, target]))
        case ["PayInt", source, target]:
            return mkTag(("PayInt",[source, target]))
        case ["PayPrin", source, target]:
            return mkTag(("PayPrin",[source, target]))
        case ["PayPrinResidual", source, target]:
            return mkTag(("PayPrinResidual",[source, target]))
        case ["PayTillYield", source, target]:
            return mkTag(("PayTillYield",[source, target]))
        case ["PayEquityResidual", source, target, limit]:
            return mkTag(("PayResidual",[limit, source, target]))
        case ["PayEquityResidual", source, target]:
            return mkTag(("PayResidual",[None, source, target]))
        case ["TransferReserve", source, target, satisfy]:
            return mkTag(("TransferReserve",[satisfy, source, target, None]))
        case ["LiquidatePool", liq, target]:
            return mkTag(("LiquidatePool",[mkLiqMethod(liq), target]))

def mk(x):
    match x:
        case ["assets", assets]:
            return {"assets": [mkAsset(a) for a in assets]}
        case ["account", accName, attrs]:
            match attrs:
                case {"balance": bal, "type": accType}:
                    return {accName: {"accBalance": bal, "accName": accName
                                      , "accType": mkAccType(accType)
                                      , "accInterest": None
                                      , "accStmt": mkAccTxn(attrs.get("txn",None))}}
                case {"balance": bal}:
                    return { accName: {"accBalance": bal, "accName": accName
                                      , "accType": None, "accInterest": None
                                      , "accStmt": mkAccTxn(attrs.get("txn",None))}}
        case ["fee", feeName, {"type": feeType}]:
            return {feeName: {"feeName": feeName, "feeType": mkFeeType(feeType), "feeStart": None, "feeDue": 0,
                              "feeArrears": 0, "feeLastPaidDay": None}}
        case ["bond", bndName, {"balance": bndBalance
            , "rate": bndRate
            , "originBalance": originBalance
            , "originRate": originRate
            , "startDate": originDate
            , "rateType": bndInterestInfo
            , "bondType": bndType
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
        case ["waterfall", instruction]:
            return mkWaterfall(instruction)
        case ["collection", collection]:
            return mkCollection(collection)
        #case ["call", calls]:
        #    return mkCall(calls)

def mkAssumption(x):
    match x:
        case {"CPR": cpr} if isinstance(cpr,list):
            return mkTag(("PrepaymentCPRCurve", cpr))
        case {"CPR": cpr} :
            return mkTag(("PrepaymentCPR", cpr))
        case {"CDR": cdr}:
            return mkTag(("DefaultCDR", cdr))
        case {"Recovery": (rr, rlag)}:
            return mkTag(("Recovery", (rr, rlag)))
        case {"Rate": [idx, rate]} if isinstance(rate, float):
            return mkTag(("InterestRateConstant", [idx, rate]))
        case {"Rate": [idx, *rateCurve]}:
            return mkTag(("InterestRateCurve", [idx, *rateCurve]))
        case {"Call": opts}:
            return mkTag(("CallWhen",[mkCallOptions(co) for co in opts]))
        case {"Stop": d}:
            return mkTag(("StopRunBy",d))

def mkAccTxn(xs):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [ mkTag(("AccTxn",x)) for x in xs]

def mkCf(x):
    if len(x)==0:
        return None
    else:
        return [ mkTag(("MortgageFlow",_x+([0.0]*5))) for _x in x]

def mkCallOptions(x):
    match x:
        case {"PoolBalance": bal}:
            return mkTag(("PoolBalance", bal))
        case {"BondBalance": bal}:
            return mkTag(("PoolBalance", bal))
        case {"PoolFactor": factor}:
            return mkTag(("PoolFactor", factor))
        case {"BondFactor": factor}:
            return mkTag(("PoolFactor", factor))
        case {"AfterDate": d}:
            return mkTag(("AfterDate", d))
        case {"Or": xs}:
            return mkTag(("Or", xs))
        case {"And": xs}:
            return mkTag(("And", xs))

def mkComponent(x):
    match x:
        case {"PVDay": pricingDay, "Curve": xs}:
            return [pricingDay, {"tag": "FloatCurve", "contents": xs}]
        case _:
            None

@dataclass
class Generic:
    name: str
    dates: tuple  # 起息日: datetime 封包日: datetime 首次兑付日 : datetime
    frequency: dict
    pool: dict
    accounts: tuple
    bonds: tuple
    fees: tuple
    waterfall: dict
    collection: tuple
    call: tuple

    @property
    def json(self):
        """
        get the json formatted string
        """
        cutoff, closing, first_pay = self.dates
        _r = {
            "dates": {
                "closing-date": closing,
                "cutoff-date": cutoff,
                "first-pay-date": first_pay},
            "name": self.name,
            "pool": {"assets": [mkAsset(x) for x in self.pool.get('breakdown', [])]
                     , "asOfDate": cutoff
                     , "issuanceStat": readIssuance(self.pool)
                     , "futureCf":mkCf(self.pool.get('cashflow', [])) },
            "bonds": functools.reduce(lambda result, current: result | current
                                      , [mk(['bond', bn, bo]) for (bn, bo) in self.bonds]),
            "waterfall": {"DistributionDay": [mkWaterfall(w) for w in self.waterfall.get('Normal',[])]
                        , "EndOfPoolCollection": [mkWaterfall(w) for w in self.waterfall.get('CollectionEnd', [])]
                        , "CleanUp":[ mkWaterfall(w) for w in self.waterfall.get('CleanUp' ,[])]},
            "fees": functools.reduce(lambda result, current: result | current
                                     , [mk(["fee", feeName, feeO]) for (feeName, feeO) in self.fees]) if self.fees else {},
            "accounts": functools.reduce(lambda result, current: result | current
                                         , [mk(["account", accName, accO]) for (accName, accO) in self.accounts]),
            "collects": self.collection,
            "collectPeriod": self.frequency['collection'],
            "payPeriod": self.frequency['payment']
        }
        for fn, fo in _r['fees'].items():
            fo['feeStart'] = _r['dates']['closing-date']
        return _r  # ,ensure_ascii=False)       return {}

    def read_assump(self, assump):
        if assump:
            return [mkAssumption(a) for a in assump]
        return None

    def read_pricing(self, pricing):
        if pricing:
            return mkComponent(pricing)
        return None


    def read(self, resp, position=None):
        read_paths = {'bonds': ('bndStmt'
                               , ["date", "balance", "interest", "principal", "rate", "cash", "memo"]
                               , "bond")
                     , 'fees': ('feeStmt'
                               , ["date", "balance", "payment", "due", "memo"]
                                , "fee")
                     , 'accounts': ('accStmt'
                                 , ["date", "balance", "change", "memo"]
                                 , "account")}
        output = {}
        for comp_name, comp_v in read_paths.items():
            #output[comp_name] = collections.OrderedDict()
            output[comp_name] = {}
            for k, x in resp[0][comp_name].items():
                ir = None
                if x[comp_v[0]]:
                    ir = [_['contents'] for _ in x[comp_v[0]]]
                output[comp_name][k] = pd.DataFrame(ir, columns=comp_v[1]).set_index("date")
            output[comp_name] = collections.OrderedDict(sorted(output[comp_name].items()))
        # aggregate fees
        print(output['fees'].items())
        output['fees'] = {f: v.groupby('date').agg({"balance": "min"
                                                   , "payment": "sum"
                                                   , "due": "min"})
                          for f, v in output['fees'].items()}

        # aggregate accounts
        agg_acc = {}
        for k,v in output['accounts'].items():
            acc_by_date = v.groupby("date")
            acc_txn_amt = acc_by_date.agg(change=("change", sum))
            ending_bal_column = acc_by_date.last()['balance'].rename("end balance")
            begin_bal_column = ending_bal_column.shift(1).rename("begin balance")
            agg_acc[k] = acc_txn_amt.join([begin_bal_column,ending_bal_column])
            if agg_acc[k].empty:
                agg_acc[k].columns = ['begin balance', "change", 'end balance']
                continue
            fst_idx = agg_acc[k].index[0]
            agg_acc[k].at[fst_idx, 'begin balance'] = round(agg_acc[k].at[fst_idx, 'end balance'] - agg_acc[k].at[fst_idx, 'change'], 2)
            agg_acc[k] = agg_acc[k][['begin balance', "change", 'end balance']]

        output['agg_accounts'] = agg_acc

        output['pool'] = {}
        output['pool']['flow'] = pd.DataFrame([_['contents'] for _ in resp[0]['pool']['futureCf']]
                                              , columns=["date", "未偿余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失", "利率"])
        output['pool']['flow'] = output['pool']['flow'].set_index("date")
        output['pool']['flow'].index.rename("date", inplace=True)

        output['pricing'] = pd.DataFrame.from_dict(resp[3]
                                                   , orient='index'
                                                   , columns=["估值", "票面估值", "WAL", "久期", "应计利息"]) if resp[3] else None

        return output
