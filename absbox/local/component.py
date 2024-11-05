from absbox.local.util import mkTag, mkTs, readTagStr, subMap, subMap2, renameKs, ensure100
from absbox.local.util import mapListValBy, uplift_m_list, mapValsBy, allList, getValWithKs, applyFnToKey,flat
from absbox.local.util import earlyReturnNone, mkFloatTs, mkRateTs, mkRatioTs, mkTbl, mapNone, guess_pool_flow_header
from absbox.local.util import filter_by_tags, enumVals, lmap, readTagMap, patchDicts
from absbox.local.base import *

import sys

from absbox.validation import vDict, vList, vStr, vNum, vInt, vDate, vFloat, vBool
from schema import Or
from enum import Enum
import itertools
import functools
import logging
import toolz as tz
from lenses import lens

import pandas as pd

numVal = Or(float,int)


def mkLiq(x):
    ''' make pricing method '''
    match x:
        case {"正常余额折价": cf, "违约余额折价": df}:
            return mkTag(("BalanceFactor", [vNum(cf), vNum(df)]))
        case {"CurrentFactor": cf, "DefaultFactor": df}:
            return mkTag(("BalanceFactor", [vNum(cf), vNum(df)]))
        case {"贴现计价": df, "违约余额回收率": r}:
            return mkTag(("PV", [df, vNum(r)]))
        case {"PV": df, "DefaultRecovery": r}:
            return mkTag(("PV", [df, vNum(r)]))
        case _:
            raise RuntimeError(f"Failed to match {x} in Liquidation Method")


def mkDatePattern(x):
    ''' make date pattern, to describe a series of dates'''
    match x:
        case ["DayOfMonth", _d] | ["每月", _d] | ("每月", _d):
            return mkTag(("DayOfMonth", vInt(_d)))
        case ["MonthDayOfYear", _m, _d] | ["每年", _m, _d] | ("每年", _m, _d):
            return mkTag(("MonthDayOfYear",[vInt(_m), vInt(_d)]))
        case ["CustomDate", *_ds]:
            return mkTag(("CustomDate", _ds))
        case ["EveryNMonth", d, n]:
            return mkTag(("EveryNMonth", [vDate(d), vInt(n)]))
        case ["Weekday", n] if n >= 0 and n <= 6:
            return mkTag(("Weekday", vInt(n)))
        case ["All", *_dps] | ["AllDatePattern", *_dps] | ["+", *_dps]:
            return mkTag(("AllDatePattern", lmap(mkDatePattern, _dps)))
        case [">", _d, dp] | ["After", _d, dp] | ["之后", _d, dp]:
            return mkTag(("StartsAt", ["Exc", vDate(_d), mkDatePattern(dp) ]))
        case [">=", _d, dp] :
            return mkTag(("StartsAt", ["Inc", vDate(_d), mkDatePattern(dp) ]))
        case ["<", _d, dp] | ["Before", _d, dp] | ["之前", _d, dp]:
            return mkTag(("EndsAt", ["Exc", vDate(_d), mkDatePattern(dp) ]))
        case ["<=", _d, dp] :
            return mkTag(("EndsAt", ["Inc", vDate(_d), mkDatePattern(dp) ]))
        case ["Exclude", _d, _dps] | ["ExcludeDatePattern", _d, _dps] | ["排除", _d, _dps] | ["-", _d, _dps]:
            return mkTag(("Exclude", [mkDatePattern(_d), [mkDatePattern(_) for _ in _dps]]))
        case ["Offset", _dp, n] | ["OffsetDateDattern", _dp, n] | ["平移", _dp, n]:
            return mkTag(("OffsetBy", [mkDatePattern(_dp), vInt(n)]))
        case _x if (_x in datePattern.values()):
            return mkTag((_x))
        case _x if (_x in datePattern.keys()):
            return mkTag((datePattern[x]))
        case _:
            raise RuntimeError(f"Failed to match {x}")


def getStartDate(x):
    match x:
        case {"封包日": a, "起息日": b, "首次兑付日": c, "法定到期日": d, "收款频率": pf, "付款频率": bf} | \
             {"cutoff": a, "closing": b, "firstPay": c, "stated": d, "poolFreq": pf, "payFreq": bf}:
            return (vDate(a), vDate(b))
        case {"封包日": a, "回款日": d, "分配日": c, "起息日":b} | \
             {"cutoff": a, "closing": b, "payDays": c, "collectDays": d}:
            return (vDate(a), vDate(b))
        case {"归集日": (lastCollected, nextCollect), "兑付日": (pp, np), "法定到期日": c, "收款频率": pf, "付款频率": bf} | \
             {"collect": (lastCollected, nextCollect), "pay": (pp, np), "stated": c, "poolFreq": pf, "payFreq": bf}:
            return (vDate(lastCollected), vDate(pp))
        case _:
            raise RuntimeError(f"Failed to get Start Date from {x}")


def mkDate(x):
    ''' make date component for deal '''
    match x:
        case {"封包日": a, "起息日": b, "首次兑付日": c, "法定到期日": d, "收款频率": pf, "付款频率": bf} | \
             {"cutoff": a, "closing": b, "firstPay": c, "stated": d, "poolFreq": pf, "payFreq": bf}:
            firstCollection = x.get("首次归集日", b)
            mr = x.get("循环结束日", None)
            return mkTag(("PreClosingDates"
                          , [vDate(a), vDate(b), mr, vDate(d), [vDate(firstCollection), mkDatePattern(pf)], [vDate(c), mkDatePattern(bf)]]))
        case {"归集日": (lastCollected, nextCollect), "兑付日": (pp, np), "法定到期日": c, "收款频率": pf, "付款频率": bf} | \
             {"collect": (lastCollected, nextCollect), "pay": (pp, np), "stated": c, "poolFreq": pf, "payFreq": bf}:
            mr = x.get("循环结束日", None)
            return mkTag(("CurrentDates", [[vDate(lastCollected), vDate(pp)],
                                           mr,
                                           vDate(c),
                                           [vDate(nextCollect), mkDatePattern(pf)],
                                           [vDate(np), mkDatePattern(bf)]]))
        case {"回款日": cdays, "分配日": ddays, "封包日": cutoffDate, "起息日": closingDate} | \
                {"poolCollection": cdays, "distirbution": ddays, "cutoff": cutoffDate, "closing": closingDate}:
            return mkTag(("CustomDates", [cutoffDate
                                          , [mkTag(("PoolCollection", [cd, ""])) for cd in cdays]
                                          , closingDate
                                          , [mkTag(("RunWaterfall", [dd, ""])) for dd in ddays]]))
        case _:
            raise RuntimeError(f"Failed to match:{x} in Dates")


def mkDsRate(x):
    if isinstance(x,float):
        return mkDs(("constant", x))
    else:
        return mkDs(x)


def mkFeeType(x):
    match x:
        case {"年化费率": [base, rate]} | {"annualPctFee": [base, rate]}:
            return mkTag(("AnnualRateFee", [mkDs(base), mkDsRate(rate)]))
        case {"百分比费率": [base, _rate]} | {"pctFee": [base, _rate]}:
            rate = mkDsRate(_rate)
            return mkTag(("PctFee", [mkDs(base), rate]))
        case {"固定费用": amt} | {"fixFee": amt}:
            return mkTag(("FixFee", vNum(amt)))
        case {"周期费用": [p, amt]} | {"recurFee": [p, amt]}:
            return mkTag(("RecurFee", [mkDatePattern(p), vNum(amt)]))
        case {"自定义": fflow} | {"customFee": fflow}:
            return mkTag(("FeeFlow", mkTs("BalanceCurve", fflow)))
        case {"计数费用": [p, s, amt]} | {"numFee": [p, s, amt]}:
            return mkTag(("NumFee", [mkDatePattern(p), mkDs(s), amt]))
        case {"差额费用": [ds1, ds2]} | {"targetBalanceFee": [ds1, ds2]}:
            return mkTag(("TargetBalanceFee", [mkDs(ds1), mkDs(ds2)]))
        case {"回款期间费用": amt} | {"byPeriod": amt}:
            return mkTag(("ByCollectPeriod", amt))
        case {"分段费用": [dp, ds, tbl]} | {"byTable": [dp, ds, tbl]}:
            return mkTag(("AmtByTbl", [mkDatePattern(dp), mkDs(ds), tbl]))
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


def mkPoolSource(x):
    match x:
        case "利息" | "Interest" | "利息回款" | "CollectedInterest" :
            return "CollectedInterest" 
        case "本金" | "Principal" | "本金回款" | "CollectedPrincipal":
            return "CollectedPrincipal" 
        case "回收" | "Recovery" | "回收回款" | "CollectedRecoveries" :
            return "CollectedRecoveries" 
        case "早偿" | "Prepayment" | "早偿回款" | "CollectedPrepayment":
            return "CollectedPrepayment" 
        case "租金" | "Rental" | "租金回款" | "CollectedRental":
            return "CollectedRental" 
        case "现金" | "Cash" | "现金回款" | "CollectedCash":
            return "CollectedCash"
        case "费用" | "Fee" | "现金回款" | "CollectedFeePaid":
            return "CollectedFeePaid"
        case "新增违约" | "Defaults":
            return "NewDefaults"
        case "新增拖欠" | "Delinquencies":
            return "NewDelinquencies"
        case "新增损失" | "Losses":
            return "NewLosses"
        case "余额" | "Balance":
            return "CurBalance"
        case "期初余额" | "BegBalance":
            return "CurBegBalance"
        case _ :
            raise RuntimeError(f"not match found: {x} :make Pool Source")


@functools.lru_cache(maxsize=128)
def mkDs(x):
    "Making Deal Stats"
    match x:
        case ("债券余额",) | ("bondBalance",):
            return mkTag("CurrentBondBalance")
        case ("债券余额", *bnds) | ("bondBalance", *bnds):
            return mkTag(("CurrentBondBalanceOf", vList(bnds, str)))
        case ("债券应付本金", *bnds) | ("bondDuePrin", *bnds):
            return mkTag(("BondDuePrin", vList(bnds, str)))
        case ("初始债券余额",*bnds) | ("originalBondBalance",*bnds):
            if bnds:
                return mkTag(("OriginalBondBalanceOf", vList(bnds, str)))
            return mkTag("OriginalBondBalance")
        case ("到期月份", bn) | ("monthsTillMaturity", bn):
            return mkTag(("MonthsTillMaturity", vStr(bn)))
        case ("资产池余额", *pNames) | ("poolBalance", *pNames):
            if pNames:
                return mkTag(("CurrentPoolBalance", lmap(mkPid,pNames)))
            return mkTag(("CurrentPoolBalance", None))
        case ("资产池期初余额", *pNames) | ("poolBegBalance", *pNames):
            if pNames:
                return mkTag(("CurrentPoolBegBalance", lmap(mkPid,pNames)))
            return mkTag(("CurrentPoolBegBalance", None))
        case ("初始资产池余额", *pNames) | ("originalPoolBalance", *pNames):
            if pNames:
                return mkTag(("OriginalPoolBalance", lmap(mkPid,pNames)))
            return mkTag(("OriginalPoolBalance", None))
        case ("资产池违约余额", *pNames) | ("currentPoolDefaultedBalance", *pNames): #DEPRECATE
            if pNames:
                return mkTag(("CurrentPoolDefaultedBalance", lmap(mkPid, pNames)))
            return mkTag(("CurrentPoolDefaultedBalance", None))
        case ("资产池累计违约余额", *pNames) | ("cumPoolDefaultedBalance", *pNames): #DEPRECATE
            if pNames:
                return mkTag(("CumulativePoolDefaultedBalance",lmap(mkPid, pNames)))
            return mkTag(("CumulativePoolDefaultedBalance", None))
        case ("资产池累计违约率", *pNames) | ("cumPoolDefaultedRate", *pNames):  # DEPRECATE
            if pNames:
                return mkTag(("CumulativePoolDefaultedRate", lmap(mkPid,pNames)))
            return mkTag(("CumulativePoolDefaultedRate", None))
        case ("资产池累计违约率", n, *pNames) | ("cumPoolDefaultedRateTill", n, *pNames): # DEPRECATE
            if pNames:
                return mkTag(("CumulativePoolDefaultedRateTill", [n,lmap(mkPid,pNames)]))
            return mkTag(("CumulativePoolDefaultedRateTill", [n,None]))
        case ("资产池累计损失余额", *pNames) | ("cumPoolNetLoss", *pNames): # DEPRECATE
            if pNames:
                return mkTag(("CumulativeNetLoss", lmap(mkPid, pNames)))
            return mkTag(("CumulativeNetLoss", None))
        case ("资产池累计损失率",*pNames) | ("cumPoolNetLossRate",*pNames): # DEPRECATE
            if pNames:
                return mkTag(("CumulativeNetLossRatio", lmap(mkPid,pNames)))
            return mkTag(("CumulativeNetLossRatio", None))
        case ("资产池累计回收额",*pNames) | ("cumPoolRecoveries", *pNames): # DEPRECATE
            if pNames:
                return mkTag(("CumulativePoolRecoveriesBalance",lmap(mkPid,pNames)))
            return mkTag(("CumulativePoolRecoveriesBalance",None))
        case ("资产池累计", pNames, *i) | ("cumPoolCollection", pNames, *i):
            if pNames:
                return mkTag(("PoolCumCollection", [lmap(mkPoolSource,i) ,lmap(mkPid,pNames)]))
            return mkTag(("PoolCumCollection", [lmap(mkPoolSource,i), None]))
        case ("资产池累计至", pNames, idx, *i) | ("cumPoolCollectionTill", pNames, idx, *i):
            if pNames:
                return mkTag(("PoolCumCollectionTill", [idx, lmap(mkPoolSource,i) ,lmap(mkPid,pNames)] ))
            return mkTag(("PoolCumCollectionTill", [idx, lmap(mkPoolSource,i), None] ))
        case ("资产池当期", pNames, *i) | ("curPoolCollection", pNames, *i):
            if pNames:
                return mkTag(("PoolCurCollection", [lmap(mkPoolSource,i), lmap(mkPid,pNames)]))
            return mkTag(("PoolCurCollection", [lmap(mkPoolSource,i), None]))
        case ("资产池当期至", pNames, idx, *i) | ("curPoolCollectionStats", pNames, idx, *i):
            if pNames:
                return mkTag(("PoolCurCollectionStats", [idx, lmap(mkPoolSource,i), lmap(mkPid,pNames)]))
            return mkTag(("PoolCollectionStats", [idx, lmap(mkPoolSource,i), None]))
        case ("计划资产池估值", pricingMethod, *pNames) | ("schedulePoolValuation", pricingMethod, *pNames):
            if pNames:
                return mkTag(("PoolScheduleCfPv", [mkLiqMethod(pricingMethod), lmap(mkPid,pNames)]))
            return mkTag(("PoolScheduleCfPv", [mkLiqMethod(pricingMethod), None]))
        case ("债券系数", bn) | ("bondFactor", bn):
            return mkTag(("BondFactorOf", bn))
        case ("债券系数",) | ("bondFactor",):
            return mkTag("BondFactor")
        case ("资产池系数", *pNames) | ("poolFactor", *pNames):
            if pNames:
                return mkTag(("PoolFactor", lmap(mkPid,pNames)))
            return mkTag(("PoolFactor", None))
        case ("债券利率", bn) | ("bondRate", bn):
            return mkTag(("BondRate", vStr(bn)))
        case ("债券加权利率", *bn) | ("bondWaRate", *bn):
            return mkTag(("BondWaRate", vList(bn, str)))
        case ("资产池利率", *pNames) | ("poolWaRate", *pNames):
            if pNames:
                return mkTag(("PoolWaRate", lmap(mkPid, pNames)))
            return mkTag(("PoolWaRate", None))
        case ("所有账户余额",) | ("accountBalance"):
            return mkTag("AllAccBalance")
        case ("账户余额", *ans) | ("accountBalance", *ans):
            return mkTag(("AccBalance", vList(ans, str)))
        case ("账簿余额", *ans) | ("ledgerBalance", *ans):
            return mkTag(("LedgerBalance", vList(ans, str)))
        case ("账簿发生额", lns, cmt) | ("ledgerTxnAmount", lns, cmt):
            return mkTag(("LedgerTxnAmt", [vStr(lns), mkComment(cmt)]))
        case ("账簿发生额", lns) | ("ledgerTxnAmount", lns):
            return mkTag(("LedgerTxnAmt", [vStr(lns), None]))
        case ("债券待付利息", *bnds) | ("bondDueInt", *bnds):
            return mkTag(("CurrentDueBondInt", vList(bnds, str)))
        case ("债券待付罚息", *bnds) | ("bondDueIntOverInt", *bnds):
            return mkTag(("CurrentDueBondIntOverInt", vList(bnds, str)))
        case ("债券待付合计利息", *bnds) | ("bondDueIntTotal", *bnds):
            return mkTag(("CurrentDueBondIntTotal", vList(bnds, str)))
        case ("债券当期已付利息", *bnds) | ("lastBondIntPaid", *bnds):
            return mkTag(("LastBondIntPaid", vList(bnds, str)))
        case ("债券当期已付本金", *bnds) | ("lastBondPrinPaid", *bnds):
            return mkTag(("LastBondPrinPaid", vList(bnds, str)))
        case ("债券低于目标余额", bn) | ("behindTargetBalance", bn):
            return mkTag(("BondBalanceGap", vStr(bn)))
        case ("已提供流动性", *liqName) | ("liqBalance", *liqName):
            return mkTag(("LiqBalance", liqName))
        case ("流动性额度", *liqName) | ("liqCredit", *liqName):
            return mkTag(("LiqCredit", liqName))
        case ("rateCapNet", n):
            return mkTag(("RateCapNet", n))
        case ("rateSwapNet", n):
            return mkTag(("RateSwapNet", n))
        case ("债务人数量", *pNames) | ("borrowerNumber", *pNames):
            if pNames:
                return mkTag(("CurrentPoolBorrowerNum", lmap(mkPid, pNames)))
            return mkTag(("CurrentPoolBorrowerNum"))
        case ("期数",) | ("periodNum",):
            return mkTag(("ProjCollectPeriodNum"))
        case ("事件", loc, idx) | ("trigger", loc, idx):
            if not loc in dealCycleMap:
                raise RuntimeError(f" {loc} not in map {dealCycleMap}")
            return mkTag(("TriggersStatus", [dealCycleMap[loc], idx]))
        case ("阶段", st) | ("status", st):
            return mkTag(("IsDealStatus", mkStatus(st)))
        case ("待付费用", *fns) | ("feeDue", *fns):
            return mkTag(("CurrentDueFee", fns))
        case ("已付费用", *fns) | ("lastFeePaid", *fns):
            return mkTag(("LastFeePaid", fns))
        case ("费用支付总额", cmt, *fns) | ("feeTxnAmount", cmt, *fns) | ("feeTxnAmt", cmt, *fns):
            return mkTag(("FeeTxnAmt", [fns, cmt]))
        case ("债券支付总额", cmt, *bns) | ("bondTxnAmount", cmt, *bns) | ("bondTxnAmt", cmt, *bns):
            return mkTag(("BondTxnAmt", [bns, cmt]))
        case ("账户变动总额", cmt, *ans) | ("accountTxnAmount", cmt, *ans) | ("accountTxnAmt", cmt, *ans):
            return mkTag(("AccTxnAmt", [ans, cmt]))
        case ("系数", ds, f) | ("factor", ds, f) | ("*", ds, f) if isinstance(f, float):
            return mkTag(("Factor", [mkDs(ds), f]))
        case ("*", *ds):
            return mkTag(("Multiply", lmap(mkDs, ds)))
        case ("Min", *ds) | ("min", *ds):
            return mkTag(("Min", lmap(mkDs, ds)))
        case ("Max", *ds) | ("max", *ds):
            return mkTag(("Max", lmap(mkDs, ds)))
        case ("合计", *ds) | ("sum", *ds) | ("+", *ds):
            return mkTag(("Sum", lmap(mkDs, ds)))
        case ("差额", *ds) | ("substract", *ds) | ("subtract", *ds) | ("-", *ds):
            return mkTag(("Substract", lmap(mkDs, ds)))
        case ("常数", n) | ("constant", n) | ("const", n):
            return mkTag(("Constant", n))
        case ("储备账户缺口", *accs) | ("reserveGap", *accs):
            return mkTag(("ReserveAccGap", accs))
        case ("储备账户盈余", *accs) | ("reserveExcess", *accs):
            return mkTag(("ReserveExcess", accs))
        case ("最优先", bn, bns) | ("isMostSenior", bn, bns):
            return mkTag(("IsMostSenior", bn, bns))
        case ("清偿完毕", *bns) | ("isPaidOff", *bns):
            return mkTag(("IsPaidOff", bns))
        case ("isOutstanding", *bns):
            return mkTag(("IsOutstanding", bns))
        case ("逾期", *bns) | ("hasPassedMaturity", *bns):
            return mkTag(("HasPassedMaturity",bns))
        case ("比率测试", ds, op, r) | ("rateTest", ds, op, r):
            return mkTag(("TestRate", [mkDs(ds), op_map[op], r]))
        case ("所有测试", b, *ds) | ("allTest", b, *ds):
            return mkTag(("TestAll", [b, [mkDs(_) for _ in ds]]))
        case ("非", ds) | ("not", ds):
            return mkTag(("TestNot", mkDs(ds)))
        case ("任一测试", b, *ds) | ("anyTest", b, *ds):
            return mkTag(("TestAny", [b, [mkDs(_) for _ in ds]]))
        case ("自定义", n) | ("custom", n):
            return mkTag(("UseCustomData", n))
        case ("区间内", floor, cap, s) | ("floorCap", floor, cap, s):
            return mkTag(("FloorAndCap", [floor, cap, s]))
        case ("floorWith", ds1, ds2):
            return mkTag(("FloorWith", [mkDs(ds1), mkDs(ds2)]))
        case ("floorWithZero", ds1):
            return mkTag(("FloorWithZero", mkDs(ds1)))
        case ("excess", ds1, *dss) | ("超额", ds1, *dss):
            return mkTag(("Excess", [mkDs(ds1)]+[mkDs(_) for _ in dss]))
        case ("capWith", ds1, ds2):
            return mkTag(("CapWith", [mkDs(ds1), mkDs(ds2)]))
        case ("/", ds1, ds2) | ("divide", ds1, ds2):
            return mkTag(("Divide", [mkDs(ds1), mkDs(ds2)]))
        case ("比例", ds1, ds2) | ("ratio", ds1, ds2):
            return mkTag(("DivideRatio", [mkDs(ds1), mkDs(ds2)]))
        case ("abs", ds):
            return mkTag(("Abs", mkDs(ds)))
        case ("avg", *ds) | ("平均", *ds):
            return mkTag(("Avg", [mkDs(_) for _ in ds]))
        case ("avgRatio", *ds) | ("平均比例", *ds):
            return mkTag(("AvgRatio", [mkDs(_) for _ in ds]))
        case _:
            raise RuntimeError(f"Failed to match DS/Formula: {x}")


def mkCurve(tag, xs):
    
    return mkTag((tag, xs))


def mkPre(p):
    def queryType(y):
        match y:
            case (_y, *_) if _y in rateLikeFormula:
                return "IfRate"
            case ("avg", *ds) if set([_[0] for _ in ds]).issubset(rateLikeFormula):
                return "IfRate"
            case (_y, *_) if _y in intLikeFormula:
                return "IfInt"
            case _:
                return "If"

    match p:
        case ["状态", _st] | ["status", _st]:
            return mkTag(("IfDealStatus", mkStatus(_st)))
        case ["同时满足", *_p] | ["同时", *_p] | ["all", *_p]:
            return mkTag(("All", [mkPre(p) for p in _p]))
        case ["任一满足", *_p] | ["任一", *_p] | ["any", *_p]:
            return mkTag(("Any", [mkPre(p) for p in _p]))
        case ["非", _p] | ["not", _p]:
            return mkTag(("IfNot", mkPre(p)))

        case ["date", "between" ,rngType, d1, d2] | ["date","><",rngType, d1, d2]:
            return mkTag(("IfDateBetween", [rngType, vDate(d1), vDate(d2)]))
        case ["date", "in", *vs]:
            return mkTag(("IfDateIn", [vDate(v) for v in vs]))
        case ["date", op, v]:
            return mkTag(("IfDate", [op_map[op], vDate(v)]))

        case ["period", "between", rngType, d1, d2] | ["period", "><", rngType, d1, d2]:
            return mkTag(("IfIntBetween", [mkDs(("periodNum",)), rngType, vNum(d1), vNum(d2)]))
        case ["period", "in", *vs]:
            return mkTag(("IfIntIn", [mkDs(("periodNum",)), [vNum(v) for v in vs]]))
        case ["period", op, v]:
            return mkTag(("IfInt", [op_map[op], mkDs(("periodNum",)), vNum(v)]))

        case [ds, "=", 0]:
            return mkTag(("IfZero", mkDs(ds)))
        case [ds, b] | [ds, b] if isinstance(b, bool):
            return mkTag(("IfBool", [mkDs(ds), b]))
        case [ds1, op, ds2] if (isinstance(ds1, tuple) and isinstance(ds2, tuple)):
            q = queryType(ds1)
            return mkTag((f"{q}2", [op_map[op], mkDs(ds1), mkDs(ds2)]))
        case [ds, op, curve] if isinstance(curve, list):
            q = queryType(ds)
            return mkTag((f"{q}Curve", [op_map[op], mkDs(ds), mkCurve("ThresholdCurve", curve)]))
        case [ds, op, n]:
            q = queryType(ds)
            return mkTag((q, [op_map[op], mkDs(ds), n]))
        case [op, _d]:
            return mkTag(("IfDate", [op_map[op], _d]))
        case _:
            raise RuntimeError(f"Failed to match on Pre: {p}")


def mkAccInt(x):
    match x:
        case {"周期": _dp, "利率": idx, "利差": spd, "最近结息日": lsd} \
                | {"period": _dp,  "index": idx, "spread": spd, "lastSettleDate": lsd}:
            return mkTag(("InvestmentAccount", [idx, spd, lsd, mkDatePattern(_dp)]))
        case {"周期": _dp, "利率": br, "最近结息日": lsd} \
                | {"period": _dp, "rate": br, "lastSettleDate": lsd}:
            return mkTag(("BankAccount", [br, lsd, mkDatePattern(_dp)]))
        case None:
            return None
        case _:
            raise RuntimeError(
                f"Failed to match on account interest definition: {x}")


def mkAccType(x):
    match x:
        # fixed amount
        case ("固定", amt) | ("fix", amt) | {"固定储备金额": amt} | {"fixReserve": amt}:
            return mkTag(("FixReserve", vNum(amt)))
        case ("目标", base, rate) | ("target", base, rate) | {"目标储备金额": [base, rate]} | {"targetReserve": [base, rate]}:
            match base:
                case ("合计", *qs) | ("sum", *qs) | ["合计", *qs] | ["Sum", *qs]:
                    sumDs = lmap(mkDs, qs)
                    return mkTag(("PctReserve", [mkTag(("Sum", sumDs)), vNum(rate)]))
                case _:
                    return mkTag(("PctReserve", [mkDs(base), vNum(rate)]))
        # formula and rate
        case {"目标储备金额": {"公式": ds, "系数": rate}} | {"targetReserve": {"formula": ds, "factor": rate}}:
            return mkTag(("PctReserve", [mkDs(ds), vNum(rate)]))
        case ("目标", ds, rate) | ("target", ds, rate):
            return mkTag(("PctReserve", [mkDs(ds), vNum(rate)]))
        case ("目标", ds) | ("target", ds):
            return mkTag(("PctReserve", [mkDs(ds), 1.0]))
        # higher
        case {"较高": _s} | {"max": _s} if isinstance(_s, list):
            return mkTag(("Max", lmap(mkAccType, _s)))
        case ("较高", *_s) | ("max", *_s):
            return mkTag(("Max", lmap(mkAccType, _s)))
        # lower
        case {"较低": _s} | {"min": _s} if isinstance(_s, list):
            return mkTag(("Min", lmap(mkAccType, _s)))
        case ("较低", *_s) | ("min", *_s):
            return mkTag(("Min", lmap(mkAccType, _s)))
        # with predicate
        case ("分段", p, a, b) | ("when", p, a, b):
            return mkTag(("Either", [mkPre(p), mkAccType(a), mkAccType(b)]))
        case {"分段": [p, a, b]} | {"when": [p, a, b]}:
            return mkTag(("Either", [mkPre(p), mkAccType(a), mkAccType(b)]))
        case None:
            return None
        case _:
            raise RuntimeError(f"Failed to match {x} for account reserve type")


def mkAccTxn(xs: list):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [mkTag(("AccTxn", x)) for x in xs]


def mkAcc(an, x=None):
    match x:
        case {"余额": b, "类型": t, "计息": i, "记录": tx} | {"balance": b, "type": t, "interest": i, "txn": tx}:
            return {"accBalance": vNum(b), "accName": vStr(an), "accType": mkAccType(t), "accInterest": mkAccInt(i), "accStmt": mkAccTxn(tx)}

        case {"余额": b} | {"balance": b}:
            return mkAcc(vStr(an), x | {"计息": x.get("计息", None), "interest": x.get("interest", None), "记录": x.get("记录", None), "txn": x.get("txn", None), "类型": x.get("类型", None), "type": x.get("type", None)})
        case None:
            return mkAcc(vStr(an), {"balance": 0})
        case _:
            raise RuntimeError(f"Failed to match account: {an},{x}")


def mkBondType(x):
    match x:
        case {"固定摊还": schedule} | {"PAC": schedule}:
            return mkTag(("PAC", mkTag(("BalanceCurve", schedule))))
        case {"过手摊还": None} | {"Sequential": None}:
            return mkTag(("Sequential"))
        case {"锁定摊还": _after} | {"Lockout": _after}:
            return mkTag(("Lockout", vDate(_after)))
        case {"权益": _} | {"Equity": _}:
            return mkTag(("Equity"))
        case _:
            raise RuntimeError(f"Failed to match bond type: {x}")

def mkBondIoItype(x):
    match x:
        case ("上浮", f) | ("inflate", f):
            return mkTag(("OverCurrRateBy", vNum(f)))
        case ("利差", spd) | ("spread", spd):
            return mkTag(("OverFixSpread", vNum(spd)))
        case _:
            raise RuntimeError(f"Failed to match bond IoI type:{x}")


def mkBondRate(x):
    match x:
        case {"浮动": [r, _index, Spread, resetInterval], "日历": dc} | \
                {"floater": [r, _index, Spread, resetInterval], "dayCount": dc}:
            return mkTag(("Floater", [r, _index, Spread, mkDatePattern(resetInterval), dc, None, None]))
        case {"浮动": [r, _index, Spread, resetInterval]} | \
             {"floater": [r, _index, Spread, resetInterval]} :
            return mkBondRate(x | {"日历": DC.DC_ACT_365F.value, "dayCount": DC.DC_ACT_365F.value})
        case {"固定": _rate, "日历": dc} | {"fix": _rate, "dayCount": dc}:
            return mkTag(("Fix", [vNum(_rate), dc]))
        case {"固定": _rate} | {"Fixed": _rate} | {"fix": _rate}:
            return mkTag(("Fix", [vNum(_rate), DC.DC_ACT_365F.value]))
        case {"期间收益": _yield} | {"interimYield": _yield}:
            return mkTag(("InterestByYield", vNum(_yield)))
        case ("上限", cap, br) | ("cap", cap, br):
            return mkTag(("CapRate", [mkBondRate(br), vNum(cap)]))
        case ("下限", floor, br) | ("floor", floor, br):
            return mkTag(("FloorRate", [mkBondRate(br), vNum(floor)]))
        case ("罚息", pRateInfo,bRateInfo) | ("withIntOverInt", pRateInfo, bRateInfo):
            return mkTag(("WithIoI", [mkBondRate(bRateInfo), mkBondIoItype(pRateInfo)]))
        case _:
            raise RuntimeError(f"Failed to match bond rate type:{x}")


def mkStepUp(x):
    match x:
        case ("ladder", d, spd, dp):
            return mkTag(("PassDateLadderSpread", [d, vNum(spd), mkDatePattern(dp)]))
        case ("once", d, spd):
            return mkTag(("PassDateSpread", [d, vNum(spd)]))
        case _:
            raise RuntimeError(f"Failed to match bond step up type:{x}")

def mkBndComp(bn,bo):
    """ Make bond component, accept a tuple with (bond name, bond map) or (bond group name, bond map) """
    def itlookslikeaBond(bm:dict):
        try:
            mkBnd("whatever",bm)
        except Exception as e:
            return False
        return True

    match (bn,bo):
        case (bn, bnd) if itlookslikeaBond(bnd): # single bond
            return mkBnd(bn, bnd) | {"tag":"Bond"}
        case (bondGroupName, bndMap) : # bond group
            return mkTag(("BondGroup", {k:mkBnd(k,v) | {"tag":"Bond"} for k,v in bndMap.items() }))
        case _ :
            raise RuntimeError(f"Failed to match bond component")


def mkBnd(bn, x:dict):
    """ Make a single bond object """
    md = getValWithKs(x, ["到期日", "maturityDate"])
    lastAccrueDate = getValWithKs(x, ["计提日", "lastAccrueDate"])
    lastIntPayDate = getValWithKs(x, ["付息日", "lastIntPayDate"])
    dueInt = getValWithKs(x, ["应付利息", "dueInt"], defaultReturn=0)
    dueIntOverInt = getValWithKs(x, ["拖欠利息", "dueIntOverInt"], defaultReturn=0)
    mSt = earlyReturnNone(mkStepUp, getValWithKs(x, ["调息", "stepUp"], defaultReturn=None))
    match x:
        case {"当前余额": bndBalance, "当前利率": bndRate, "初始余额": originBalance, "初始利率": originRate, "起息日": originDate, "利率": bndInterestInfo, "债券类型": bndType} | \
             {"balance": bndBalance, "rate": bndRate, "originBalance": originBalance, "originRate": originRate, "startDate": originDate, "rateType": bndInterestInfo, "bondType": bndType}:
            return {"bndName": vStr(bn), "bndBalance": bndBalance, "bndRate": bndRate
                    , "bndOriginInfo": {"originBalance": originBalance, "originDate": originDate, "originRate": originRate} | {"maturityDate": md}
                    , "bndInterestInfo": mkBondRate(bndInterestInfo), "bndType": mkBondType(bndType)
                    , "bndDuePrin": 0, "bndDueInt": dueInt, "bndDueIntOverInt":dueIntOverInt, "bndDueIntDate": lastAccrueDate, "bndStepUp": mSt
                    , "bndLastIntPayDate": lastIntPayDate}
        case {"初始余额": originBalance, "初始利率": originRate, "起息日": originDate, "利率": bndInterestInfo, "债券类型": bndType} | \
             {"originBalance": originBalance, "originRate": originRate, "startDate": originDate, "rateType": bndInterestInfo, "bondType": bndType}:
            return {"bndName": vStr(bn), "bndBalance": originBalance, "bndRate": originRate
                    , "bndOriginInfo": {"originBalance": originBalance, "originDate": originDate, "originRate": originRate} | {"maturityDate": md}
                    , "bndInterestInfo": mkBondRate(bndInterestInfo), "bndType": mkBondType(bndType)
                    , "bndDuePrin": 0, "bndDueInt": dueInt, "bndDueIntOverInt":dueIntOverInt, "bndDueIntDate": lastAccrueDate, "bndStepUp": mSt
                    , "bndLastIntPayDate": lastIntPayDate}
        case _:
            raise RuntimeError(f"Failed to match bond:{bn},{x}:mkBnd")


def mkLiqMethod(x):
    match x:
        case ["正常|违约", a, b] | ["Current|Defaulted", a, b]:
            return mkTag(("BalanceFactor", [vNum(a), vNum(b)]))
        case ["正常|拖欠|违约", a, b, c] | ["Current|Delinquent|Defaulted", a, b, c]:
            return mkTag(("BalanceFactor2", [vNum(a), vNum(b), vNum(c)]))
        case ["贴现|违约", a, b] | ["PV|Defaulted", a, b]:
            return mkTag(("PV", [a, b]))
        case ["贴现曲线", ts] | ["PVCurve", ts]:
            return mkTag(("PVCurve", mkTs("PricingCurve", ts)))
        case ["贴现率", r] | ["PvRate", r] | ("PvRate", r) if isinstance(r, float):
            return mkTag(("PvRate", r))
        case ["贴现率", r] | ["PvRate", r] | ("PvRate", r):
            return mkTag(("PvByRef", mkDs(r)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkLiqMethod")


def mkPDA(x):
    match x:
        case {"公式": ds} | {"formula": ds}:
            return mkTag(("DS", mkDs(ds)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkPDA")


def mkAccountCapType(x):
    match x:
        case {"余额百分比": pct} | {"balPct": pct}:
            return mkTag(("DuePct", vNum(pct)))
        case {"金额上限": amt} | {"balCapAmt": amt}:
            return mkTag(("DueCapAmt", vNum(amt)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAccountCapType")


def mkLimit(x:dict):
    match x:
       case {"余额百分比": pct} | {"balPct": pct}:
           return mkTag(("DuePct", vFloat(pct)))
       case {"金额上限": amt} | {"balCapAmt": amt}:
           return mkTag(("DueCapAmt", vNum(amt)))
       case {"公式": formula} | {"formula": formula}:
           return mkTag(("DS", mkDs(formula)))
       case {"冲销":(dr, an)} | {"clearLedger": (dr, an)}:
           return mkTag(("ClearLedger", [dr, vStr(an)]))
       case {"簿记":an} | {"bookLedger": an}:
           return mkTag(("BookLedger", vStr(an)))
       case {"系数":[limit, factor]} | {"multiple":[limit, factor]}:
           return mkTag(("Multiple", [mkLimit(limit), vNum(factor)]))
       case {"储备":"缺口"} | {"reserve":"gap"} :
           return mkTag(("TillTarget"))
       case {"储备":"盈余"} | {"reserve":"excess"} :
           return mkTag(("TillSource"))
       case None:
           return None
       case _:
           raise RuntimeError(f"Failed to match :{x}:mkLimit")


def mkComment(x):
    match x:
        case {"payInt":bns}:
            return mkTag(("PayInt",bns))
        case {"payYield":bn}:
            return mkTag(("PayYield",bn))
        case {"transfer":[a1,a2]}:
            return mkTag(("Transfer",[a1,a2]))
        case {"transfer":[a1,a2,limit]}:
            return mkTag(("TransferBy",[a1,a2,limit]))
        case {"direction":d}:
            return mkTag(("TxnDirection",d))


def mkLiqDrawType(x):
    match x:
        case "账户" | "account":
            return "LiqToAcc"
        case "费用" | "fee":
            return "LiqToFee"
        case "债券利息" | "interest":
            return "LiqToBondInt"
        case "债券本金" | "principal":
            return "LiqToBondPrin"
        case _:
            raise RuntimeError(f"Failed to match :{x}:Liquidation Draw Type")


def mkLiqRepayType(x):
    match x:
        case "余额" | "bal" | "balance":
            return mkTag(("LiqBal"))
        case "费用" | "premium" | "fee":
            return mkTag(("LiqPremium"))
        case "利息" | "int" | "interest":
            return mkTag(("LiqInt"))
        case x if isinstance(x, list):
            return mkTag(("LiqRepayTypes", lmap(mkLiqRepayType, x)))
        case _:
            raise RuntimeError(f"Failed to match :{x}:Liquidation Repay Type")


def mkRateSwapType(pr, rr):
    def isFloater(y):
        if isinstance(y, tuple):
            return True
        return False
    match (isFloater(pr), isFloater(rr)):
        case (True, True):
            return mkTag(("FloatingToFloating", [pr, rr]))
        case (False, True):
            return mkTag(("FixedToFloating", [pr, rr]))
        case (True, False):
            return mkTag(("FloatingToFixed", [pr, rr]))
        case _:
            raise RuntimeError(f"Failed to match :{rr,pr}:Interest Swap Type")


def mkRsBase(x):
    match x:
        case {"fix": bal} | {"fixed": bal} | {"固定": bal}:
            return mkTag(("Fixed", vNum(bal)))
        case {"formula": ds} | {"公式": ds}:
            return mkTag(("Base", mkDs(ds)))
        case {"schedule": tbl} | {"计划": tbl}:
            return mkTs("Balance", tbl)
        case _:
            raise RuntimeError(f"Failed to match :{x}:Interest Swap Base")


def mkRateSwap(x):
    match x:
        case {"settleDates": stl_dates, "pair": pair, "base": base
              ,"start": sd, "balance": bal, **p}:
            return {"rsType": mkRateSwapType(*pair),
                    "rsSettleDates": mkDatePattern(stl_dates),
                    "rsNotional": mkRsBase(base),
                    "rsStartDate": vDate(sd),
                    "rsPayingRate": p.get("payRate", 0),
                    "rsReceivingRate": p.get("receiveRate", 0),
                    "rsRefBalance": vNum(bal),
                    "rsLastStlDate": p.get("lastSettleDate", None),
                    "rsNetCash": p.get("netcash", 0),
                    "rsStmt": p.get("stmt", None)
                    }
        case _:
            raise RuntimeError(f"Failed to match :{x}:Interest Swap")


def mkRateCap(x):
    match x:
        case {"index": index, "strike": strike, "base": base, "start": sd
              , "end": ed, "settleDates": dp, "rate": r, **p}:
            return {"rcIndex": index,
                    "rcStrikeRate": mkTs("IRateCurve", strike),
                    "rcNotional": mkRsBase(base),
                    "rcStartDate": vDate(sd),
                    "rcSettleDates": mkDatePattern(dp),
                    "rcEndDate": vDate(ed),
                    "rcReceivingRate": vFloat(r),
                    "rcLastStlDate": p.get("lastSettleDate", None),
                    "rcNetCash": p.get("netcash", 0),
                    "rcStmt": p.get("stmt", None)
                    }
        case _:
            raise RuntimeError(f"Failed to match :{x}:Interest Cap")


def mkRateType(x):
    match x :
        case {"fix":r} | {"固定":r} | ["fix", r] | ["固定", r] | ("fix", r) | ("固定", r):
            return mkTag(("Fix", [DC.DC_ACT_365F.value, vNum(r)]))
        case {"floater":(idx, spd), "rate":r, "reset":dp, **p} | \
            {"浮动":(idx, spd), "利率":r, "重置":dp, **p}:
            mf, mc, mrnd = tz.get(["floor", "cap", "rounding"], p, None)
            dc = p.get("dayCount", DC.DC_ACT_365F.value)
            return mkTag(("Floater",[dc, vStr(idx), vNum(spd), vNum(r), mkDatePattern(dp), mf, mc, mrnd]))
        case ["浮动", r, {"基准":idx, "利差":spd, "重置频率":dp, **p}] | \
             ["floater", r, {"index":idx, "spread":spd, "reset":dp, **p}] :
            mf, mc, mrnd = tz.get(["floor", "cap", "rounding"], p, None)
            dc = p.get("dayCount", DC.DC_ACT_365F.value)
            return mkTag(("Floater", [dc, vStr(idx), vNum(spd), vNum(r), mkDatePattern(dp), mf, mc, mrnd]))
        case ("浮动", r, {"基准":idx, "利差":spd, "重置频率":dp, **p}) | \
             ("floater", r, {"index":idx, "spread":spd, "reset":dp, **p}) :
            mf, mc, mrnd = tz.get(["floor", "cap", "rounding"], p, None)
            dc = p.get("dayCount", DC.DC_ACT_365F.value)
            return mkTag(("Floater", [dc, vStr(idx), vNum(spd), vNum(r), mkDatePattern(dp), mf, mc, mrnd]))
        case None:
            return None
        case _ :
            raise RuntimeError(f"Failed to match :{x}: Rate Type")


def mkBookType(x: list):
    match x:
        case ["PDL", defaults, ledgers] | ["pdl", defaults, ledgers]:
            return mkTag(("PDL",[mkDs(defaults)
                                 ,[[ln, mkDs(ds)] 
                                   for ln, ds in ledgers]]))
        case ["AccountDraw", ledger] | ['accountDraw', ledger]:
            return mkTag(("ByAccountDraw", vStr(ledger)))
        case ["ByFormula", ledger, dr, ds] | ['formula', ledger, dr, ds]:
            return mkTag(("ByDS", [vStr(ledger), dr, mkDs(ds)]))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkBookType")



def mkSupport(x:list):
    match x:
        case ["account", accName, mBookType] | ["suppportAccount", accName, mBookType] | ["支持账户", accName, mBookType]:
            return mkTag(("SupportAccount", [vStr(accName), mkBookType(mBookType)]))
        case ["account", accName] | ["suppportAccount", accName] | ["支持账户", accName]:
            return mkTag(("SupportAccount", [vStr(accName), None]))
        case ["facility", liqName] | ["suppportFacility", liqName] | ["支持机构", liqName]:
            return mkTag(("SupportLiqFacility", vStr(liqName)))
        case ["support", *supports] | ["multiSupport", *supports] | ["多重支持", *supports]:
            return mkTag(("MultiSupport", lmap(mkSupport, supports)))
        case ["withCondition", pre, s] | ["条件支持", pre, s]:
            return mkTag(("WithCondition", [mkPre(pre), mkSupport(s)]))
        case None:
            return None
        case _:
            raise RuntimeError(f"Failed to match :{x}:SupportType")

def mkOrder(x):
    match x:
        case "byName":
            return "ByName"
        case "byProrata":
            return "ByProRataCurBal"
        case "byCurRate":
            return "ByCurrentRate"
        case "byMaturity":
            return "ByMaturity"
        case "byStartDate":
            return "ByStartDate"


def mkAction(x:list):
    ''' make waterfall actions '''
    def mkMod(y: dict) -> tuple:
        limit = getValWithKs(y, ['limit', "限制"], mapping=mkLimit)
        support = getValWithKs(y, ['support', "支持"], mapping=mkSupport)
        return (limit, support)
        
    match x:
        case ["账户转移", source, target, m] | ["transfer", source, target, m]:
            return mkTag(("Transfer", [mkLimit(m), vStr(source), vStr(target), None]))
        case ["账户转移", source, target] | ["transfer", source, target]:
            return mkTag(("Transfer", [None, vStr(source), vStr(target), None]))
        case ["批量账户转移", sources, target] | ["transferMultiple", sources, target] | ["transferM", sources, target]:
            if isinstance(sources, list) and len(sources[0])==2:
                return mkTag(("TransferMultiple", [ [(mkLimit(m), vStr(source)) for (source,m) in sources], vStr(target), None]))
            else:
                return mkTag(("TransferMultiple", [ [(None, vStr(source)) for source in sources], vStr(target), None]))
        case ["簿记", bookType] | ["bookBy", bookType]:
            return mkTag(("BookBy", mkBookType(bookType)))
        case ["计提费用", *feeNames] | ["calcFee", *feeNames]:
            return mkTag(("CalcFee", vList(feeNames, str)))
        case ["特殊计提利息", (mbal, mrate), bndName] | ["calcIntBy", (mbal, mrate), bndName]:
            return mkTag(("CalcBondInt", [[vStr(bndName)]
                                          , earlyReturnNone(mkDs, mbal)
                                          , earlyReturnNone(mkDsRate, mrate)]))
        case ["计提利息", *bndNames] | ["calcInt", *bndNames]:
            return mkTag(("CalcBondInt", [vList(bndNames, str), None, None]))
        case ["计提支付费用", source, target, m] | ["calcAndPayFee", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("CalcAndPayFee", [l, vStr(source), vList(target, str), s]))
        case ["计提支付费用", source, target] | ["calcAndPayFee", source, target]:
            return mkTag(("CalcAndPayFee", [None, vStr(source), vList(target, str), None]))
        case ["顺序支付费用", source, target, m] | ["payFeeBySeq", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayFeeBySeq", [l, vStr(source), vList(target, str), s]))
        case ["顺序支付费用", source, target] | ["payFeeBySeq", source, target]:
            return mkTag(("PayFeeBySeq", [None, vStr(source), vList(target, str), None]))
        case ["支付费用", source, target, m] | ["payFee", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayFee", [l, vStr(source), vList(target, str), s]))
        case ["支付费用", source, target] | ["payFee", source, target]:
            return mkTag(("PayFee", [None, vStr(source), vList(target, str), None]))
        case ["支付费用收益", source, target, limit] | ["payFeeResidual", source, target, limit]:
            return mkTag(("PayFeeResidual", [mkLimit(limit), vStr(source), vStr(target)]))
        case ["支付费用收益", source, target] | ["payFeeResidual", source, target]:
            return mkTag(("PayFeeResidual", [None, vStr(source), vStr(target)]))
        case ["计提支付利息", source, target, m] | ["accrueAndPayInt", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("AccrueAndPayInt", [l, vStr(source), vList(target, str), s]))
        case ["顺序计提支付利息", source, target, m] | ["accrueAndPayIntBySeq", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("AccrueAndPayIntBySeq", [l, vStr(source), vList(target, str), s]))
        case ["计提支付利息", source, target] | ["accrueAndPayInt", source, target]:
            return mkTag(("AccrueAndPayInt", [None, vStr(source), vList(target, str), None]))
        case ["顺序计提支付利息", source, target] | ["accrueAndPayIntBySeq", source, target]:
            return mkTag(("AccrueAndPayIntBySeq", [None, vStr(source), vList(target, str), None]))
        case ["支付利息", source, target, m] | ["payInt", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayInt", [l, vStr(source), vList(target, str), s]))
        case ["顺序支付利息", source, target, m] | ["payIntBySeq", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayIntBySeq", [l, vStr(source), vList(target, str), s]))
        case ["支付罚息", source, target, m] | ["payIntOverInt", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayIntOverInt", [l, vStr(source), vList(target, str), s]))
        case ["顺序支付罚息", source, target, m] | ["payIntOverIntBySeq", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayIntOverIntBySeq", [l, vStr(source), vList(target, str), s]))
        case ["支付利息", source, target] | ["payInt", source, target]:
            return mkTag(("PayInt", [None, vStr(source), vList(target, str), None]))
        case ["顺序支付利息", source, target] | ["payIntBySeq", source, target]:
            return mkTag(("PayIntBySeq", [None, vStr(source), vList(target, str), None]))
        case ["顺序支付本金", source, target, m] | ["payPrinBySeq", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayPrinBySeq", [l, vStr(source), vList(target, str), s]))
        case ["顺序支付本金", source, target] | ["payPrinBySeq", source, target]:
            return mkTag(("PayPrinBySeq", [None, vStr(source), vList(target, str), None]))
        case ["计提应付本金", source, target, m] | ["calcBondPrin", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("CalcBondPrin", [l, vStr(source), vList(target, str),s]))
        case ["计提应付本金", target, limit] | ["calcBondPrin", target, limit]:
            return mkTag(("CalcBondPrin2", [mkLimit(limit), vList(target, str)]))
        case ["支付计提本金", source, target] | ["payPrinWithDue", source, target]:
            return mkTag(("PayPrinWithDue", [vStr(source), vList(target, str), None])) 
        case ["支付本金", source, target, m] | ["payPrin", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayPrin", [l, vStr(source), vList(target, str), s]))
        case ["支付本金","组",source, target, o, m] | ["payPrinByGroup", source, target,o, m]:
            (l, s) = mkMod(m)
            byOrder = mkOrder(o)
            return mkTag(("PayPrinGroup", [l, vStr(source), vStr(target), byOrder,s]))
        case ["支付本金","组",source, target, o] | ["payPrinByGroup", source, target, o]:
            byOrder = mkOrder(o)
            return mkTag(("PayPrinGroup", [None, vStr(source), vStr(target), byOrder, None]))
        case ["计提利息","组",targets] | ["calcIntByGroup", targets]:
            return mkTag(("AccrueIntGroup", vList(targets, str)))
        case ["支付利息","组",source, target, o, m] | ["payIntByGroup", source, target,o, m]:
            (l, s) = mkMod(m)
            byOrder = mkOrder(o)
            return mkTag(("PayIntGroup", [l, vStr(source), vStr(target),byOrder,s]))
        case ["支付利息","组",source, target, o] | ["payIntByGroup", source, target, o]:
            byOrder = mkOrder(o)
            return mkTag(("PayIntGroup", [None, vStr(source), vStr(target),byOrder,None]))
        case ["计提支付利息","组",source, target, o, m] | ["accrueAndPayIntByGroup", source, target,o, m]:
            (l, s) = mkMod(m)
            byOrder = mkOrder(o)
            return mkTag(("AccrueAndPayIntGroup", [l, vStr(source), vStr(target),byOrder,s]))
        case ["计提支付利息","组",source, target, o] | ["accrueAndPayIntByGroup", source, target,o]:
            byOrder = mkOrder(o)
            return mkTag(("AccrueAndPayIntGroup", [None, vStr(source), vStr(target),byOrder,None]))
        case ["减记本金", target, l] | ["writeOff", target, l] if isinstance(target, str):
            limit = mkLimit(l) if l else None
            return mkTag(("WriteOff", [limit, vStr(target)]))
        case ["减记本金", targets, l] | ["writeOff", targets, l] if isinstance(targets, list):
            limit = mkLimit(l) if l else None
            return mkTag(("WriteOffBySeq", [limit, vList(targets,str)]))
        case ["募集本金", source, target, l] | ["fundWith", source, target, l]:
            limit = mkLimit(l) if l else None
            return mkTag(("FundWith", [limit, vStr(source), vStr(target)]))
        case ["支付本金", source, target] | ["payPrin", source, target]:
            return mkTag(("PayPrin", [None, vStr(source), vList(target, str), None]))
        case ["支付剩余本金", source, target] | ["payPrinResidual", source, target]:
            return mkTag(("PayPrinResidual", [vStr(source), vList(target, str)]))
        case ["支付收益", source, target, m] | ["payIntResidual", source, target, m]:
            (l, s) = mkMod(m)
            return mkTag(("PayIntResidual", [l, vStr(source), vStr(target)]))
        case ["支付收益", source, target] | ["payIntResidual", source, target]:
            return mkTag(("PayIntResidual", [None, vStr(source), vStr(target)]))
        case ["出售资产", liq, target, pNames] | ["sellAsset", liq, target, pNames]:
            return mkTag(("LiquidatePool", [mkLiqMethod(liq), vStr(target), lmap(mkPid,pNames)]))
        case ["出售资产", liq, target] | ["sellAsset", liq, target]:
            return mkTag(("LiquidatePool", [mkLiqMethod(liq), vStr(target), None]))
        case ["流动性支持", source, liqType, target, limit] | ["liqSupport", source, liqType, target, limit]:
            return mkTag(("LiqSupport", [mkLimit(limit), vStr(source), mkLiqDrawType(liqType), vStr(target)]))
        case ["流动性支持", source, liqType, target] | ["liqSupport", source, liqType, target]:
            return mkTag(("LiqSupport", [None, vStr(source), mkLiqDrawType(liqType), vStr(target)]))
        case ["流动性支持偿还", rpt, source, target] | ["liqRepay", rpt, source, target]:
            return mkTag(("LiqRepay", [None, mkLiqRepayType(rpt), vStr(source), vStr(target)]))
        case ["流动性支持偿还", rpt, source, target, limit] | ["liqRepay", rpt, source, target, limit]:
            return mkTag(("LiqRepay", [mkLimit(limit), mkLiqRepayType(rpt), vStr(source), vStr(target)]))
        case ["流动性支持报酬", source, target] | ["liqRepayResidual", source, target]:
            return mkTag(("LiqYield", [None, vStr(source), vStr(target)]))
        case ["流动性支持报酬", source, target, limit] | ["liqRepayResidual", source, target, limit]:
            return mkTag(("LiqYield", [mkLimit(limit), vStr(source), vStr(target)]))
        case ["流动性支持计提", *target] | ["liqAccrue", *target]:
            return mkTag(("LiqAccrue", vList(target,str)))
        ## Rate Swap
        case ["结算", acc, swapName] | ["settleSwap", acc, swapName]:
            return mkTag(("SwapSettle", [vStr(acc), vStr(swapName)]))
        ## Rate Cap
        case ["利率结算", acc, capName] | ["settleCap", acc, capName]:
            return mkTag(("CollectRateCap", [vStr(acc), vStr(capName)]))
        case ["条件执行", pre, *actions] | ["If", pre, *actions]:
            return mkTag(("ActionWithPre", [mkPre(pre), lmap(mkAction,actions)]))
        case ["条件执行2", pre, actions1, actions2] | ["IfElse", pre, actions1, actions2]:
            return mkTag(("ActionWithPre2", [mkPre(pre), lmap(mkAction,actions1), lmap(mkAction,actions2)]))
        ## Revolving buy
        ### Revolving buy with optional limit and target pool
        case ["购买资产", liq, source, _limit, mPns] | ["buyAsset", liq, source, _limit, mPns]:
            return mkTag(("BuyAsset", [mkLimit(_limit), mkLiqMethod(liq), vStr(source), lmap(mkPid, mPns)]))
        ### Revolving buy with optional limit and default pool
        case ["购买资产", liq, source, _limit] | ["buyAsset", liq, source, _limit]:
            return mkTag(("BuyAsset", [mkLimit(_limit), mkLiqMethod(liq), vStr(source), None]))
        ### Revolving buy with all cash and default pool
        case ["购买资产", liq, source] | ["buyAsset", liq, source]:
            return mkTag(("BuyAsset", [None, mkLiqMethod(liq), vStr(source), None]))
        ### Revolving buy with all cash and source/target pool 
        case ["购买资产2", liq, source, _limit, sPool, mPn] | ["buyAsset2", liq, source, _limit, sPool, mPn ]:
            return mkTag(("BuyAssetFrom", [mkLimit(_limit), mkLiqMethod(liq), vStr(source), sPool, mkPid(mPn)]))
        
        ## Trigger
        case ["更新事件", trgName] | ["runTriggers", *trgName] | ["runTrigger", *trgName]:
            return mkTag(("RunTrigger", ["InWF", vList(trgName, str)]))
        ## Inspect
        case ["查看", comment, *ds] | ["inspect", comment, *ds]:
            return mkTag(("WatchVal", [comment, lmap(mkDs, ds)]))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkAction")


def mkStatus(x: tuple|str):
    match x:
        case "摊销" | "Amortizing" | "摊还":
            return mkTag(("Amortizing"))
        case "Warehousing" | "储备":
            return mkTag(("Warehousing", None))
        case ("Warehousing", st) | ("储备", st):
            return mkTag(("Warehousing", mkStatus(st)))
        case "循环" | "Revolving":
            return mkTag(("Revolving"))
        case "RampUp":
            return mkTag(("RampUp"))
        case "加速清偿" | "Accelerated":
            return mkTag(("DealAccelerated", None))
        case "违约" | "Defaulted":
            return mkTag(("DealDefaulted", None))
        case "结束" | "Ended":
            return mkTag(("Ended"))
        case ("设计", st) | ("PreClosing", st) | ("preclosing", st):
            return mkTag(("PreClosing", mkStatus(st)))
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkStatus")


def readStatus(x: dict, locale: str):
    m = dealStatusMap
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
        case {"tag": "Revolving"}:
            return m[locale]['revol']
        case {"tag": "Called"}:
            return m[locale]['called']
        case {"tag": "Warehousing"}:
            return m[locale]['warehousing']
        case _:
            raise RuntimeError(
                f"Failed to read deal status:{x} with locale: {locale}")


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
    if h in set(["资产池累积违约率"
                 , "cumPoolDefaultedRate"
                 , "债券系数"
                 , "bondFactor"
                 , "资产池系数"
                 , "poolFactor"]):
        return True
    return False


def mkTrigger(x: dict):
    match x:
        case {"condition":p, "effects":e, "status":st, "curable":c} | {"条件":p, "效果":e, "状态":st, "重置":c}:
            triggerName = getValWithKs(x,["name", "名称"],defaultReturn="")
            return {"trgName":triggerName
                    ,"trgCondition":mkPre(p)
                    ,"trgEffects":mkTriggerEffect(e)
                    ,"trgStatus":st
                    ,"trgCurable":vBool(c)}
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkTrigger")


def mkTriggerEffect(x):
    match x:
        case ("新状态", s) | ("newStatus", s):
            return mkTag(("DealStatusTo", mkStatus(s)))
        case ("动作", *actions) | ("actions", *actions):
            return mkTag(("RunActions", lmap(mkAction, actions)))
        case ["计提费用", *fn] | ["accrueFees", *fn]:
            return mkTag(("DoAccrueFee", vList(fn, str)))
        case ["新增事件", trg] | ["newTrigger", trg]: # not implementd in Hastructure
            return mkTag(("AddTrigger", mkTrigger(trg)))
        case ["新储备目标", accName, newReserve] | ["newReserveBalance", accName, newReserve]:
            return mkTag(("ChangeReserveBalance", [vStr(accName), mkAccType(newReserve)]))
        case ["结果", *efs] | ["Effects", *efs]:
            return mkTag(("TriggerEffects", [mkTriggerEffect(e) for e in efs]))
        case None:
            return mkTag(("DoNothing"))
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
        "储备": "Warehousing",
    }
    if len(x) == 0:
        return tz.valmap(list, r)
    _k, _v = x.popitem()
    _w_tag = None
    match _k:
        case ("兑付日", "加速清偿") | ("amortizing", "accelerated") | "Accelerated" :
            _w_tag = f"DistributionDay (DealAccelerated Nothing)"
        case ("兑付日", "违约") | ("amortizing", "defaulted") | "Defaulted" | "违约后":
            _w_tag = f"DistributionDay (DealDefaulted Nothing)"
        case "Revolving" | "循环" | "revolving" | ("兑付日", "循环") :
            _w_tag = f"DistributionDay Revolving"
        case ("兑付日","储备") | ("DistributionDay", "Warehousing"):
            _w_tag = f"DistributionDay (Warehousing Nothing)"
        case ("兑付日", _st) | ("amortizing", _st):
            _w_tag = f"DistributionDay {mapping.get(_st, _st)}"
        case "兑付日" | "未违约" | "amortizing" | "Amortizing" | "摊销":
            _w_tag = f"DistributionDay Amortizing"
        case "清仓回购" | "cleanUp":
            _w_tag = "CleanUp"
        case "回款日" | "回款后" | "endOfCollection":
            _w_tag = f"EndOfPoolCollection"
        case "设立日" | "closingDay":
            _w_tag = f"OnClosingDay"
        case "默认" | "default":
            _w_tag = f"DefaultDistribution"
        case "储备" | "Warehousing" | ('Warehousing', None):
            _w_tag = f"Warehousing Nothing"
        case _:
            raise RuntimeError(f"Failed to match :{x}:mkWaterfall with key {_k}")
    
    r[_w_tag] = lmap(mkAction, _v)
    return mkWaterfall(r, x)

def mkRoundingType(x):
    match x:
        case ["floor", r]:
            return mkTag(("RoundFloor", r))
        case ["ceiling", r]:
            return mkTag(("RoundCeil", r))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkRoundingType")

def mkAssetRate(x):
    match x:
        case ["固定", r] | ["fix", r]:
            return mkTag(("Fix", r))
        case ["浮动", r, {"基准": idx, "利差": spd, "重置频率": p} as m]:
            _m = subMap(m, [("cap", None), ("floor", None), ("rounding", None)])
            _m = applyFnToKey(_m, mkRoundingType, 'rounding')
            return mkTag(("Floater", [idx, vNum(spd), vNum(r), mkDatePattern(p), _m['floor'], _m['cap'], _m['rounding']]))
        case ["floater", r, {"index": idx, "spread": spd, "reset": p} as m]:
            _m = subMap(m, [("cap", None), ("floor", None), ("rounding", None)])
            _m = applyFnToKey(_m, mkRoundingType, 'rounding')
            return mkTag(("Floater", [idx, vNum(spd), vNum(r), mkDatePattern(p), _m['floor'], _m['cap'], _m['rounding']]))
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
        case ("PO_FirstN", n):
            return mkTag(("PO_FirstN", n))
        case ("NO_FirstN", n, _pt):
            return mkTag(("NO_FirstN", [n, mkAmortPlan(_pt)]))
        case ("IO_FirstN", n, _pt):
            return mkTag(("IO_FirstN", [n, mkAmortPlan(_pt)]))
        case ("计划还款", ts, Dp) | ("Schedule", ts, Dp):
            return mkTag(("ScheduleRepayment", [mkTs("RatioCurve", ts), mkDatePattern(Dp)]))
        case ("计划还款", ts) | ("Schedule", ts):
            return mkTag(("ScheduleRepayment", [mkTs("RatioCurve", ts), None]))
        case ("Balloon", n):
            return mkTag(("Balloon", n))
        case _:
            raise RuntimeError(f"Failed to match AmortPlan {x}:mkAmortPlan")


def mkArm(x:dict):
    match x:
        case {"initPeriod": ip}:
            exs = tz.get(["firstCap", "periodicCap", "lifeCap", "lifeFloor"], x, None)
            return mkTag(("ARM", [ip]+list(exs)))
        case _:
            raise RuntimeError(f"Failed to match ARM  {x}:mkArm")


def mkAssetStatus(x):
    match x:
        case "正常" | "Current" | "current":
            return mkTag(("Current"))
        case "违约" | "Defaulted" | "defaulted":
            return mkTag(("Defaulted",None))
        case ("违约", d) | ("Defaulted", d) | ("defaulted", d):
            return mkTag(("Defaulted", d))
        case _:
            raise RuntimeError(f"Failed to match asset statuts {x}:mkAssetStatus")


def mkPrepayPenalty(x):
    """ Build Prepayment Penalty Setting """
    if x is None:
        return None
    match x:
        case {"byTerm": [term, rate1, rate2]} | {"按期限": [term, rate1, rate2]}:
            return mkTag(("ByTerm", [vInt(term), vFloat(rate1), vFloat(rate2)]))
        case {"fixAmount": [bal, term]} | {"固定金额": [bal, term]}:
            return mkTag(("FixAmount", [vNum(bal), vInt(term)]))
        case {"fixAmount": [bal]} | {"固定金额": [bal]}:
            return mkTag(("FixAmount", [vNum(bal), None]))
        case {"fixPct": [pct, term]} | {"固定比例": [pct, term]}:
            return mkTag(("FixPct", [vNum(pct), vInt(term)]))
        case {"fixPct": [pct]} | {"固定比例": [pct]}:
            return mkTag(("FixPct", [vNum(pct), None]))
        case {"sliding": [pct, step]} | {"滑动":[ pct, step]}:
            return mkTag(("Sliding", [vNum(pct), vNum(step)]))
        case {"stepDown": ps} | {"阶梯": [ps]}:
            return mkTag(("StepDown", ps))
        case _ :
            raise RuntimeError(f"Failed to match {x}:mkPrepayPenalty")


def mkAccRule(x):
    match vStr(x):
        case "直线" | "Straight" :
            return "StraightLine"
        case "余额递减" | "DecliningBalance" :
            return "DecliningBalance"
        case _ :
            raise RuntimeError(f"Failed to match {x}:mkAccRule")

def mkInvoiceFeeType(x):
    match x :
        case ("Fixed", amt) | ("固定", amt):
            return mkTag(("FixedFee", vNum(amt)))
        case ("FixedRate", rate) | ("固定比例", rate):
            return mkTag(("FixedRateFee", vNum(rate)))
        case ("FactorFee", rate, days, rnd) | ("周期计费", rate, days, rnd):
            return mkTag(("FactorFee", [vNum(rate), vInt(days), rnd]))
        case ("AdvanceRate", rate) | ("提前比例", rate):
            return mkTag(("AdvanceFee", vNum(rate)))
        case ("CompoundFee", *fs) | ("复合计费", *fs):
            return mkTag(("CompoundFee", lmap(mkInvoiceFeeType, fs)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkInvoiceFeeType")

def mkCapacity(x):
    match x: 
        case ("固定", c) | ("Fixed", c):
            return mkTag(("FixedCapacity", vNum(c)))
        case ("按年限", cs) | ("ByTerm", cs):
            return mkTag(("CapacityByTerm", cs))
        case _ :
            raise RuntimeError(f"Failed to match {x}:mkCapacity")

def mkObligor(x:dict) -> dict:
    def mkObligorFields(y:dict) -> dict:
        if not y:
            return {}
        return {k:{"Right":float(v)} if isinstance(v, (int, float)) else {"Left":v} for k,v in y.items() }

    return {
        "obligorId": x.get("id", None),
        "obligorTag": x.get("tag",[]),
        "obligorFields": mkObligorFields(x.get("fields", {}))
    }


def mkAsset(x):
    match x:
        case ["AdjustRateMortgage", {"originBalance": originBalance, "originRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate, "arm": arm}
             , {"currentBalance": currentBalance, "currentRate": currentRate, "remainTerm": remainTerms, "status": status}]:
            borrowerNum = x[2].get("borrowerNum", None)
            prepayPenalty = getValWithKs(x[1],["prepayPenalty","早偿罚息"])
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)

            return mkTag(("AdjustRateMortgage", [{"originBalance": vNum(originBalance),
                                                "originRate": mkRateType(originRate),
                                                "originTerm": vInt(originTerm),
                                                "period": freqMap[freq],
                                                "startDate": vDate(startDate),
                                                "prinType": mkAmortPlan(_type),
                                                "prepaymentPenalty": mkPrepayPenalty(prepayPenalty),
                                                "obligor": obligorInfo
                                                } | mkTag("MortgageOriginalInfo"),
                                                mkArm(arm),
                                                vNum(currentBalance),
                                                vNum(currentRate),
                                                vInt(remainTerms),
                                                borrowerNum,
                                                mkAssetStatus(status)])) 
        case ["按揭贷款", {"放款金额": originBalance, "放款利率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate}, {"当前余额": currentBalance, "当前利率": currentRate, "剩余期限": remainTerms, "状态": status}] | \
                ["Mortgage", {"originBalance": originBalance, "originRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate}, {"currentBalance": currentBalance, "currentRate": currentRate, "remainTerm": remainTerms, "status": status}]:

            borrowerNum = getValWithKs(x[2],["borrowerNum","借款人数量"])
            prepayPenalty = getValWithKs(x[1],["prepayPenalty","早偿罚息"])
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("Mortgage", [ {"originBalance": vNum(originBalance),
                                        "originRate": mkRateType(originRate),
                                        "originTerm": vInt(originTerm),
                                        "period": freqMap[freq],
                                        "startDate": vDate(startDate),
                                        "prinType": mkAmortPlan(_type),
                                        "prepaymentPenalty": mkPrepayPenalty(prepayPenalty),
                                        "obligor": obligorInfo
                                        } | mkTag("MortgageOriginalInfo"),
                                        vNum(currentBalance),
                                        vNum(currentRate),
                                        vInt(remainTerms),
                                        borrowerNum,
                                        mkAssetStatus(status)]))
        case ["贷款", {"放款金额": originBalance, "放款利率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate}, {"当前余额": currentBalance, "当前利率": currentRate, "剩余期限": remainTerms, "状态": status}] \
                | ["Loan", {"originBalance": originBalance, "originRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate}, {"currentBalance": currentBalance, "currentRate": currentRate, "remainTerm": remainTerms, "status": status}]:
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("PersonalLoan", [
                {"originBalance": vNum(originBalance),
                 "originRate": mkRateType(originRate),
                 "originTerm": vInt(originTerm),
                 "period": freqMap[freq],
                 "startDate": vDate(startDate),
                 "prinType": mkAmortPlan(_type),
                 "obligor": obligorInfo
                 } | mkTag("LoanOriginalInfo"),
                vNum(currentBalance),
                vNum(currentRate),
                vInt(remainTerms),
                mkAssetStatus(status)]))
        case ["分期", {"放款金额": originBalance, "放款费率": originRate, "初始期限": originTerm, "频率": freq, "类型": _type, "放款日": startDate}, {"当前余额": currentBalance, "剩余期限": remainTerms, "状态": status}] \
                | ["Installment", {"originBalance": originBalance, "feeRate": originRate, "originTerm": originTerm, "freq": freq, "type": _type, "originDate": startDate}, {"currentBalance": currentBalance, "remainTerm": remainTerms, "status": status}]:
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("Installment", [
                {"originBalance": vNum(originBalance),
                 "originRate": mkRateType(originRate),
                 "originTerm": vInt(originTerm),
                 "period": freqMap[freq],
                 "startDate": vDate(startDate),
                 "prinType": mkAmortPlan(_type),
                 "obligor": obligorInfo
                 } | mkTag("LoanOriginalInfo"),
                vNum(currentBalance),
                vInt(remainTerms),
                mkAssetStatus(status)]))
        case ["租赁", {"固定租金": dailyRate, "初始期限": originTerm, "频率": dp, "起始日": startDate, "状态": status, "剩余期限": remainTerms}] \
                | ["Lease", {"fixRental": dailyRate, "originTerm": originTerm, "freq": dp, "originDate": startDate, "status": status, "remainTerm": remainTerms}]:
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("RegularLease"
                            , [{"originTerm": originTerm, "startDate": startDate, "paymentDates": mkDatePattern(dp), "originRental": dailyRate
                                ,"obligor": obligorInfo} | mkTag("LeaseInfo"), 0, remainTerms, mkAssetStatus(status)]))
        case ["租赁", {"初始租金": dailyRate, "初始期限": originTerm, "频率": dp, "起始日": startDate, "计提周期": accDp, "涨幅": rate, "状态": status, "剩余期限": remainTerms}] \
                | ["Lease", {"initRental": dailyRate, "originTerm": originTerm, "freq": dp, "originDate": startDate, "accrue": accDp, "pct": rate, "status": status, "remainTerm": remainTerms}]:

            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            dailyRatePlan = None
            _stepUpType = "curve" if isinstance(rate, list) else "constant"
            if _stepUpType == "constant":
                dailyRatePlan = mkTag(("FlatRate", [mkDatePattern(accDp), rate]))
            else:
                dailyRatePlan = mkTag(("ByRateCurve", [mkDatePattern(accDp), rate]))
            return mkTag(("StepUpLease", [{"originTerm": originTerm, "startDate": startDate, "paymentDates": mkDatePattern(dp), "originRental": dailyRate, "obligor": obligorInfo} | mkTag("LeaseInfo"), dailyRatePlan, 0, remainTerms, mkAssetStatus(status)]))
        case ["固定资产",{"起始日":sd,"初始余额":ob,"初始期限":ot,"残值":rb,"周期":p,"摊销":ar,"产能":cap}
                      ,{"剩余期限":rt}] \
             |["FixedAsset",{"start":sd,"originBalance":ob,"originTerm":ot,"residual":rb,"period":p,"amortize":ar
                             ,"capacity":cap}
                           ,{"remainTerm":rt}]:
            return mkTag(("FixedAsset",[{"startDate":vDate(sd),"originBalance":vNum(ob),"originTerm":vInt(ot),"residualBalance":vNum(rb)
                                         ,"period":freqMap[p],"accRule":mkAccRule(ar)
                                         ,"capacity":mkCapacity(cap)} | mkTag("FixedAssetInfo")
                                        ,vInt(rt)]))
        case ["Invoice", {"start":sd,"originBalance":ob,"originAdvance":oa,"dueDate":dd,"feeType":ft},{"status":status}] :
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("Invoice",[{"startDate":vDate(sd),"originBalance":vNum(ob),"originAdvance":vNum(oa),"dueDate":vDate(dd),"feeType":mkInvoiceFeeType(ft),"obligor":obligorInfo} | mkTag("ReceivableInfo")
                                     ,mkAssetStatus(status)]))
        case ["Invoice", {"start":sd,"originBalance":ob,"originAdvance":oa,"dueDate":dd},{"status":status}] :
            obligorInfo = getValWithKs(x[1],["obligor","借款人"], mapping=mkObligor)
            return mkTag(("Invoice",[{"startDate":vDate(sd),"originBalance":vNum(ob),"originAdvance":vNum(oa),"dueDate":vDate(dd),"feeType":None,"obligor":obligorInfo} | mkTag("ReceivableInfo")
                                     ,mkAssetStatus(status)]))
        case ["ProjectedFlowFix", cf, dp]:
            return mkTag(("ProjectedFlowFixed",[mkCashFlowFrame(cf) ,mkDatePattern(dp)]))
        case ['ProjectedFlowMix', cf, dp, fixPct, floatPcts]:
            return mkTag(("ProjectedFlowMixFloater",[mkCashFlowFrame(cf) ,mkDatePattern(dp)
                                                   , fixPct, floatPcts]))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkAsset")

def identify_deal_type(x):
    """ identify deal type from 1st asset in asset list  """
    def id_by_pool_assets(z):
        match z:
            case {"assets": [{'tag': 'PersonalLoan'}, *rest]}:
                return "LDeal"
            case {"assets": [{'tag': 'Mortgage'}, *rest]}:
                return "MDeal"
            case {"assets": [{'tag': 'AdjustRateMortgage'}, *rest]}:
                return "MDeal"
            case {"assets": [], "futureCf": cfs} if cfs['contents'][1][0]['tag'] == 'MortgageFlow':
                return "MDeal"
            case {"assets": [{'tag': 'Installment'}, *rest]}:
                return "IDeal"
            case {"assets": [{'tag': 'Lease'}, *rest]} | {"assets": [{'tag': 'RegularLease'}, *rest]}:
                return "RDeal"
            case {"assets": [{'tag': 'StepUpLease'}, *rest]}:
                return "RDeal"
            case {"assets": [{'tag': 'FixedAsset'}, *rest]}:
                return "FDeal"
            case {"assets": [{'tag': 'Invoice'}, *rest]}:
                return "VDeal"
            case {"assets": [{'tag': 'ProjectedFlowMix'}, *rest]} | {"assets": [{'tag': 'ProjectedFlowMixFloater'}, *rest]}:
                return "PDeal"
            case _:
                raise RuntimeError(f"Failed to identify deal type {z}")
    y = None
    #if query(x, ["pool","tag"])=='SoloPool':
    if tz.get_in(["pool","tag"], x)=='SoloPool':
        return id_by_pool_assets(x["pool"]['contents'])
    elif "pool" in x and set(x.keys()) == {"pool"}:
        return id_by_pool_assets(x['pool'])
    elif "pool" in x and x["pool"]['tag']=='MultiPool':
        assetTags = lens['pool']['contents'].Values()['assets'][0]['tag'].collect()(x)
        if len(set(assetTags))>1:
            return "UDeal"
        else:
            return id_by_pool_assets(list(x["pool"]['contents'].values())[0])
    elif "ResecDeal" == x['pool']['tag']:
        vs = [ v['deal'] for k,v in x["pool"]['contents'].items() ]
        assetTypes = set(map(identify_deal_type, vs))
        if len(assetTypes)>1:
            return "UDeal"
        else:
            return list(assetTypes)[0]
    else:
        raise RuntimeError(f"Failed to match pool type {x}")



def mkCallOptionsLegacy(x):
    ''' Build call options (legacy) '''
    match x:
        case {"资产池余额": bal} | {"poolBalance": bal} | ("poolBalance", bal):
            return mkTag(("PoolBalance", vNum(bal)))
        case {"债券余额": bal} | {"bondBalance": bal} | ("bondBalance", bal):
            return mkTag(("BondBalance", vNum(bal)))
        case {"资产池余额剩余比率": factor} | {"poolFactor": factor} | ("poolFactor", factor):
            return mkTag(("PoolFactor", vNum(factor)))
        case {"债券余额剩余比率": factor} | {"bondFactor": factor} | ("bondFactor", factor):
            return mkTag(("BondFactor", vNum(factor)))
        case {"指定日之后": d} | {"afterDate": d} | ("afterDate", d):
            return mkTag(("AfterDate", vDate(d)))
        case ("判断", p) | ("条件", p) | ("if", p) | ("condition", p):
            return mkTag(("Pre", mkPre(p)))
        case {"任意满足": xs} | {"or": xs} | ("any", *xs) | ("or", *xs):
            return mkTag(("Or", lmap(mkCallOptionsLegacy, xs)))
        case {"全部满足": xs} | {"and": xs} | ("all", *xs) | ("all", *xs):
            return mkTag(("And", lmap(mkCallOptionsLegacy, xs)))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkCallOptionsLegacy")


def mkAssumpDefault(x):
    ''' New default assumption for performing assets '''
    match x:
        case {"CDR": r} if isinstance(r, list):
            return mkTag(("DefaultVec", vList(r, numVal)))
        case {"CDRPadding": r} if isinstance(r, list):
            return mkTag(("DefaultVecPadding", vList(r, numVal)))
        case {"CDR": r}:
            return mkTag(("DefaultCDR", vNum(r)))
        case {"ByAmount": (bal, rs)} | {"ByAmt": (bal, rs)}:
            return mkTag(("DefaultByAmt", (vNum(bal), vList(rs,numVal))))
        case "DefaultAtEnd":
            return mkTag(("DefaultAtEnd"))
        case {"DefaultAtEndByRate":(r1,r2)}:
            return mkTag(("DefaultAtEndByRate", [vNum(r1), vNum(r2)]))
        case {"StressByCurve": [curve, assump]}:
            return mkTag(("DefaultStressByTs", [ mkRateTs(curve), mkAssumpDefault(assump)]))
        case _ :
            raise RuntimeError(f"failed to match {x}")


def mkAssumpPrepay(x):
    ''' New prepayment assumption for performing assets '''
    match x:
        case {"CPR": r} if isinstance(r, list):
            return mkTag(("PrepaymentVec", vList(r, numVal)))
        case {"CPRPadding": r} if isinstance(r, list):
            return mkTag(("PrepaymentVecPadding", vList(r, numVal)))
        case {"CPR": r}:
            return mkTag(("PrepaymentCPR", vNum(r)))
        case {"StressByCurve": [curve, assump]}:
            return mkTag(("PrepayStressByTs", [ mkRateTs(curve), mkAssumpPrepay(assump)]))
        case _ :
            raise RuntimeError(f"failed to match {x}")


def mkAssumpDelinq(x):
    ''' New delinquency assumption for performing assets '''
    match x:
        case {"DelinqCDR": cdr, "Lag": lag, "DefaultPct": pct}:
            return mkTag(("DelinqCDR", [cdr, (lag, pct)]))
        case _:
            raise RuntimeError(f"failed to match {x}")


def mkAssumpLeaseGap(x):
    match x:
        case {"Days":d}:
            return mkTag(("GapDays",vInt(d)))
        case {"DaysByAmount":(tbl,d)}:
            return mkTag(("GapDaysByAmount",[tbl, vInt(d)]))
        case _:
            raise RuntimeError(f"failed to match {x}")


def mkAssumpLeaseRent(x):
    match x:
        case {"AnnualIncrease":r}:
            return mkTag(("BaseAnnualRate",vNum(r)))
        case {"CurveIncrease":r}:
            return mkTag(("BaseCurve",vNum(r)))
        case _:
            raise RuntimeError(f"failed to match {x}")


def mkAssumpRecovery(x):
    ''' recovery assumption for defaults from performing assets '''
    match x:
        case {"Rate":r,"Lag":lag}:
            return mkTag(("Recovery",[vNum(r),vInt(lag)]))
        case {"Rate":r,"Timing":ts}:
            assert sum(ts)==1.0,f"Recvoery timing should sum up to 100%,but current sum up to {sum(ts)}"
            return mkTag(("RecoveryTiming",[vNum(r),vList(ts, numVal)]))
        case {"Rate":r, "ByDays": lst}:
            return mkTag(("RecoveryByDays",[vNum(r),lst]))
        case _:
            raise RuntimeError(f"failed to match {x}")


def mkDefaultedAssumption(x):
    ''' default assumption for defaulted assets'''
    match x:
        case ("Defaulted",r,lag,rs):
            return mkTag(("DefaultedRecovery",[r,lag,rs]))
        case _:
            return mkTag(("DummyDefaultAssump"))


def mkDelinqAssumption(x):
    #return "DummyDelinqAssump"
    #return mkTag("DummyDelinqAssump")
    return []


def mkPerfAssumption(x):
    "Make assumption on performing assets"
    def mkExtraStress(y):
        ''' make extra stress for mortgage/loans '''
        if y is None:
            return None
        ## ppy/default time-based stress
        defaultFactor = getValWithKs(y,['defaultFactor',"违约因子"],mapping=mkFloatTs)
        prepayFactor = getValWithKs(y,['prepayFactor',"早偿因子"],mapping=mkFloatTs)
        ## haircuts
        mkHaircut = lambda xs : [ (mkPoolSource(ps),r)  for (ps,r) in xs]
        haircuts = getValWithKs(y,['haircuts','haircut',"折扣"],mapping=mkHaircut)

        return {
            "defaultFactors":defaultFactor,
            "prepaymentFactors":prepayFactor,
            "poolHairCut": haircuts
        }
    match x:
        case ("Mortgage","Delinq",md,mp,mr,mes):
            d = earlyReturnNone(mkAssumpDelinq,md)
            p = earlyReturnNone(mkAssumpPrepay,mp)
            r = earlyReturnNone(mkAssumpRecovery,mr)
            return mkTag(("MortgageDeqAssump",[d,p,r,mkExtraStress(mes)]))
        case ("Mortgage",md,mp,mr,mes):
            d = earlyReturnNone(mkAssumpDefault,md)
            p = earlyReturnNone(mkAssumpPrepay,mp)
            r = earlyReturnNone(mkAssumpRecovery,mr)
            return mkTag(("MortgageAssump",[d,p,r,mkExtraStress(mes)]))
        case ("Lease", gap, rent, endDate):
            return mkTag(("LeaseAssump",[mkAssumpLeaseGap(gap)
                                         ,mkAssumpLeaseRent(rent)
                                         ,endDate
                                         ,None]))
        case ("Loan",md,mp,mr,mes):
            d = earlyReturnNone(mkAssumpDefault,md)
            p = earlyReturnNone(mkAssumpPrepay,mp)
            r = earlyReturnNone(mkAssumpRecovery,mr)
            return mkTag(("LoanAssump",[d,p,r,mkExtraStress(mes)]))
        case ("Installment",md,mp,mr,mes):
            d = earlyReturnNone(mkAssumpDefault,md)
            p = earlyReturnNone(mkAssumpPrepay,mp)
            r = earlyReturnNone(mkAssumpRecovery,mr)
            return mkTag(("InstallmentAssump",[d,p,r,None]))
        case ("Fixed",utilCurve,priceCurve):
            return mkTag(("FixedAssetAssump",[mkTs("RatioCurve",utilCurve)
                                              ,mkTs("BalanceCurve",priceCurve)]))
        case ("Receivable", md, mr, mes):
            d = earlyReturnNone(mkAssumpDefault,md)
            r = earlyReturnNone(mkAssumpRecovery,mr)
            return mkTag(("ReceivableAssump",[d, r, mkExtraStress(mes)]))
        case _:
            raise RuntimeError(f"failed to match {x}")


def mkPDF(a, b, c):
    ''' make assumps asset with 3 status: performing/delinq/defaulted '''
    return [mkPerfAssumption(a)
            ,mkDelinqAssumption(b)
            ,mkDefaultedAssumption(c)]

def mkObligorStrategy(x):
    def mkRule(y):
        match y:
            case ("not", t):
                return mkTag(("TagNot",mkRule(t)))
            case _:
                return mkTag(y)

    def mkFieldRule(z):
        match z:
            case ("not", t):
                return mkTag(("FieldNot",mkFieldRule(t)))
            case (f, "in", lst):
                return mkTag(("FieldIn",[f,lst]))
            case (f, "cmp",cmp,val):
                return mkTag(("FieldCmp",[f,cmp,val]))
            case (f, "range",rng,lowVal,highVal):
                return mkTag(("FieldInRange",[f,rng,lowVal,highVal]))
            case _:
                raise RuntimeError(f"failed to match {z}, mkFieldRule")

    match x:
        case ("ById",ids,assumps)| ("ByID",ids,assumps):
            return mkTag(("ObligorById",[[vStr(i) for i in ids],mkPDF(*assumps)]))
        case ("ByTag", tags, rule, assumps):
            return mkTag(("ObligorByTag",[lmap(mkRule,tags), mkRule(rule),mkPDF(*assumps)]))
        case ("ByField", fieldRules, assumps):
            return mkTag(("ObligorByField",[lmap(mkFieldRule,fieldRules),mkPDF(*assumps)]))
        case ("ByDefault",assumps) | ("_",assumps):
            return mkTag(("ObligorByDefault",mkPDF(*assumps)))
        case _:
            raise RuntimeError(f"failed to match {x}, mkObligorStrategy")


def mkAssumpType(x):
    ''' make assumps either on pool level or asset level '''
    match x:
        case ("Pool", p, d, f):
            return mkTag(("PoolLevel",mkPDF(p, d, f)))
        case ("ByIndex", *ps):
            return mkTag(("ByIndex",[ [idx, mkPDF(a,b,c)] for (idx,(a,b,c)) in ps ]))
        case ("ByObligor",*rules):
            return mkTag(("ByObligor",[mkObligorStrategy(r) for r in rules]))
        case ("ByName", assumpMap):
            return mkTag(("ByName",{f"PoolName:{k}":mkPDF(*v) for k,v in assumpMap.items()}))
        case ("ByPoolId", assumpMap):
            return mkTag(("ByPoolId",{f"PoolName:{k}": mkAssumpType(v) for k,v in assumpMap.items()}))
        case ("ByDealName", assumpMap):
            return mkTag(("ByDealName",{k:(mkAssumpType(perfAssump),mkNonPerfAssumps({},nonPerfAssump)) 
                                        for k,(perfAssump,nonPerfAssump) in assumpMap.items()}))
        case None:
            return None
        case _ :
            raise RuntimeError(f"failed to match {x} | mkAssumpType")


def mkAssetUnion(x):
    match x[0]:
        case "AdjustRateMortgage" | "Mortgage" | "按揭贷款" :
            return mkTag(("MO", mkAsset(x)))
        case "贷款" | "Loan" : 
            return mkTag(("LO", mkAsset(x)))
        case "分期" | "Installment" : 
            return mkTag(("IL", mkAsset(x)))
        case "租赁" | "Lease" : 
            return mkTag(("LS", mkAsset(x)))
        case "固定资产" | "FixedAsset" : 
            return mkTag(("FA", mkAsset(x)))
        case "应收帐款" | "Invoice" : 
            return mkTag(("RE", mkAsset(x)))
        case "ProjectedFlowFix" | "ProjectedFlowMix" :
            return mkTag(("PF", mkAsset(x)))
        case _:
            raise RuntimeError(f"Failed to match AssetUnion {x}")


def mkRevolvingPool(x):
    assert isinstance(x, list), f"Revolving Pool Assumption should be a list, but got {x}"
    'intput with list, return revolving pool'
    match x:
        case ["constant", *asts]|["固定", *asts]:
            return mkTag(("ConstantAsset", lmap(mkAssetUnion, asts)))
        case ["static", *asts]|["静态", *asts]:
            return mkTag(("StaticAsset",lmap(mkAssetUnion, asts)))
        case ["curve", astsWithDates]|["曲线", astsWithDates]:
            assetCurve = [ [d, lmap(mkAssetUnion, asts)] for (d,asts) in astsWithDates ]
            return mkTag(("AssetCurve",assetCurve))


def mkPoolType(assetDate, x, mixedFlag) -> dict:
    if 'assets' in x or "清单" in x or "归集表" in x:
        return mkTag(("SoloPool" ,mkPoolComp(vDate(assetDate), x, False)))
    elif 'deals' in x and isinstance(x['deals'],dict):
        return mkTag(("ResecDeal",{f"{dealObj.json['contents']['name']}:{bn}:{sd}:{str(pct)}": \
                                    {"deal":dealObj.json['contents'],"future":None,"futureScheduleCf":None,"issuanceStat":None}\
                                      for ((bn,pct,sd),dealObj) in x['deals'].items()} ))
    else:
        return mkTag(("MultiPool" ,{f"PoolName:{k}":mkPoolComp(vDate(assetDate),v,mixedFlag) for (k,v) in x.items()}))


def mkPoolComp(asOfDate, x, mixFlag) -> dict:
    assetFactory = mkAsset if (not mixFlag) else mkAssetUnion
    r = {"assets": [assetFactory(y) for y in getValWithKs(x, ['assets', "清单"],defaultReturn=[])]
        , "asOfDate": asOfDate
        , "issuanceStat": getValWithKs(x,["issuanceStat", "统计"])
        , "futureCf":mkCf(getValWithKs(x,['cashflow', '现金流归集表', '归集表'],[]))
        , "extendPeriods":mkDatePattern(getValWithKs(x,['extendBy'], "MonthEnd"))}
    return r


def mkPool(x: dict):
    mapping = {"LDeal": "LPool", "MDeal": "MPool",
               "IDeal": "IPool", "RDeal": "RPool", "FDeal":"FPool",
               "VDeal": "VPool", "UDeal":"UPool"}
    match x:
        case {"清单": assets, "封包日": d} | {"assets": assets, "cutoffDate": d}:
            _pool = {"assets": [mkAsset(a) for a in assets] , "asOfDate": d}
            _pool_asset_type = identify_deal_type({"pool": _pool})
            return mkTag((mapping[_pool_asset_type], _pool))
        case _:
            raise RuntimeError(f"Failed to match {x}:mkPool")


def mkCustom(x: dict):
    match x:
        case {"常量": n} | {"Constant": n}:
            return mkTag(("CustomConstant", n))
        case {"余额曲线": ts} | {"BalanceCurve": ts}:
            return mkTag(("CustomCurve", mkTs("BalanceCurve", ts)))
        case {"公式": ds} | {"Formula": ds}:
            return mkTag(("CustomDS", mkDs(ds)))


def mkLiqProviderType(x):
    match x:
        case {"总额度": amt} | {"total": amt}:
            return mkTag(("FixSupport", amt))
        case {"日期": dp, "限额": amt} | {"reset": dp, "quota": amt}:
            return mkTag(("ReplenishSupport", [mkDatePattern(dp), amt]))
        case {"公式": ds, "系数":pct} | {"formula":ds, "pct":pct}:
            return mkTag(("ByPct", [mkDs(ds), pct]))
        case "unlimit" | "无限额":
            return mkTag(("UnLimit"))
        case {}:
            return mkTag(("UnLimit"))
        case _:
            raise RuntimeError(f"Failed to match LiqProvider Type：{x}")
        

def mkLiqProvider(n: str, x: dict):
    x_transformed = renameKs(x,[("已提供","liqBalance"),("应付利息","liqDueInt"),("应付费用","liqDuePremium")
                                ,("利率","liqRate"),("费率","liqPremiumRate"),("记录","liqStmt")
                                ,("name","liqName"),("type","liqType")
                                ,("credit","liqCredit")
                                ,("dueInt","liqDueInt"),("duePremium","liqDuePremium")
                                ,("rate","liqRate"),("fee","liqPremiumRate")
                                ,("rateType","liqRateType"),("feeType","liqPremiumRateType")
                                ,("dueIntDate","liqDueIntDate")
                                ,("balance","liqBalance")
                                ,("end","liqEnds"),("start","liqStart")
                                ,("stmt","liqStmt")
                                ,("creditCalc","liqCreditCalc")
                                ]
                                ,opt_key=True)

    r = {
        "liqName": vStr(n),
        "liqType": mkLiqProviderType(x_transformed["liqType"]),
        "liqBalance":(x_transformed.get("liqBalance",0)),
        "liqCredit":(x_transformed.get("liqCredit",None)),
        "liqCreditCalc":(x_transformed.get("liqCreditCalc",None)),
        "liqRateType": mkRateType(x_transformed.get("liqRateType",None)),
        "liqPremiumRateType": mkRateType(x_transformed.get("liqPremiumRateType",None)),
        "liqRate":(x_transformed.get("liqRate",None)),
        "liqPremiumRate":(x_transformed.get("liqPremiumRate",None)),
        "liqDueIntDate":(x_transformed.get("liqDueIntDate",None)),
        "liqDueInt":(x_transformed.get("liqDueInt",0)),
        "liqDuePremium":(x_transformed.get("liqDuePremium",0)),
        "liqStart":(x_transformed["liqStart"]),
        "liqEnds":(x_transformed.get("liqEnds",None)),
        "liqStmt": mkAccTxn(x_transformed.get("liqStmt",None))
    }
    return r

def mkLedger(n: str, x: dict=None):
    ''' Build ledger '''
    match x:
        case {"balance":bal} | {"余额":bal}:
            return {"ledgName":vStr(n),"ledgBalance":vNum(bal),"ledgStmt":None}
        case {"balance":bal,"txn":tx} | {"余额":bal, "记录":tx}:
            return {"ledgName":vStr(n),"ledgBalance":vNum(bal),"ledgStmt":mkAccTxn(tx)}
        case None:
            return {"ledgName":vStr(n),"ledgBalance":0,"ledgStmt":None}
        case _:
            raise RuntimeError(f"Failed to match Ledger:{n},{x}")


def mkCf(x:list):
    """ Make project cashflow ( Mortgage Only ) """
    if len(x) == 0:
        return None
    else:
        cfs = [mkTag(("MortgageFlow", _x+[0.0]*5+[None,None,None])) for _x in x]
        return mkTag(("CashFlowFrame", [[0,"1900-01-01",None],cfs]))
    
def mkCashFlowFrame(x):
    """ Make cashflow frame """ 
    flows = x.get("flows",[])
    begBal = x.get("beginBalance",0)
    begDate = x.get("beginDate","1900-01-01")
    accInt = x.get("accruedInterest",None)
    return mkTag(("CashFlowFrame", [[begBal,begDate,accInt], [ mkTag(("MortgageFlow", f+[0.0]*5+[None,None,None] )) for f in flows] ]))


def mkPid(x):
    match x:
        case None:
            return None
        case x if isinstance(x,str):
            return mkTag((f"PoolName",x))
        case x if isinstance(x,str) and x.startswith("Deal-"):
            dealName,bondName = x.split(":")
            return mkTag(("UnderlyingDeal",[dealName,bondName]))


def mkCollection(x):
    """ Build collection rules """
    match x :
        case [s, acc] if isinstance(acc, str) and isinstance(s, str):
            return mkTag(("Collect",[None, mkPoolSource(s), acc]))
        case [s, *pcts] if isinstance(pcts, list) and isinstance(s, str):
            return mkTag(("CollectByPct" ,[None, mkPoolSource(s), pcts]))
        case [None, s, acc] if isinstance(acc, str):
            return mkTag(("Collect",[None, mkPoolSource(s), acc]))
        case [None, s, *pcts] if isinstance(pcts, list):
            return mkTag(("CollectByPct" ,[None, mkPoolSource(s), pcts]))
        case [mPids, s, acc] if isinstance(acc, str):
            return mkTag(("Collect",[lmap(mkPid,mPids), mkPoolSource(s), acc]))
        case [mPids, s, *pcts] if isinstance(pcts, list):
            return mkTag(("CollectByPct" ,[lmap(mkPid,mPids), mkPoolSource(s), pcts]))
        case _:
            raise RuntimeError(f"Failed to match collection rule {x}")


def mkFee(x,fsDate=None):
    match x :
        case {"name":fn, "type": feeType, **fi}:
            opt_fields = subMap(fi, [("feeStart",fsDate),("feeDueDate",None),("feeDue",0),
                                    ("feeArrears",0),("feeLastPaidDate",None)])
            return  {"feeName": vStr(fn), "feeType": mkFeeType(feeType)} | opt_fields
        case {"名称":fn , "类型": feeType, **fi}:
            opt_fields = subMap2(fi, [("起算日","feeStart",fsDate),("计算日","feeDueDate",None),("应计费用","feeDue",0),
                                      ("拖欠","feeArrears",0),("上次缴付日期","feeLastPaidDay",None)])
            return  {"feeName": vStr(fn), "feeType": mkFeeType(feeType)} | opt_fields
        case _:
            raise RuntimeError(f"Failed to match fee: {x}")


def mkPricingAssump(x):
    match x:
        case {"贴现日": pricingDay, "贴现曲线": xs} | {"date": pricingDay, "curve": xs}| {"PVDate": pricingDay, "PVCurve": xs}:
            return mkTag(("DiscountCurve", [vDate(pricingDay), mkTs("IRateCurve", xs)]))
        case {"债券": bnd_with_price, "利率曲线": rdps} | {"bonds": bnd_with_price, "curve": rdps}:
            return mkTag(("RunZSpread", [mkTs("IRateCurve", rdps), bnd_with_price]))
        case _:
            raise RuntimeError(f"Failed to match pricing assumption: {x}")


def readPricingResult(x, locale) -> dict | None:
    if x is None:
        return None
    h = None

    tag = list(x.values())[0]["tag"]
    if tag == "PriceResult":
        h = {"cn": ["估值", "票面估值", "WAL", "久期", "凸性", "应计利息"],
             "en": ["pricing", "face", "WAL", "duration", "convexity", "accure interest"]}
    elif tag == "ZSpread":
        h = {"cn": ["静态利差"], "en": ["Z-spread"]}
    else:
        raise RuntimeError(f"Failed to read princing result: {x} with tag={tag}")

    # 
    if (v:=list(x.values())):
        if len(v[0]['contents'])==6:
            return pd.DataFrame.from_dict(tz.valmap(lambda y:y['contents'],x)
                                  , orient='index', columns=h[locale]).sort_index()

    pricingResult = pd.DataFrame.from_dict(tz.valmap(lambda y:y['contents'][:-1],x)
                                  , orient='index', columns=h[locale]).sort_index()
    #
    return {"summary":pricingResult
           ,"breakdown":tz.valmap(lambda z: pd.DataFrame( [ _['contents'] for _ in z['contents'][-1]], columns=english_bondflow_fields).set_index("date"), x)
           }


def readPoolCf(x, lang='english'):
    r = None
    cflow = x[1]
    _pool_cf_header,_,expandFlag = guess_pool_flow_header(cflow[0], lang)
    if not expandFlag:
        r = pd.DataFrame(list(tz.pluck('contents',cflow)), columns=_pool_cf_header)
    else:
        r = pd.DataFrame([_['contents'][:-1]+mapNone(_['contents'][-1],[None]*6) for _ in cflow]
                                                , columns=_pool_cf_header)
    pool_idx = cfIndexMap[lang]
    r = r.set_index(pool_idx)
    r.index.rename(pool_idx, inplace=True)    
    return r


def readRunSummary(x, locale) -> dict:
    r = {}
    if x is None:
        return None

    bndStatus = {'cn': ["本金违约", "利息违约", "起算余额"]
                ,'en': ["Balance Defaults", "Interest Defaults", "Original Balance"]
                }
    bond_defaults = [(_['contents'][0], _['tag'], _['contents'][1], _['contents'][2])
                     for _ in x if _['tag'] in set(['BondOutstanding', 'BondOutstandingInt'])]
    
    _fmap = {"cn": {'BondOutstanding': "本金违约", "BondOutstandingInt": "利息违约"}
            ,"en": {'BondOutstanding': "Balance Defaults", "BondOutstandingInt": "Interest Defaults"}}
    ## Build bond summary
    
    bndNames = set([y[0] for y in bond_defaults])

    bndSummary = pd.DataFrame(columns=bndStatus[locale], index=list(bndNames))

    for bn, amt_type, amt, begBal in bond_defaults:
        bndSummary.loc[bn, _fmap[locale][amt_type]] = amt
        bndSummary.loc[bn, bndStatus[locale][2]] = begBal
    
    bndSummary.fillna(0, inplace=True)
    bndSummary["Total"] = bndSummary[bndStatus[locale][0]] + \
        bndSummary[bndStatus[locale][1]]

    r['bonds'] = bndSummary
    ## Build status change logs
    status_change_logs = [(_['contents'][0], readStatus(_['contents'][1], locale), readStatus(_['contents'][2], locale))
                          for _ in filter_by_tags(x, ["DealStatusChangeTo"])]
    deal_ended_log = [ (_['contents'][0],"DealEnd",_['contents'][1]) for _ in filter_by_tags(x, ["EndRun"])]
    r['status'] = pd.DataFrame(data=status_change_logs+deal_ended_log, columns=dealStatusLog[locale])

    # inspection variables
    def uplift_ds(df:pd.DataFrame) -> pd.DataFrame:
        ds_name = readTagStr(df['DealStats'].iloc[0])
        df.drop(columns=["DealStats"],inplace=True)
        df.rename(columns={"Value":ds_name},inplace=True)
        df.set_index("Date",inplace=True)
        return df
    inspect_vars = [  c & lens['contents'][2].set(sys.float_info.max) if c['contents'][2]==inf else c  for c in filter_by_tags(x, enumVals(InspectTags))  ]
    if inspect_vars:
        inspect_df = pd.DataFrame(data = [ (c['contents'][0],str(c['contents'][1]),c['contents'][2]) for c in inspect_vars ]
                                ,columns = ["Date","DealStats","Value"])
        grped_inspect_df = inspect_df.groupby("DealStats")

        r['inspect'] = {readTagStr(k):uplift_ds(v) for k,v in grped_inspect_df}

    # inspect variables during waterfall
    r['waterfallInspect'] = None
    waterfall_inspect_vars = filter_by_tags(x, ["InspectWaterfall"])
    if waterfall_inspect_vars:
        waterfall_inspect_df = pd.DataFrame(data = [ (c['contents'][0],str(c['contents'][1]),ds,dsv) 
                                                        for c in waterfall_inspect_vars
                                                         for (ds,dsv) in zip(c['contents'][2],c['contents'][3]) ]
                                            ,columns = ["Date","Comment","DealStats","Value"])
        r['waterfallInspect'] = waterfall_inspect_df
    
    # extract errors and warnings
    error_warning_logs = filter_by_tags(x, enumVals(ValidationMsg))
    r['logs'] = None
    if error_warning_logs:
        error_warnings_by_map = tz.groupby('tag',error_warning_logs)
        errorLogs = [ ["Error",c['contents']] for c in error_warnings_by_map[ValidationMsg.Error.value]] if ValidationMsg.Error.value in error_warnings_by_map else []
        warningLogs = [ ["Warning",c['contents']] for c in error_warnings_by_map[ValidationMsg.Warning.value]] if ValidationMsg.Warning.value in error_warnings_by_map else []
        r['logs'] = pd.DataFrame(data = errorLogs+warningLogs ,columns = ["Type","Comment"])

    # extract waterfall in use 
    waterfall_logs = filter_by_tags(x, ["RunningWaterfall"])
    r['waterfall'] = None
    if waterfall_logs:
        r['waterfall'] = pd.DataFrame(data = [ [c['contents'][0],readTagMap(c['contents'][1])] for c in waterfall_logs ]
                                        ,columns = ["Date","Waterfall Location"])


    # build financial reports
    def mapItem(z):
        match z:
            case {"tag":"Item","contents":[accName,accBal]}:
                return {accName:accBal}
            case {"tag":"ParentItem","contents":[accName,subItems]}:
                items = map(mapItem, subItems)
                return {accName : items}

    def buildBalanceSheet(bsData):
        bsRptDate = bsData.pop("reportDate")
        bs = mapListValBy(bsData, mapItem)
        return mapValsBy(bs, uplift_m_list) | {"reportDate":bsRptDate}

    def buildBsType(yname, y:dict)-> pd.DataFrame:
        mi = pd.MultiIndex.from_product([[yname],y.keys()])
        d = y.values()
        return pd.DataFrame(d, index=mi).T
    
    def buildBS(bs):
        bs_df = pd.concat([  buildBsType(k,v)  for k,v in bs.items() if k!="reportDate"],axis=1)
        bs_df['reportDate'] = bs['reportDate']
        return bs_df.set_index("reportDate")

    def buildCashReport(cashData):
        sd = cashData.pop('startDate')
        ed = cashData.pop('endDate')
        net = cashData.pop('net')
        cashList = mapListValBy(cashData, mapItem)
        cashMap = {k:uplift_m_list(v) for k,v in cashList.items() }
        cashMap = pd.concat([  buildBsType(k,v) for k,v in cashMap.items() ],axis=1)
        cashMap['startDate'] = sd
        cashMap['endDate'] = ed
        cashMap['Net'] = net
        return cashMap.set_index(["startDate","endDate"])

    balanceSheetIdx = 2
    cashReportIdx = 3
    rpts = [ _['contents'] for  _ in  (filter_by_tags(x, ["FinancialReport"])) ]
    if rpts:
        r['report'] = {}
        r['report']['balanceSheet'] = pd.concat([buildBS(buildBalanceSheet(rpt[balanceSheetIdx])) for rpt in rpts])
        r['report']['cash'] = pd.concat([buildCashReport(rpt[cashReportIdx]) for rpt in rpts])[["inflow","outflow","Net"]]
    

    return r


def aggAccs(x, locale):
    """ Aggregate Ending balance for accounts on each day """

    header = accountHeader[locale]
    agg_acc = {}
    for k, v in x.items():
        acc_by_date = v.groupby(header["idx"])
        acc_txn_amt = acc_by_date.agg(change=(header["change"], "sum")).rename(columns={"change":header["change"]})
        
        ending_bal_column = acc_by_date.last()[header["bal"][1]].rename(header["bal"][2])
        begin_bal_column = ending_bal_column.shift(1).rename(header["bal"][0])
        
        agg_acc[k] = acc_txn_amt.join([begin_bal_column, ending_bal_column])
        if agg_acc[k].empty:
            agg_acc[k].columns = header["bal"][0], header['change'], header["bal"][2]
            continue
        fst_idx = agg_acc[k].index[0]
        agg_acc[k].at[fst_idx, header["bal"][0]] = round(agg_acc[k].at[fst_idx,  header["bal"][2]] - agg_acc[k].at[fst_idx, header['change']], 2)
        agg_acc[k] = agg_acc[k][[header["bal"][0], header['change'], header["bal"][2]]]

    return agg_acc


def readCutoffFields(pool):
    _map = {'cn': "发行", 'en': "Issuance"}

    lang_flag = None
    if '发行' in pool.keys():
        lang_flag = 'cn'
    elif 'Issuance' in pool.keys():
        lang_flag = 'en'
    else:
        return None

    r = {}
    for k, v in pool[_map[lang_flag]].items():
        if k in validCutoffFields:
            r[validCutoffFields[k]] = v
        else:
            logging.warning(f"Key {k} is not in pool fields {validCutoffFields.keys()}")
    return r


def mkRateAssumption(x):
    match x:
        case (idx, r) if isinstance(r, list):
            return mkTag(("RateCurve",[idx, mkCurve("IRateCurve",r)]))
        case (idx, r) :
            return mkTag(("RateFlat" ,[idx, vNum(r)]))
        case _ :
            raise RuntimeError(f"Failed to match RateAssumption:{x}")

def mkFundingPlan(x:tuple):
    # IssueBondEvent mPre bondName accountName Bond mFormula mFormula
    match x:
        case (d,p,bName,accName,bnd,mBal,mRate):
            return [vDate(d), mkTag(("IssueBondEvent",[earlyReturnNone(mkPre,p),vStr(bName),vStr(accName)
                                                       ,mkBnd(bnd["name"],bnd|{"startDate":vDate(d)})|{"tag":"Bond"}
                                                       ,earlyReturnNone(mkDs,mBal)
                                                       ,earlyReturnNone(mkDs,mRate)]))]
        case (d,bName,accName,bnd):
            return [vDate(d), mkTag(("IssueBondEvent",[None,vStr(bName),vStr(accName),mkBnd(bnd["name"],bnd|{"startDate":vDate(d)})|{"tag":"Bond"},None,None]))]
        case _:
            raise RuntimeError(f"Failed to match mkFundingPlan:{x}")


def mkRefiPlan(x:tuple):
    match x:
        case ("byRate",d,accName, bndName, interestInfo):
            return [vDate(d), mkTag(("RefiRate",[vStr(accName), vStr(bndName), mkBondRate(interestInfo) ]))]
        case _:
            raise RuntimeError(f"Failed to match mkRefinancePlan:{x}")

def mkInspect(x):
    match x:
        case (dp,ds) if isinstance(ds, tuple):
            return mkTag(("InspectPt",[mkDatePattern(dp),mkDs(ds)]))
        case (dp,ds) if isinstance(ds, list):
            return mkTag(("InspectRpt",[mkDatePattern(dp),lmap(mkDs,ds)]))
        case _:
            raise RuntimeError(f"Failed to match mkInspect:{x}")
# data CallOpt = LegacyOpts [C.CallOption]                 -- ^ legacy support
#              | Predicate [Pre]                           -- ^ default test call for each pay day, keep backward compatible
#              | CallOnDates DatePattern [Pre]             -- ^ test call at end of day
#              deriving (Show, Generic, Read, Ord, Eq)
# 
# data NonPerfAssumption = NonPerfAssumption {
#   stopRunBy :: Maybe Date                                    -- ^ optional stop day,which will stop cashflow projection
#   ,projectedExpense :: Maybe [(FeeName,Ts)]                  -- ^ optional expense projection
#   ,callWhen :: Maybe [CallOpt]           


def mkCallOptions(x):
    match x:
        case ("onDates", dp, *pres):
            return mkTag(("CallOnDates", [mkDatePattern(dp), lmap(mkPre,pres)]))
        case ("if", *pres) | ("condition", *pres):
            return mkTag(("CallPredicate", lmap(mkPre,pres)))
        case _:
            raise RunTimeError(f"Failed to make call options: {x}")


def mkNonPerfAssumps(r, xs:list) -> dict:
    def translate(y) -> dict:
        match y:
            case ("stop", d):
                return {"stopRunBy":vDate(d)}
            case ("estimateExpense", *projectExps):
                return {"projectedExpense":[(vStr(fn),mkTs("BalanceCurve",ts)) for (fn, ts) in projectExps]}
            case ("call", *opts):
                return {"callWhen":[mkTag(("LegacyOpts", lmap(mkCallOptionsLegacy, opts)))]}
            case ("callWhen", *opts):
                return {"callWhen": lmap(mkCallOptions, opts)}
            case ("revolving", rPool, rPerf):
                return {"revolving":mkTag(("AvailableAssets", [mkRevolvingPool(rPool), mkAssumpType(rPerf)]))}
            case ("revolving", rPoolPerfMap) if isinstance(rPoolPerfMap, dict):
                return {"revolving":mkTag(("AvailableAssetsBy", {k: [mkRevolvingPool(vPool),mkAssumpType(vAssump)]  for (k,(vPool,vAssump)) in rPoolPerfMap.items()}))}
            case ("interest", *ints) | ("rate", *ints):
                return {"interest":[mkRateAssumption(_) for _ in ints]}
            case ("inspect", *tps):
                return {"inspectOn": lmap(mkInspect,tps)}
            case ("report", m):
                interval = m['dates']
                return {"buildFinancialReport":mkDatePattern(interval)}
            case ("pricing", p):
                return {"pricing":mkPricingAssump(p)}
            case ("fireTrigger", scheduleFired):
                return {"fireTrigger":[ (dt, dealCycleMap[cyc], tn) for (dt, cyc, tn) in scheduleFired]}
            case ("makeWhole", d,spd,tbl):
                return {"makeWholeWhen": [d,spd,tbl]}
            case ("issueBond", *issuancePlan):
                return {"issueBondSchedule": lmap(mkFundingPlan,issuancePlan)  }
            case ("refinance", *refiPlans):
                return {"refinance": lmap(mkRefiPlan,refiPlans)  }
    match xs:
        case None:
            return {}
        case []:
            return r
        case [x,*rest]:
            return mkNonPerfAssumps(r | translate(x),rest)
