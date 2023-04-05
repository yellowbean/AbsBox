from absbox.local.util import mkTag, DC, mkTs, guess_locale, readTagStr
from enum import Enum
import itertools
import functools
import logging

import pandas as pd
from pyspecter import query, S

datePattern = {"月末": "MonthEnd", "季度末": "QuarterEnd", "年末": "YearEnd", "月初": "MonthFirst",
               "季度初": "QuarterFirst", "年初": "YearFirst", "每年": "MonthDayOfYear", "每月": "DayOfMonth", "每周": "DayOfWeek"}


freqMap = {"每月": "Monthly", "每季度": "Quarterly", "每半年": "SemiAnnually", "每年": "Annually", "Monthly": "Monthly", "Quarterly": "Quarterly", "SemiAnnually": "SemiAnnually", "Annually": "Annually", "monthly": "Monthly", "quarterly": "Quarterly", "semiAnnually": "SemiAnnually", "annually": "Annually"
           }

baseMap = {"资产池余额": "CurrentPoolBalance", "资产池期末余额": "CurrentPoolBalance", "资产池期初余额": "CurrentPoolBegBalance", "资产池初始余额": "OriginalPoolBalance", "初始资产池余额": "OriginalPoolBalance", "资产池当期利息": "PoolCollectionInt", "债券余额": "CurrentBondBalance", "债券初始余额": "OriginalBondBalance", "当期已付债券利息": "LastBondIntPaid", "当期已付费用": "LastFeePaid", "当期未付债券利息": "CurrentDueBondInt", "当期未付费用": "CurrentDueFee"
           }


def mkLiq(x):
    match x:
        case {"正常余额折价": cf, "违约余额折价": df}:
            return mkTag(("BalanceFactor", [cf, df]))
        case {"CurrentFactor": cf, "DefaultFactor": df}:
            return mkTag(("BalanceFactor", [cf, df]))
        case {"贴现计价": df, "违约余额回收率": r}:
            return mkTag(("PV", [df, r]))
        case {"PV": df, "DefaultRecovery": r}:
            return mkTag(("PV", [df, r]))


def mkDatePattern(x):
    match x:
        case ["每月", _d]:
            return mkTag((datePattern["每月"], _d))
        case ["每年", _m, _d]:
            return mkTag((datePattern["每年"], [_m, _d]))
        case ["DayOfMonth", _d]:
            return mkTag(("DayOfMonth", _d))
        case ["MonthDayOfYear", _m, _d]:
            return mkTag(("MonthDayOfYear", _m, _d))
        case ["CustomDate", *_ds]:
            return mkTag(("CustomDate", _ds))
        case ["AllDatePattern", *_dps]:
            return mkTag(("AllDatePattern", [ mkDatePattern(_) for _ in _dps]))
        case _x if (_x in datePattern.values()):
            return mkTag((_x))
        case _x if (_x in datePattern.keys()):
            return mkTag((datePattern[x]))
        case _:
            raise RuntimeError(f"Failed to match {x}")


def mkDate(x):
    match x:
        case {"封包日": a, "起息日": b, "首次兑付日": c, "法定到期日": d, "收款频率": pf, "付款频率": bf} | \
             {"cutoff": a, "closing": b, "firstPay": c, "stated": d, "poolFreq": pf, "payFreq": bf}:
            firstCollection = x.get("首次归集日", b)
            mr = x.get("循环结束日", None)
            return mkTag(("PreClosingDates", [a, b, mr, d, [firstCollection, mkDatePattern(pf)], [c, mkDatePattern(bf)]]))
        case {"归集日": (lastCollected, nextCollect), "兑付日": (pp, np), "法定到期日": c, "收款频率": pf, "付款频率": bf} | \
             {"collect": (lastCollected, nextCollect), "pay": (pp, np), "stated": c, "poolFreq": pf, "payFreq": bf}:
            mr = x.get("循环结束日", None)
            return mkTag(("CurrentDates", [[lastCollected, pp],
                                           mr,
                                           c,
                                           [nextCollect, mkDatePattern(pf)],
                                           [np, mkDatePattern(bf)]]))
        case {"回款日": cdays, "分配日": ddays, "封包日": cutoffDate, "起息日": closingDate} | \
                {"poolCollection": cdays, "distirbution": ddays, "cutoff": cutoffDate, "closing": closingDate}:
            return mkTag(("CustomDates", [cutoffDate, [mkTag(("PoolCollection", [cd, ""])) for cd in cdays], closingDate, [mkTag(("RunWaterfall", [dd, ""])) for dd in ddays]]))
        case _:
            raise RuntimeError(f"Failed to match:{x}")


def mkFeeType(x):
    match x:
        case {"年化费率": [base, rate]} | {"annualPctFee": [base, rate]}:
            return mkTag(("AnnualRateFee", [mkTag((baseMap[base], '1970-01-01')), rate]))
        case {"百分比费率": [*desc, rate]} | {"pctFee": [*desc, rate]}:
            match desc:
                case ["资产池回款", "利息"] | ["poolCollection", "interest"]:
                    return mkTag(("PctFee", [mkTag(("PoolCollectionIncome", "CollectedInterest")), rate]))
                case ["已付利息合计", *bns] | ["paidInterest", *bns]:
                    return mkTag(("PctFee", [mkTag(("LastBondIntPaid", bns)), rate]))
                case ["已付本金合计", *bns] | ["paidPrincipal", *bns]:
                    return mkTag(("PctFee", [mkTag(("LastBondPrinPaid", bns)), rate]))
                case _:
                    raise RuntimeError(f"Failed to match on 百分比费率：{desc,rate}")
        case {"固定费用": amt} | {"fixFee": amt}:
            return mkTag(("FixFee", amt))
        case {"周期费用": [p, amt]} | {"recurFee": [p, amt]}:
            return mkTag(("RecurFee", [mkDatePattern(p), amt]))
        case {"自定义": fflow} | {"customFee": fflow}:
            return mkTag(("FeeFlow", mkTs("BalanceCurve", fflow)))
        case {"计数费用": [p, s, amt]} | {"numFee": [p, s, amt]}:
            return mkTag(("NumFee", [mkDatePattern(p), mkDs(s), amt]))
        case _:
            raise RuntimeError(f"Failed to match on fee type:{x}")


def mkDateVector(x):
    match x:
        case dp if isinstance(dp, str):
            return mkTag(datePattern[dp])
        case [dp, *p] if (dp in datePattern.keys()):
            return mkTag((datePattern[dp], p))
        case _:
            raise RuntimeError(f"not match found: {x}")


def mkDs(x):
    "Making Deal Stats"
    match x:
        case ("债券余额",) | ("bondBalance",):
            return mkTag("CurrentBondBalance")
        case ("债券余额", *bnds) | ("bondBalance", *bnds):
            return mkTag(("CurrentBondBalanceOf", bnds))
        case ("初始债券余额",) | ("originalBondBalance",):
            return mkTag("OriginalBondBalance")
        case ("到期月份", bn) | ("monthsTillMaturity", bn):
            return mkTag(("MonthsTillMaturity", bn))
        case ("资产池余额",) | ("poolBalance",):
            return mkTag("CurrentPoolBalance")
        case ("初始资产池余额",) | ("originalPoolBalance",):
            return mkTag("OriginalPoolBalance")
        case ("资产池违约余额",) | ("currentPoolDefaultedBalance",):
            return mkTag("CurrentPoolDefaultedBalance")
        case ("资产池累积违约余额",) | ("cumPoolDefaultedBalance",):
            return mkTag("CumulativePoolDefaultedBalance")
        case ("资产池累积违约率",) | ("cumPoolDefaultedRate",):
            return mkTag("CumulativePoolDefaultedRate")
        case ("债券系数",) | ("bondFactor",):
            return mkTag("BondFactor")
        case ("资产池系数",) | ("poolFactor",):
            return mkTag("PoolFactor")
        case ("所有账户余额",) | ("accountBalance"):
            return mkTag("AllAccBalance")
        case ("账户余额", *ans) | ("accountBalance", *ans):
            return mkTag(("AccBalance", ans))
        case ("债券待付利息", *bnds) | ("bondDueInt", *bnds):
            return mkTag(("CurrentDueBondInt", bnds))
        case ("债券已付利息", *bnds) | ("lastBondIntPaid", *bnds):
            return mkTag(("LastBondIntPaid", bnds))
        case ("债券低于目标余额", bn) | ("behindTargetBalance", bn):
            return mkTag(("BondBalanceGap", bn))
        case ("债务人数量",) | ("borrowerNumber",):
            return mkTag(("CurrentPoolBorrowerNum"))

        #   , "当期已付债券利息":"LastBondIntPaid"
        #   , "当期已付费用" :"LastFeePaid"
        #   , "当期未付债券利息" :"CurrentDueBondInt"
        #   , "当期未付费用": "CurrentDueFee"

        case ("待付费用", *fns) | ("feeDue", *fns):
            return mkTag(("CurrentDueFee", fns))
        case ("已付费用", *fns) | ("lastFeePaid", *fns):
            return mkTag(("LastFeePaid", fns))
        case ("系数", ds, f) | ("factor", ds, f):
            return mkTag(("Factor", [mkDs(ds), f]))
        case ("Min", ds1, ds2):
            return mkTag(("Min", [mkDs(ds1), mkDs(ds2)]))
        case ("Max", ds1, ds2):
            return mkTag(("Max", [mkDs(ds1), mkDs(ds2)]))
        case ("合计", *ds) | ("sum", *ds):
            return mkTag(("Sum", [mkDs(_ds) for _ds in ds]))
        case ("差额", *ds) | ("substract", *ds):
            return mkTag(("Substract", [mkDs(_ds) for _ds in ds]))
        case ("常数", n) | ("constant", n):
            return mkTag(("Constant", n))
        case ("储备账户缺口", *accs) | ("reserveGap", *accs):
            return mkTag(("ReserveAccGap", accs))
        case ("自定义", n) | ("custom", n):
            return mkTag(("UseCustomData", n))
        case legacy if (legacy in baseMap.keys()):
            return mkDs((legacy,))
        case _:
            raise RuntimeError(f"Failed to match DS/Formula: {x}")


def isPre(x):
    try:
        return mkPre(x) is not None
    except RuntimeError as e:
        return False


def mkPre(p):
    def isIntQuery(y):
        match y:
            case ("monthsTillMaturity", _):
                return True
            case ("到期月份", _):
                return True
            case _:
                return False
    dealStatusMap = {"摊还": "Current", "加速清偿": "Accelerated", "循环": "Revolving"}

    match p:
        case [ds, "=", n]:
            if isIntQuery(ds):
                return mkTag(("IfEqInt", [mkDs(ds), n]))
            else:
                return mkTag(("IfEqBal", [mkDs(ds), n]))
        case [ds, ">", amt]:
            if isIntQuery(ds):
                return mkTag(("IfGTInt", [mkDs(ds), amt]))
            else:
                return mkTag(("IfGT", [mkDs(ds), amt]))
        case [ds, "<", amt]:
            if isIntQuery(ds):
                return mkTag(("IfLTInt", [mkDs(ds), amt]))
            else:
                return mkTag(("IfLT", [mkDs(ds), amt]))
        case [ds, ">=", amt]:
            if isIntQuery(ds):
                return mkTag(("IfGETInt", [mkDs(ds), amt]))
            else:
                return mkTag(("IfGET", [mkDs(ds), amt]))
        case [ds, "<=", amt]:
            if isIntQuery(ds):
                return mkTag(("IfLETInt", [mkDs(ds), amt]))
            else:
                return mkTag(("IfLET", [mkDs(ds), amt]))
        case [ds, "=", 0]:
            return mkTag(("IfZero", mkDs(ds)))
        case [">", _d]:
            return mkTag(("IfAfterDate", _d))
        case ["<", _d]:
            return mkTag(("IfBeforeDate", _d))
        case [">=", _d]:
            return mkTag(("IfAfterOnDate", _d))
        case ["<=", _d]:
            return mkTag(("IfBeforeOnDate", _d))
        case ["状态", _st] | ["status", _st]:
            return mkTag(("IfDealStatus", mkStatus(_st)))
        case ["同时满足", _p1, _p2] | ["all", _p1, _p2]:
            return mkTag(("And", mkPre(_p1), mkPre(_p2)))
        case ["任一满足", _p1, _p2] | ["any", _p1, _p2]:
            return mkTag(("Or", mkPre(_p1), mkPre(_p2)))
        case _:
            raise RuntimeError(f"Failed to match on Pre: {p}")


def mkAccInt(x):
    match x:
        case {"周期": _dp, "利率": idx, "利差": spd, "最近结息日": lsd} \
                | {"period": _dp,  "index": idx, "spread": spd, "lastSettleDate": lsd}:
            return mkTag(("InvestmentAccount", [idx, spd, lsd, mkDateVector(_dp)]))
        case {"周期": _dp, "利率": br, "最近结息日": lsd} \
                | {"period": _dp, "rate": br, "lastSettleDate": lsd}:
            return mkTag(("BankAccount", [br, lsd, mkDateVector(_dp)]))
        case None:
            return None
        case _:
            raise RuntimeError(
                f"Failed to match on account interest definition: {x}")


def mkAccType(x):
    match x:
        case {"固定储备金额": amt} | {"fixReserve": amt}:
            return mkTag(("FixReserve", amt))
        case {"目标储备金额": [base, rate]} | {"targetReserve": [base, rate]}:
            match base:
                case ["合计", *qs] | ["Sum", *qs]:
                    sumDs = [mkDs(q) for q in qs]
                    return mkTag(("PctReserve", [mkTag(("Sum", sumDs)), rate]))
                case _:
                    return mkTag(("PctReserve", [mkDs(base), rate]))
        case {"目标储备金额": {"公式": ds, "系数": rate}} | {"targetReserve": {"formula": ds, "factor": rate}}:
            return mkTag(("PctReserve", [mkDs(ds), rate]))
        case {"目标储备金额": {"公式": ds}} | {"targetReserve": {"formula": ds}}:
            return mkTag(("PctReserve", [mkDs(ds), 1.0]))
        case {"较高": [a, b]} | {"max": [a, b]}:
            return mkTag(("Max", [mkAccType(a), mkAccType(b)]))
        case {"较低": [a, b]} | {"min": [a, b]}:
            return mkTag(("Min", [mkAccType(a), mkAccType(b)]))
        case {"分段": [p, a, b]} | {"When": [p, a, b]}:
            return mkTag(("Either", [mkPre(p), mkAccType(a), mkAccType(b)]))
        case None:
            return None
        case _:
            raise RuntimeError(f"Failed to match {x} for account reserve type")


def mkAccTxn(xs):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [mkTag(("AccTxn", x)) for x in xs]


def mkAcc(an, x):
    match x:
        case {"余额": b, "类型": t, "计息": i, "记录": tx} | {"balance": b, "type": t, "interest": i, "txn": tx}:
            return {"accBalance": b, "accName": an, "accType": mkAccType(t), "accInterest": mkAccInt(i), "accStmt": mkAccTxn(tx)}

        case {"余额": b} | {"balance": b}:
            return mkAcc(an, x | {"计息": x.get("计息", None), "interest": x.get("interest", None), "记录": x.get("记录", None), "txn": x.get("txn", None), "类型": x.get("类型", None), "type": x.get("type", None)})
        case _:
            raise RuntimeError(f"Failed to match account: {an},{x}")


def mkBondType(x):
    match x:
        case {"固定摊还": schedule} | {"PAC": schedule}:
            return mkTag(("PAC", mkTag(("BalanceCurve", schedule))))
        case {"过手摊还": None} | {"Sequential": None}:
            return mkTag(("Sequential"))
        case {"锁定摊还": _after} | {"Lockout": _after}:
            return mkTag(("Lockout", _after))
        case {"权益": _} | {"Equity": _}:
            return mkTag(("Equity"))
        case _:
            raise RuntimeError(f"Failed to match bond type: {x}")


def mkRateReset(x):
    match x:
        case {"重置期间": interval, "起始": sdate} | {"resetInterval": interval, "starts": sdate}:
            return mkTag(("ByInterval", [freqMap[interval], sdate]))
        case {"重置期间": interval} | {"resetInterval": interval}:
            return mkTag(("ByInterval", [freqMap[interval], None]))
        case {"重置月份": monthOfYear} | {"resetMonth": monthOfYear}:
            return mkTag(("MonthOfYear", monthOfYear))
        case _:
            raise RuntimeError(f"Failed to match:{x}: mkRateReset")


def mkBondRate(x):
    indexMapping = {"LPR5Y": "LPR5Y", "LIBOR1M": "LIBOR1M"}
    match x:
        case {"浮动": [_index, Spread, resetInterval], "日历": dc} | \
                {"floater": [_index, Spread, resetInterval], "dayCount": dc}:
            return mkTag(("Floater", [indexMapping[_index], Spread, mkRateReset(resetInterval), dc, None, None]))
        case {"浮动": [_index, Spread, resetInterval]} | {"floater": [_index, Spread, resetInterval]}:
            return mkBondRate(x | {"日历": DC.DC_ACT_365F.value, "dayCount": DC.DC_ACT_365F.value})
        case {"固定": _rate, "日历": dc} | {"fix": _rate, "dayCount": dc}:
            return mkTag(("Fix", [_rate, dc]))
        case {"固定": _rate} | {"Fixed": _rate}:
            return mkTag(("Fix", [_rate, DC.DC_ACT_365F.value]))
        case {"期间收益": _yield}:
            return mkTag(("InterestByYield", _yield))
        case _:
            raise RuntimeError(f"Failed to match bond rate type:{x}")


def mkBnd(bn, x):
    match x:
        case {"当前余额": bndBalance, "当前利率": bndRate, "初始余额": originBalance, "初始利率": originRate, "起息日": originDate, "利率": bndInterestInfo, "债券类型": bndType} | \
                {"balance": bndBalance, "rate": bndRate, "originBalance": originBalance, "originRate": originRate, "startDate": originDate, "rateType": bndInterestInfo, "bondType": bndType}:
            md = x.get("到期日", None) or x.get("maturityDate", None)
            return {bn: {"bndName": bn, "bndBalance": bndBalance, "bndRate": bndRate, "bndOriginInfo":
                         {"originBalance": originBalance, "originDate": originDate, "originRate": originRate} | {"maturityDate": md}, "bndInterestInfo": mkBondRate(bndInterestInfo), "bndType": mkBondType(bndType), "bndDuePrin": 0, "bndDueInt": 0, "bndDueIntDate": None}}

        case _:
            raise RuntimeError(f"Failed to match bond:{bn},{x}:mkBnd")


def mkLiqMethod(x):
    match x:
        case ["正常|违约", a, b] | ["Cuurent|Defaulted", a, b]:
            return mkTag(("BalanceFactor", [a, b]))
        case ["正常|拖欠|违约", a, b, c] | ["Cuurent|Delinquent|Defaulted", a, b, c]:
            return mkTag(("BalanceFactor2", [a, b, c]))
        case ["贴现|违约", a, b] | ["PV|Defaulted", a, b]:
            return mkTag(("PV", [a, b]))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkLiqMethod")


def mkFeeCapType(x):
    match x:
        case {"应计费用百分比": pct} | {"duePct": pct}:
            return mkTag(("DuePct", pct))
        case {"应计费用上限": amt} | {"dueCapAmt": amt}:
            return mkTag(("DueCapAmt", amt))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkFeeCapType")


def mkPDA(x):
    match x:
        case {"公式": ds} | {"formula": ds}:
            return mkTag(("DS", mkDs(ds)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkPDA")


def mkAccountCapType(x):
    match x:
        case {"余额百分比": pct} | {"balPct": pct}:
            return mkTag(("DuePct", pct))
        case {"金额上限": amt} | {"balCapAmt": amt}:
            return mkTag(("DueCapAmt", amt))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAccountCapType")


def mkTransferLimit(x):
    match x:
        case {"余额百分比": pct} | {"balPct": pct}:
            return mkTag(("DuePct", pct))
        case {"金额上限": amt} | {"balCapAmt": amt}:
            return mkTag(("DueCapAmt", amt))
        case {"公式": "ABCD"}:
            return mkTag(("Formula", "ABCD"))
        case {"公式": formula} | {"formula": formula}:
            return mkTag(("DS", mkDs(formula)))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkTransferLimit")


def mkAction(x):
    match x:
        case ["账户转移", source, target] | ["transfer", source, target]:
            return mkTag(("Transfer", [source, target]))
        case ["按公式账户转移", _limit, source, target] | ["transferBy", _limit, source, target]:
            return mkTag(("TransferBy", [mkTransferLimit(_limit), source, target]))
        case ["计提费用", *feeNames] | ["calcFee", *feeNames]:
            return mkTag(("CalcFee", feeNames))
        case ["计提利息", *bndNames] | ["calcInt", *bndNames]:
            return mkTag(("CalcBondInt", bndNames))
        case ["支付费用", source, target] | ["payFee", source, target]:
            return mkTag(("PayFee", [source, target]))
        case ["支付费用收益", source, target, _limit] | ["payFeeResidual", source, target, _limit]:
            limit = mkAccountCapType(_limit)
            return mkTag(("PayFeeResidual", [limit, source, target]))
        case ["支付费用收益", source, target] | ["payFeeResidual", source, target]:
            return mkTag(("PayFeeResidual", [None, source, target]))
        case ["支付费用限额", source, target, _limit] | ["payFeeBy", source, target, _limit]:
            limit = mkFeeCapType(_limit)
            return mkTag(("PayFeeBy", [limit, source, target]))
        case ["支付利息", source, target] | ["payInt", source, target]:
            return mkTag(("PayInt", [source, target]))
        case ["支付本金", source, target, _limit] | ["payPrin", source, target, _limit]:
            pda = mkPDA(_limit)
            return mkTag(("PayPrinBy", [pda, source, target]))
        case ["支付本金", source, target] | ["payPrin", source, target]:
            return mkTag(("PayPrin", [source, target]))
        case ["支付剩余本金", source, target] | ["payPrinResidual", source, target]:
            return mkTag(("PayPrinResidual", [source, target]))
        case ["支付期间收益", source, target]:
            return mkTag(("PayTillYield", [source, target]))
        case ["支付收益", source, target, limit] | ["payResidual", source, target, limit]:
            return mkTag(("PayResidual", [limit, source, target]))
        case ["支付收益", source, target] | ["payResidual", source, target]:
            return mkTag(("PayResidual", [None, source, target]))
        case ["储备账户转移", source, target, satisfy] | ["transferReserve", source, target, satisfy]:
            _map = {"源储备": "Source", "目标储备": "Target"}
            return mkTag(("TransferReserve", [_map[satisfy], source, target]))
        case ["出售资产", liq, target] | ["sellAsset", liq, target]:
            return mkTag(("LiquidatePool", [mkLiqMethod(liq), target]))
        case ["流动性支持", source, target, limit] | ["liqSupport", source, target, limit]:
            return mkTag(("LiqSupport", [mkTag(("DS", mkDs(limit))), source, target]))
        case ["流动性支持", source, target] | ["liqSupport", source, target]:
            return mkTag(("LiqSupport", [None, source, target]))
        case ["流动性支持偿还", source, target] | ["liqRepay", source, target]:
            return mkTag(("LiqRepay", [None, source, target]))
        case ["流动性支持报酬", source, target] | ["liqRepayResidual", source, target]:
            return mkTag(("LiqYield", [None, source, target]))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkAction")


def mkWaterfall2(x):
    match x:
        case (pre, *_action) if isPre(pre) and len(x) > 2:  # pre with multiple actions
            _pre = mkPre(pre)
            return [[_pre, mkAction(a)] for a in _action]
        case (pre, _action) if isPre(pre) and len(x) == 2:  # pre with 1 actions
            _pre = mkPre(pre)
            return [[_pre, mkAction(_action)]]
        case _:
            return [[None, mkAction(x)]]


def mkStatus(x):
    match x:
        case "摊销" | "Amortizing":
            return mkTag(("Amortizing"))
        case "循环" | "Revolving":
            return mkTag(("Revolving"))
        case "加速清偿" | "Accelerated":
            return mkTag(("DealAccelerated", None))
        case "违约" | "Defaulted":
            return mkTag(("DealDefaulted", None))
        case "结束" | "Ended":
            return mkTag(("Ended"))
        case "设计" | "PreClosing":
            return mkTag(("PreClosing"))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkStatus")


def readStatus(x, locale):
    m = {"en": {'amort': "Amortizing", 'def': "Defaulted", 'acc': "Accelerated", 'end': "Ended",
                'pre': "PreClosing"}, "cn": {'amort': "摊销", 'def': "违约", 'acc': "加速清偿", 'end': "结束", 'pre': "设计"}}
    match x:
        case {"tag": "Amortizing"}:
            return m[locale]['amort']
        case {"tag": "DealAccelerated"}:
            return m[locale]['acc']
        case {"tag": "DealDefaulted"}:
            return m[locale]['def']
        case {"tag": "Ended"}:
            return m[locale]['end']
        case {"tag": "PreClosing"}:
            return m[locale]['pre']
        case _:
            raise RuntimeError(
                f"Failed to read deal status:{x} with locale: {locale}")


def mkWhenTrigger(x):
    match x:
        case "回收后" | "BeforeCollect":
            return "BeginCollectionWF"
        case "回收动作后" | "AfterCollect":
            return "EndCollectionWF"
        case "分配前" | "BeforeDistribution":
            return "BeginDistributionWF"
        case "分配后" | "AfterDistribution":
            return "EndDistributionWF"
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkWhenTrigger")


def mkThreshold(x):
    match x:
        case ">":
            return "Above"
        case ">=":
            return "EqAbove"
        case "<":
            return "Below"
        case "<=":
            return "EqBelow"
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkThreshold")


def _rateTypeDs(x):
    h = x[0]
    if h in set(["资产池累积违约率", "cumPoolDefaultedRate", "债券系数", "bondFactor", "资产池系数", "poolFactor"]):
        return True
    return False


def mkTrigger(x):
    match x:
        case [">", _d]:
            return mkTag(("AfterDate", _d))
        case [">=", _d]:
            return mkTag(("AfterOnDate", _d))
        case ["到期日未兑付", _bn] | ["passMaturity", _bn]:
            return mkTag(("PassMaturityDate", _bn))
        case ["所有满足", *trgs] | ["all", *trgs]:
            return mkTag(("AllTrigger", [mkTrigger(t) for t in trgs]))
        case ["任一满足", *trgs] | ["any", *trgs]:
            return mkTag(("AnyTrigger", [mkTrigger(t) for t in trgs]))
        case ["一直", b] | ["always", b]:
            return mkTag(("Always", b))
        case [ds, cmp, v] if (isinstance(v, float) and _rateTypeDs(ds)):
            return mkTag(("ThresholdRate", [mkThreshold(cmp), mkDs(ds), v]))
        case [ds, cmp, ts] if _rateTypeDs(ds):
            return mkTag(("ThresholdRateCurve", [mkThreshold(cmp), mkDs(ds), mkTs("ThresholdCurve", ts)]))
        case [ds, cmp, v] if (isinstance(v, float) or isinstance(v, int)):
            return mkTag(("ThresholdBal", [mkThreshold(cmp), mkDs(ds), v]))
        case [ds, cmp, ts]:
            return mkTag(("ThresholdBalCurve", [mkThreshold(cmp), mkDs(ds), mkTs("ThresholdCurve", ts)]))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkTrigger")


def mkTriggerEffect(x):
    match x:
        case ("新状态", s) | ("newStatus", s):
            return mkTag(("DealStatusTo", mkStatus(s)))
        case ["计提费用", *fn] | ["accrueFees", *fn]:
            return mkTag(("DoAccrueFee", fn))
        case ["新增事件", trg] | ["newTrigger", trg]:
            return mkTag(("AddTrigger", mkTrigger(trg)))
        case ["结果", *efs] | ["Effects", *efs]:
            return mkTag(("TriggerEffects", [mkTriggerEffect(e) for e in efs]))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkTriggerEffect")


def mkWaterfall(r, x):
    mapping = {
        "未违约": "Amortizing",
        "摊销": "Amortizing",
        "循环": "Revolving",
        "加速清偿": "DealAccelerated",
        "违约": "DealDefaulted",
        "未设立": "PreClosing",
    }
    if len(x) == 0:
        return {k: list(v) for k, v in r.items()}
    _k, _v = x.popitem()
    _w_tag = None
    match _k:
        case ("兑付日", "加速清偿") | ("amortizing", "accelerated"):
            _w_tag = f"DistributionDay (DealAccelerated Nothing)"
        case ("兑付日", "违约") | ("amortizing", "defaulted"):
            _w_tag = f"DistributionDay (DealDefaulted Nothing)"
        case ("兑付日", _st) | ("amortizing", _st):
            _w_tag = f"DistributionDay {mapping.get(_st,_st)}"
        case "兑付日" | "未违约" | "amortizing":
            _w_tag = f"DistributionDay Amortizing"
        case "清仓回购" | "cleanUp":
            _w_tag = "CleanUp"
        case "回款日" | "回款后" | "endOfCollection":
            _w_tag = f"EndOfPoolCollection"
        case "设立日" | "closingDay":
            _w_tag = f"OnClosingDay"
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkWaterfall")
    r[_w_tag] = itertools.chain.from_iterable([mkWaterfall2(_a) for _a in _v])
    return mkWaterfall(r, x)


def mkAssetRate(x):
    match x:
        case ["固定", r] | ["fix", r]:
            return mkTag(("Fix", r))
        case ["浮动", r, {"基准": idx, "利差": spd, "重置频率": p}]:
            return mkTag(("Floater", [idx, spd, r, freqMap[p], None]))
        case ["floater", r, {"index": idx, "spread": spd, "reset": p}]:
            return mkTag(("Floater", [idx, spd, r, freqMap[p], None]))
        case ["Floater", r, {"index": idx, "spread": spd, "reset": p}]:
            return mkTag(("Floater", [idx, spd, r, freqMap[p], None]))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAssetRate")


def mkAmortPlan(x) -> dict:
    match x:
        case "等额本息" | "Level" | "level":
            return mkTag("Level")
        case "等额本金" | "Even" | "even":
            return mkTag("Even")
        case "先息后本" | "I_P" | "i_p":
            return mkTag("I_P")
        case "等本等费" | "F_P" | "f_p":
            return mkTag("F_P")
        case _:
            raise RuntimeError(f"Failed to match AmortPlan {x}:mkAmortPlan")


def mkAsset(x):
    _statusMapping = {"正常": mkTag(("Current")), "违约": mkTag(("Defaulted", None)), "current": mkTag(("Current")), "defaulted": mkTag(("Defaulted", None)), "Current": mkTag(("Current")), "Defaulted": mkTag(("Defaulted", None))
                      }
    match x:
        case ["按揭贷款", {"放款金额": originBalance, "放款利率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate}, {"当前余额": currentBalance, "当前利率": currentRate, "剩余期限": remainTerms, "状态": status}] | \
                ["Mortgage", {"originBalance": originBalance, "originRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate}, {"currentBalance": currentBalance, "currentRate": currentRate, "remainTerm": remainTerms, "status": status}]:

            borrowerNum1 = x[2].get("borrowerNum", None)
            borrowerNum2 = x[2].get("借款数量", None)

            return mkTag(("Mortgage", [
                {"originBalance": originBalance,
                 "originRate": mkAssetRate(originRate),
                 "originTerm": originTerm,
                 "period": freqMap[freq],
                 "startDate": startDate,
                 "prinType": mkAmortPlan(_type)
                 } | mkTag("MortgageOriginalInfo"),
                currentBalance,
                currentRate,
                remainTerms,
                (borrowerNum1 or borrowerNum2),
                _statusMapping[status]]))
        case ["贷款", {"放款金额": originBalance, "放款利率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate}, {"当前余额": currentBalance, "当前利率": currentRate, "剩余期限": remainTerms, "状态": status}] \
                | ["Loan", {"originBalance": originBalance, "originRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate}, {"currentBalance": currentBalance, "currentRate": currentRate, "remainTerm": remainTerms, "status": status}]:
            return mkTag(("PersonalLoan", [
                {"originBalance": originBalance,
                 "originRate": mkAssetRate(originRate),
                 "originTerm": originTerm,
                 "period": freqMap[freq],
                 "startDate": startDate,
                 "prinType": mkAmortPlan(_type)
                 } | mkTag("LoanOriginalInfo"),
                currentBalance,
                currentRate,
                remainTerms,
                _statusMapping[status]]))
        case ["分期", {"放款金额": originBalance, "放款费率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate, "剩余期限": remainTerms}, {"当前余额": currentBalance, "状态": status}] \
                | ["Installment", {"originBalance": originBalance, "feeRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate, "remainTerm": remainTerms}, {"currentBalance": currentBalance, "status": status}]:
            return mkTag(("Installment", [
                {"originBalance": originBalance,
                 "originRate": mkAssetRate(originRate),
                 "originTerm": originTerm,
                 "period": freqMap[freq],
                 "startDate": startDate,
                 "prinType": mkAmortPlan(_type)
                 } | mkTag("LoanOriginalInfo"),
                currentBalance,
                remainTerms,
                _statusMapping[status]]))
        case ["租赁", {"固定租金": dailyRate, "初始期限": originTerm, "频率": dp, "起始日": startDate, "状态": status, "剩余期限": remainTerms}] \
                | ["Lease", {"fixRental": dailyRate, "originTerm": originTerm, "freq": dp, "originDate": startDate, "status": status, "remainTerm": remainTerms}]:
            return mkTag(("RegularLease", [{"originTerm": originTerm, "startDate": startDate, "paymentDates": mkDatePattern(dp), "originRental": dailyRate} | mkTag("LeaseInfo"), 0, remainTerms, _statusMapping[status]]))
        case ["租赁", {"初始租金": dailyRate, "初始期限": originTerm, "频率": dp, "起始日": startDate, "计提周期": accDp, "涨幅": rate, "状态": status, "剩余期限": remainTerms}] \
                | ["Lease", {"initRental": dailyRate, "originTerm": originTerm, "freq": dp, "originDate": startDate, "accrue": accDp, "pct": rate, "status": status, "remainTerm": remainTerms}]:

            dailyRatePlan = None
            _stepUpType = "curve" if isinstance(rate, list) else "constant"
            if _stepUpType == "constant":
                dailyRatePlan = mkTag(
                    ("FlatRate", [mkDatePattern(accDp), rate]))
            else:
                dailyRatePlan = mkTag(
                    ("ByRateCurve", [mkDatePattern(accDp), rate]))
            return mkTag(("StepUpLease", [{"originTerm": originTerm, "startDate": startDate, "paymentDates": mkDatePattern(dp), "originRental": dailyRate} | mkTag("LeaseInfo"), dailyRatePlan, 0, remainTerms, _statusMapping[status]]))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAsset")


def identify_deal_type(x):
    match x:
        case {"pool": {"assets": [{'tag': 'PersonalLoan'}, *rest]}}:
            return "LDeal"
        case {"pool": {"assets": [{'tag': 'Mortgage'}, *rest]}}:
            return "MDeal"
        case {"pool": {"assets": [], "futureCf": cfs}} if cfs[0]['tag'] == 'MortgageFlow':
            return "MDeal"
        case {"pool": {"assets": [{'tag': 'Installment'}, *rest]}}:
            return "IDeal"
        case {"pool": {"assets": [{'tag': 'Lease'}, *rest]}} | {"pool": {"assets": [{'tag': 'RegularLease'}, *rest]}}:
            return "RDeal"
        case {"pool": {"assets": [{'tag': 'StepUpLease'}, *rest]}}:
            return "RDeal"
        case _:
            raise RuntimeError(f"Failed to identify deal type {x}")


def mkCallOptions(x):
    match x:
        case {"资产池余额": bal} | {"poolBalance": bal}:
            return mkTag(("PoolBalance", bal))
        case {"债券余额": bal} | {"bondBalance": bal}:
            return mkTag(("BondBalance", bal))
        case {"资产池余额剩余比率": factor} | {"poolFactor": factor}:
            return mkTag(("PoolFactor", factor))
        case {"债券余额剩余比率": factor} | {"bondFactor": factor}:
            return mkTag(("BondFactor", factor))
        case {"指定日之后": d} | {"afterDate": d}:
            return mkTag(("AfterDate", d))
        case {"任意满足": xs} | {"or": xs}:
            return mkTag(("Or", [mkCallOptions(_x) for _x in xs]))
        case {"全部满足": xs} | {"and": xs}:
            return mkTag(("And", [mkCallOptions(_x) for _x in xs]))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkCallOptions")


def mkAssumption(x) -> dict:
    match x:
        case {"CPR": cpr} if isinstance(cpr, list):
            return mkTag(("PrepaymentVec", cpr))
        case {"CDR": cdr} if isinstance(cdr, list):
            return mkTag(("DefaultVec", cdr))
        case {"CPR": cpr}:
            return mkTag(("PrepaymentCPR", cpr))
        case {"CPR调整": [*cprAdj, ed]} | {"CPRAdjust": [*cprAdj, ed]}:
            return mkTag(("PrepaymentFactors", mkTs("FactorCurveClosed", [cprAdj, ed])))
        case {"CDR": cdr}:
            return mkTag(("DefaultCDR", cdr))
        case {"CDR调整": [*cdrAdj, ed]} | {"CDRAdjust": [*cdrAdj, ed]}:
            return mkTag(("DefaultFactors", mkTs("FactorCurveClosed", [cdrAdj, ed])))
        case {"回收": (rr, rlag)} | {"Recovery": (rr, rlag)}:
            return mkTag(("Recovery", (rr, rlag)))
        case {"利率": [idx, rate]} if isinstance(rate, float):
            return mkTag(("InterestRateConstant", [idx, rate]))
        case {"Rate": [idx, rate]} if isinstance(rate, float):
            return mkTag(("InterestRateConstant", [idx, rate]))
        case {"利率": [idx, *rateCurve]} | {"Rate": [idx, *rateCurve]}:
            return mkTag(("InterestRateCurve", [idx, *rateCurve]))
        case {"清仓": opts} | {"CleanUp": opts}:
            return mkTag(("CallWhen", [mkCallOptions(co) for co in opts]))
        case {"停止": d} | {"StopAt": d}:
            return mkTag(("StopRunBy", d))
        case {"租赁截止日": d} | {"LeaseProjectEnd": d}:
            return mkTag(("LeaseProjectionEnd", d))
        case {"租赁年涨幅": r} | {"LeaseAnnualIncreaseRate": r} if not isinstance(r, list):
            return mkTag(("LeaseBaseAnnualRate", r))
        case {"租赁年涨幅": r} | {"LeaseAnnualIncreaseRate": r}:
            return mkTag(("LeaseBaseCurve", mkTs("FloatCurve", r)))
        case {"租赁间隔": n} | {"LeaseGapDays": n}:
            return mkTag(("LeaseGapDays", n))
        case {"租赁间隔表": (tbl, n)} | {"LeaseGapDaysByAmount": (tbl, n)}:
            return mkTag(("LeaseGapDaysByAmount", [tbl, n]))
        case {"查看":inspects} | {"Inspect":inspects}:
            inspectVars = [ [mkDatePattern(dp),mkDs(ds)] for dp,ds in inspects ]
            return mkTag(("InspectOn", inspectVars))
        case _:
            raise RuntimeError(f"Failed to match {x}:Assumption")


def mkAssumpList(xs):
    return [mkAssumption(x) for x in xs]


def mkAssumption2(x) -> dict:
    match x:
        case (assetAssumpList, dealAssump) if isinstance(x, tuple):
            return mkTag(("ByIndex", [[(ids, mkAssumpList(aps)) for ids, aps in assetAssumpList], mkAssumpList(dealAssump)]))
        case xs if isinstance(xs, list):
            return mkTag(("PoolLevel", mkAssumpList(xs)))
        case None:
            return None
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAssumption2")


def mkPool(x):
    mapping = {"LDeal": "LPool", "MDeal": "MPool",
               "IDeal": "IPool", "RDeal": "RPool"}
    match x:
        case {"清单": assets, "封包日": d} | {"assets": assets, "cutoffDate": d}:
            _pool = {"assets": [mkAsset(a) for a in assets], "asOfDate": d}
            _pool_asset_type = identify_deal_type({"pool": _pool})
            return mkTag((mapping[_pool_asset_type], _pool))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkPool")


def mkCustom(x):
    match x:
        case {"常量": n} | {"Constant": n}:
            return mkTag(("CustomConstant", n))
        case {"余额曲线": ts} | {"BalanceCurve": ts}:
            return mkTag(("CustomCurve", mkTs("BalanceCurve", ts)))
        case {"公式": ds} | {"Formula": ds}:
            return mkTag(("CustomDS", mkDs(ds)))


def mkLiqProvider(n, x):
    match x:
        case {"类型": "无限制", "起始日": _sd, **p} \
                | {"type": "Unlimited", "start": _sd, **p}:
            return {"liqName": n, "liqType": mkLiqProviderType({}), "liqBalance": None, "liqCredit": p.get("已提供", 0), "liqStart": _sd}
        case {"类型": _sp, "额度": _ab, "起始日": _sd, **p} \
                | {"type": _sp, "lineOfCredit": _ab, "start": _sd, **p}:
            return {"liqName": n, "liqType": mkLiqProviderType(_sp), "liqBalance": _ab, "liqCredit": p.get("已提供", 0), "liqStart": _sd}
        case _:
            raise RuntimeError(f"无法匹配流动性支持类型：{n,x}")


def mkCf(x):
    if len(x) == 0:
        return None
    else:
        return [mkTag(("MortgageFlow", _x+[0.0]*5+[None])) for _x in x]


def mkCollection(xs):
    sourceMapping = {"利息回款": "CollectedInterest", "本金回款": "CollectedPrincipal", "早偿回款": "CollectedPrepayment", "回收回款": "CollectedRecoveries", "租金回款": "CollectedRental", "CollectedInterest": "CollectedInterest", "CollectedPrincipal": "CollectedPrincipal", "CollectedPrepayment": "CollectedPrepayment", "CollectedRecoveries": "CollectedRecoveries", "CollectedRental": "CollectedRental"
                     }
    return [[sourceMapping[x], acc] for (x, acc) in xs]


def mkAccTxn(xs):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [mkTag(("AccTxn", x)) for x in xs]


def mk(x):
    match x:
        case ["资产", assets]:
            return {"assets": [mkAsset(a) for a in assets]}
        case ["账户", accName, attrs] | ["account", accName, attrs]:
            return {accName: mkAcc(accName, attrs)}
        case ["费用", feeName, {"类型": feeType, **fi}] \
                | ["fee", feeName, {"type": feeType, **fi}]:
            return {feeName: {"feeName": feeName, "feeType": mkFeeType(feeType), "feeStart": fi.get("起算日", None), "feeDueDate": fi.get("计算日", None), "feeDue": 0,
                              "feeArrears": 0, "feeLastPaidDay": None}}
        case ["债券", bndName, bnd] | ["bond", bndName, bnd]:
            return mkBnd(bndName, bnd)
        case ["归集规则", collection]:
            return mkCollection(collection)


def mkPricingAssump(x):
    match x:
        case {"贴现日": pricingDay, "贴现曲线": xs} | {"PVDate": pricingDay, "PVCurve": xs}:
            return mkTag(("DiscountCurve", [pricingDay, mkTs("IRateCurve", xs)]))
        case {"债券": bnd_with_price, "利率曲线": rdps} | {"bonds": bnd_with_price, "curve": rdps}:
            return mkTag(("RunZSpread", [mkTs("IRateCurve", rdps), bnd_with_price]))
        case _:
            raise RuntimeError(f"Failed to match pricing assumption: {x}")


def mkLiqProviderType(x):
    match x:
        case {"总额度": amt} | {"Total": amt}:
            return mkTag(("FixSupport"))
        case {"日期": dp, "限额": amt} | {"Reset": dp, "Quota": amt}:
            return mkTag(("ReplenishSupport", [mkDatePattern(dp), amt]))
        case {}:
            return mkTag(("UnLimit"))


def readPricingResult(x, locale) -> dict:
    if x is None:
        return None
    h = None

    tag = query(x, [S.MVALS, S.ALL, "tag"])[0]
    if tag == "PriceResult":
        h = {"cn": ["估值", "票面估值", "WAL", "久期", "凸性", "应计利息"],
             "en": ["pricing", "face", "WAL", "duration", "convexity", "accure interest"]}
    elif tag == "ZSpread":
        h = {"cn": ["静态利差"], "en": ["Z-spread"]}
    else:
        raise RuntimeError(
            f"Failed to read princing result: {x} with tag={tag}")

    return pd.DataFrame.from_dict({k: v['contents'] for k, v in x.items()}, orient='index', columns=h[locale]).sort_index()


def readRunSummary(x, locale) -> dict:
    def filter_by_tags(xs, tags):
        tags_set = set(tags)
        return [ x for x in xs if x['tag'] in tags_set]

    r = {}
    if x is None:
        return None

    bndStatus = {'cn': ["本金违约", "利息违约", "起算余额"], 'en': [
        "Balance Defaults", "Interest Defaults", "Original Balance"]}
    bond_defaults = [(_['contents'][0], _['tag'], _['contents'][1], _['contents'][2])
                     for _ in x if _['tag'] in set(['BondOutstanding', 'BondOutstandingInt'])]
    _fmap = {"cn": {'BondOutstanding': "本金违约", "BondOutstandingInt": "利息违约"}, "en": {
        'BondOutstanding': "Balance Defaults", "BondOutstandingInt": "Interest Defaults"}}
    bndNames = set([y[0] for y in bond_defaults])
    bndSummary = pd.DataFrame(columns=bndStatus[locale], index=list(bndNames))
    for bn, amt_type, amt, begBal in bond_defaults:
        bndSummary.loc[bn][_fmap[locale][amt_type]] = amt
        bndSummary.loc[bn][bndStatus[locale][2]] = begBal
    bndSummary.fillna(0, inplace=True)
    bndSummary["Total"] = bndSummary[bndStatus[locale][0]] + \
        bndSummary[bndStatus[locale][1]]

    r['bonds'] = bndSummary

    dealStatusLog = {'cn': ["日期", "旧状态", "新状态"], 'en': ["Date", "From", "To"]}
    status_change_logs = [(_['contents'][0], readStatus(_['contents'][1], locale), readStatus(_['contents'][2], locale))
                          for _ in x if _['tag'] in set(['DealStatusChangeTo'])]
    r['status'] = pd.DataFrame(data=status_change_logs, columns=dealStatusLog[locale])

    # inspection variables
    def uplift_ds(df):
        ds_name = readTagStr(df['DealStats'].iloc[0])
        df.drop(columns=["DealStats"],inplace=True)
        df.rename(columns={"Value":ds_name},inplace=True)
        df.set_index("Date",inplace=True)
        return df
    inspect_vars = filter_by_tags(x, ["InspectBal"])
    inspect_df = pd.DataFrame(data = [ (c['contents'][0],str(c['contents'][1]),c['contents'][2])   for c in inspect_vars ]
                                ,columns=["Date","DealStats","Value"])

    grped_inspect_df = inspect_df.groupby("DealStats")

    r['inspect'] = {readTagStr(k):uplift_ds(v) for k,v in grped_inspect_df}
    return r


def aggAccs(x, locale):
    _header = {
        "cn": {"idx": "日期", "change": "变动额", "bal": ("期初余额", '余额', "期末余额")}, "en": {"idx": "date", "change": "change", "bal": ("begin balance", 'balance', "end balance")}
    }

    header = _header[locale]
    agg_acc = {}
    for k, v in x.items():
        acc_by_date = v.groupby(header["idx"])
        acc_txn_amt = acc_by_date.agg(change=(header["change"], sum))
        ending_bal_column = acc_by_date.last(
        )[header["bal"][1]].rename(header["bal"][2])
        begin_bal_column = ending_bal_column.shift(1).rename(header["bal"][0])
        agg_acc[k] = acc_txn_amt.join([begin_bal_column, ending_bal_column])
        if agg_acc[k].empty:
            agg_acc[k].columns = header["bal"][0], header['change'], header["bal"][2]
            continue
        fst_idx = agg_acc[k].index[0]
        agg_acc[k].at[fst_idx, header["bal"][0]] = round(
            agg_acc[k].at[fst_idx,  header["bal"][2]] - agg_acc[k].at[fst_idx, header['change']], 2)
        agg_acc[k] = agg_acc[k][[header["bal"][0],
                                 header['change'], header["bal"][2]]]

    return agg_acc


def readIssuance(pool):
    _map = {'cn': "发行", 'en': "Issuance"}

    lang_flag = None
    if '发行' in pool.keys():
        lang_flag = 'cn'
    elif 'Issuance' in pool.keys():
        lang_flag = 'en'
    else:
        return None

    validIssuanceFields = {
        "资产池规模": "IssuanceBalance",
        "IssuanceBalance": "IssuanceBalance"
    }

    r = {}
    for k, v in pool[_map[lang_flag]].items():
        if k in validIssuanceFields:
            r[validIssuanceFields[k]] = v
        else:
            logging.warning(
                "Key {k} is not in pool fields {validIssuanceFields.keys()}")
    return r


def show(r, x="full"):
    ''' show cashflow of SPV during the projection '''
    def _map(y):
        if y == 'cn':
            return {"agg_accounts": "账户", "fees": "费用", "bonds": "债券", "pool": "资产池", "idx": "日期"}
        else:
            return {"agg_accounts": "Accounts", "fees": "Fees", "bonds": "Bonds", "pool": "Pool", "idx": "date"}

    _comps = ['agg_accounts', 'fees', 'bonds']

    dfs = {c: pd.concat(r[c].values(), axis=1, keys=r[c].keys())
           for c in _comps if r[c]}

    locale = guess_locale(r)
    _m = _map(locale)

    dfs2 = {}

    for k, v in dfs.items():
        dfs2[_m[k]] = pd.concat([v], keys=[_m[k]], axis=1)

    agg_pool = pd.concat([r['pool']['flow']], axis=1, keys=[_m["pool"]])
    agg_pool = pd.concat([agg_pool], axis=1, keys=[_m["pool"]])

    _full = functools.reduce(lambda acc, x: acc.merge(
        x, how='outer', on=[_m["idx"]]), [agg_pool]+list(dfs2.values()))

    match x:
        case "full":
            return _full.loc[:, [_m["pool"]]+list(dfs2.keys())].sort_index()
        case "cash":
            return None  # ""


def flow_by_scenario(rs, flowpath, annotation=True, aggFunc=None, rnd=2):
    "pull flows from multiple scenario"
    scenario_names = rs.keys()
    locale = guess_locale(list(rs.values())[0])

    def _map(y):
        if y == 'cn':
            return {"idx": "日期"}
        else:
            return {"idx": "date"}

    m = _map(locale)
    dflow = None
    aggFM = {"max": pd.Series.max, "sum": pd.Series.sum, "min": pd.Series.min}

    if aggFunc is None:
        dflows = [query(rs, [s]+flowpath) for s in scenario_names]
    else:
        dflows = [query(rs, [s]+flowpath).groupby(m['idx']).aggregate(
            aggFM.get(aggFunc, aggFunc)) for s in scenario_names]

    if annotation:
        dflows = [f.rename(f"{s}({flowpath[-1]})")
                  for (s, f) in zip(scenario_names, dflows)]
    try:
        return pd.concat(dflows, axis=1).round(rnd)
    except ValueError as e:
        return f"need to pass function to `aggFunc` to aggregate duplication rows, options: Min/Max/Sum "
