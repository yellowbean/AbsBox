
from absbox.local.util import mkTag,DC,mkTs,query
from enum import Enum
datePattern = {"月末":"MonthEnd"
              ,"季度末":"QuarterEnd"
              ,"年末":"YearEnd"
              ,"月初":"MonthFirst"
              ,"季度初":"QuarterFirst"
              ,"年初":"YearFirst"
              ,"每年":"MonthDayOfYear"
              ,"每月":"DayOfMonth"
              ,"每周":"DayOfWeek"}

class 频率(Enum):
    每月 = 12
    每季度 = 4
    每半年 = 2
    每年 = 1


freqMap = {"每月": "Monthly"
    , "每季度": "Quarterly"
    , "每半年": "SemiAnnually"
    , "每年": "Annually"}

baseMap = {"资产池余额": "CurrentPoolBalance"
           , "资产池期末余额": "CurrentPoolBalance"
           , "资产池期初余额": "CurrentPoolBegBalance"
           , "资产池初始余额": "OriginalPoolBalance"
           , "初始资产池余额": "OriginalPoolBalance"
           , "资产池当期利息":"PoolCollectionInt"
           , "债券余额":"CurrentBondBalance"
           , "债券初始余额":"OriginalBondBalance"
           , "当期已付债券利息":"LastBondIntPaid"
           , "当期已付费用" :"LastFeePaid"
           , "当期未付债券利息" :"CurrentDueBondInt"
           , "当期未付费用": "CurrentDueFee"
           }




def mkDatePattern(x):
    match x:
        case ["每月",_d]:
            return mkTag((datePattern["每月"],_d))
        case ["每年",_m,_d]:
            return mkTag((datePattern["每年"],[_m,_d]))
        case ["DayOfMonth",_d]:
            return mkTag(("DayOfMonth",_d))
        case ["MonthDayOfYear",_m,_d]:
            return mkTag(("MonthDayOfYear",_m,_d))
        case _x if (_x in datePattern.values()):
            return mkTag((_x))
        case _x if (_x in datePattern.keys()):
            return mkTag((datePattern[x]))
        case _:
            raise RuntimeError(f"Failed to match {x}")


def mkDate(x):
    match x:
        case {"封包日":a, "起息日":b,"首次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf} | \
             {"cutoff":a,"closing":b,"firstPay":c,"stated":d,"poolFreq":pf,"payFreq":bf}:
            return mkTag(("PatternInterval"
                          ,{"ClosingDate":[b,mkDatePattern(pf),d] ,"CutoffDate":[a,mkDatePattern(pf),d] 
                           ,"FirstPayDate":[c,mkDatePattern(bf),d]}))
        case {"回收期期初日":a, "起息日":b,"下次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf} | \
             {"cutoff":a,"closing":b,"nextPay":c,"stated":d,"poolFreq":pf,"payFreq":bf}:
            return mkDate({"封包日":a, "起息日":b,"首次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf})
        case {"回款日":cdays, "分配日":ddays,"封包日":cutoffDate,"起息日":closingDate} | \
            {"poolCollection":cdays,"distirbution":ddays,"cutoff":cutoffDate,"closing":closingDate} :
            return mkTag(("CustomDates"
                          ,[cutoffDate
                            ,[ mkTag(("PoolCollection",[cd,""])) for cd in cdays]
                            ,closingDate
                            ,[ mkTag(("RunWaterfall",[dd,""])) for dd in ddays]]))
        case _:
            raise RuntimeError(f"对于产品发行建模格式为：{'封包日':a, '起息日': b,'首次兑付日':c,'法定到期日':e,'收款频率':f,'付款频率':g} ")

def mkFeeType(x):
    match x:
        case {"年化费率": [base, rate]} | {"annualPctFee": [base, rate]}:
            return mkTag(("AnnualRateFee"
                        , [ mkTag((baseMap[base],'1970-01-01')) , rate]))
        case {"百分比费率": [*desc, rate]} | {"pctFee": [*desc, rate]}:
            match desc:
                case ["资产池回款","利息"] | ["poolCollection","interest"]:
                    return mkTag(("PctFee", [mkTag(("PoolCollectionIncome", "CollectedInterest")), rate]))
                case ["已付利息合计", *bns] | ["paidInterest", *bns]:
                    return mkTag(("PctFee", [mkTag(("LastBondIntPaid",bns)), rate]))
                case ["已付本金合计", *bns] | ["paidPrincipal", *bns]:
                    return mkTag(("PctFee", [mkTag(("LastBondPrinPaid",bns)), rate]))
                case _:
                    raise RuntimeError(f"Failed to match on 百分比费率：{desc,rate}")
        case {"固定费用": amt} | {"fixFee": amt}:
            return mkTag(("FixFee", amt))
        case {"周期费用": [p, amt]} | {"recurFee": [p, amt]}:
            return mkTag(("RecurFee", [mkDatePattern(p), amt]))
        case _ :
            raise RuntimeError(f"Failed to match on fee type:{x}")

def mkDateVector(x):
    match x:
        case dp if isinstance(dp,str):
            return mkTag(datePattern[dp])
        case [dp, *p] if (dp in datePattern.keys()):
            return mkTag((datePattern[dp],p))
        case _ :
            raise RuntimeError(f"not match found: {x}")


def mkDs(x):
    "Making Deal Stats"
    match x:
        case ("债券余额",) | ("bondBalance",):
            return mkTag("CurrentBondBalance")
        case ("债券余额",*bnds) | ("bondBalance",*bnds):
            return mkTag(("CurrentBondBalanceOf",bnds))
        case ("资产池余额",) | ("poolBalance",):
            return mkTag("CurrentPoolBalance")
        case ("初始债券余额",) | ("originalBondBalance",):
            return mkTag("OriginalBondBalance")
        case ("初始资产池余额",) | ("originalPoolBalance",):
            return mkTag("OriginalPoolBalance")
        case ("债券系数",) | ("bondFactor",):
            return mkTag("BondFactor")
        case ("资产池系数",) | ("poolFactor",):
            return mkTag("PoolFactor")
        case ("所有账户余额",) | ("accountBalance"):
            return mkTag("AllAccBalance")
        case ("账户余额",*ans) | ("accountBalance",*ans):
            return mkTag(("AccBalance",ans))
        case ("系数",ds,f) | ("factor", ds, f):
            return mkTag(("Factor",[mkDs(ds),f]))
        case ("债券待付利息",*bnds) | ("bondDueInt",*bnds):
            return mkTag(("CurrentDueBondInt",bnds))
        case ("债券已付利息",*bnds) | ("lastBondIntPaid",*bnds):
            return mkTag(("LastBondIntPaid",bnds))
        
        #   , "当期已付债券利息":"LastBondIntPaid"
        #   , "当期已付费用" :"LastFeePaid"
        #   , "当期未付债券利息" :"CurrentDueBondInt"
        #   , "当期未付费用": "CurrentDueFee"
  
        case ("待付费用",*fns) | ("feeDue",*fns):
            return mkTag(("CurrentDueFee",fns))
        case ("已付费用",*fns) | ("lastFeePaid",*fns):
            return mkTag(("LastFeePaid",fns))
        case ("Min", ds1, ds2):
            return mkTag(("Min",[mkDs(ds1),mkDs(ds2)]))
        case ("Max", ds1, ds2):
            return mkTag(("Max",[mkDs(ds1),mkDs(ds2)]))
        case ("合计",*ds) | ("sum", *ds):
            return mkTag(("Sum",[mkDs(_ds) for _ds in ds]))
        case ("差额",*ds) | ("substract",*ds):
            return mkTag(("Substract",[mkDs(_ds) for _ds in ds]))
        case ("常数", n) | ("constant", n):
            return mkTag(("Constant", n))
        case ("储备账户缺口", *accs) | ("reserveGap",*accs):
            return mkTag(("ReserveAccGap",accs))
        case ("自定义", n) | ("custom", n):
            return mkTag(("UseCustomData", n))
        case legacy if (legacy in baseMap.keys()):
            return mkDs((legacy,))
        case _ :
            raise RuntimeError(f"Failed to match DS/Formula: {x}")

def isPre(x):
    try: 
        return mkPre(x) is not None
    except RuntimeError as e:
        return False 

def mkPre(p):
    dealStatusMap = {"摊还":"Current"
                     ,"加速清偿":"Accelerated"
                     ,"循环":"Revolving"}
    match p:
        case [ds,">",amt]:
            return mkTag(("IfGT",[mkDs(ds),amt]))
        case [ds,"<",amt]:
            return mkTag(("IfLT",[mkDs(ds),amt]))
        case [ds,">=",amt]:
            return mkTag(("IfGET",[mkDs(ds),amt]))
        case [ds,"<=",amt]:
            return mkTag(("IfLET",[mkDs(ds),amt]))
        case [ds,"=",0]:
            return mkTag(("IfZero",mkDs(ds)))
        case [">",_d]:
            return mkTag(("IfAfterDate",_d))
        case ["<",_d]:
            return mkTag(("IfBeforeDate",_d))
        case [">=",_d]:
            return mkTag(("IfAfterOnDate",_d))
        case ["<=",_d]:
            return mkTag(("IfBeforeOnDate",_d))
        case ["状态",_ds] :
            return mkTag(("IfDealStatus",dealStatusMap[_ds]))
        case ["status",_ds]: 
            return mkTag(("IfDealStatus",_ds))
        case ["同时满足",_p1,_p2] | ["all",_p1,_p2]:
            return mkTag(("And",mkPre(_p1),mkPre(_p2)))
        case ["任一满足",_p1,_p2] | ["any",_p1,_p2]:
            return mkTag(("Or",mkPre(_p1),mkPre(_p2)))
        case _ :
            raise RuntimeError(f"Failed to match on Pre: {p}")


def mkAccInt(x):
    match x:
        case {"周期": _dp, "利率":idx, "利差":spd, "最近结息日": lsd} \
            | {"period": _dp,  "index":idx, "spread":spd, "lastSettleDate": lsd}:
            return mkTag(("InvestmentAccount",[idx, spd, lsd, mkDateVector(_dp)]))
        case {"周期": _dp, "利率": br, "最近结息日": lsd} \
            | {"period": _dp, "rate": br, "lastSettleDate": lsd}:
            return mkTag(("BankAccount",[br, lsd, mkDateVector(_dp)]))
        case None:
            return None
        case _:
            raise RuntimeError(f"Failed to match on account interest definition: {x}")


def mkAccType(x):
    match x:
        case {"固定储备金额": amt} | {"fixReserve": amt} :
            return mkTag(("FixReserve", amt))
        case {"目标储备金额": [base, rate]} | {"targetReserve": [base, rate]}:
            match base:
                case ["合计",*qs] | ["Sum",*qs]:
                    sumDs = [mkDs(q) for q in qs]
                    return mkTag(("PctReserve", [mkTag(("Sum",sumDs)), rate]))
                case _ :
                    return mkTag(("PctReserve", [mkDs(base), rate]))
        case {"目标储备金额": {"公式":ds,"系数":rate}} | {"targetReserve":{"formula":ds,"factor":rate}}:
            return mkTag(("PctReserve",[mkDs(ds), rate]))
        case {"目标储备金额": {"公式":ds}} | {"targetReserve":{"formula":ds}}:
            return mkTag(("PctReserve",[mkDs(ds), 1.0]))
        case {"较高": [a, b]} | {"max":[a, b]}:
            return mkTag(("Max", [mkAccType(a), mkAccType(b)]))
        case {"较低": [a, b]} | {"min":[a, b]}:
            return mkTag(("Min", [mkAccType(a), mkAccType(b)]))
        case {"分段": [p,a,b]} | {"When":[p,a,b]}:
            return mkTag(("Either", [mkPre(p) ,mkAccType(a), mkAccType(b)]))
        case None:
            return None
        case _ :
            raise RuntimeError(f"Failed to match {x} for account reserve type")

def mkAccTxn(xs):
    "AccTxn T.Day Balance Amount Comment"
    if xs is None:
        return None
    else:
        return [ mkTag(("AccTxn",x)) for x in xs]


def mkAcc(an,x):
    match x:
        case {"余额":b,"类型":t,"计息":i,"记录":tx}|{"balance":b,"type":t,"interest":i,"txn":tx}:
            return {"accBalance": b, "accName": an
                    ,"accType": mkAccType(t)
                    , "accInterest": mkAccInt(i)
                    , "accStmt": mkAccTxn(tx)}

        case {"余额":b}|{"balance":b}:
            return mkAcc(an, x|{"计息":x.get("计息",None),"interest":x.get("interest",None)
                                ,"记录":x.get("记录",None),"txn":x.get("txn",None)
                                ,"类型":x.get("类型",None),"type":x.get("type",None)})
        #case {"余额":b,"类型":t,"计息":i}|{"balance":b,"type":t,"interest":i}:
        #    return mkAcc(an, x|{"记录":None,"txn":None})
        #
        #case {"余额":b,"类型":t,"记录":tx}|{"balance":b,"type":t,"txn":tx}:
        #    return mkAcc(an, x|{"计息":None,"interest":None})
        #
        #case {"余额":b,"类型":t}|{"balance":b,"type":t}:
        #    return mkAcc(an, x|{"计息":None,"interest":None, "记录":None,"txn":None})

        #case {"余额":b}|{"balance":b}:
        #    return mkAcc(an, x|{"计息":None,"interest":None
        #                        ,"记录":None,"txn":None
        #                        ,"类型":None,"type":None})
        case _ :
            raise RuntimeError(f"Failed to match account: {an},{x}")
 
 
def mkBondType(x):
    match x:
        case {"固定摊还": schedule} | {"PAC":schedule}:
            return mkTag(("PAC", mkTag(("BalanceCurve", schedule))))
        case {"过手摊还": None} | {"Sequential":None}:
            return mkTag(("Sequential"))
        case {"锁定摊还": _after} | {"Lockout":_after}:
            return mkTag(("Lockout", _after))
        case {"权益": _} | {"Equity": _} :
            return mkTag(("Equity"))
        case _:
            raise RuntimeError(f"Failed to match bond type: {x}")

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
        case {"浮动": [_index, Spread, resetInterval],"日历":dc} | \
            {"Floater": [_index, Spread, resetInterval],"dayCount":dc}:
            return mkTag(("Floater", [indexMapping[_index]
                                    , Spread
                                    , mkRateReset(resetInterval)
                                    , dc
                                    , None
                                    , None]))
        case {"浮动": [_index, Spread, resetInterval]} | {"Floater": [_index, Spread, resetInterval]}:
            return mkBondRate(x | {"日历":DC.DC_ACT_365F.value
                                  ,"dayCount":DC.DC_ACT_365F.value})
        case {"固定": _rate, "日历":dc} | {"fix": _rate, "dayCount":dc}:
            return mkTag(("Fix",[_rate,dc]))
        case {"固定": _rate} | {"fix": _rate}:
            return mkTag(("Fix",[_rate,DC.DC_ACT_365F.value]))
        case {"期间收益": _yield}:
            return mkTag(("InterestByYield",_yield))
        case _ :
            raise RuntimeError(f"Failed to match bond rate type:{x}")

def mkBnd(bn,x):
    match x:
        case {"当前余额": bndBalance
              ,"当前利率": bndRate
              ,"初始余额": originBalance
              ,"初始利率": originRate
              ,"起息日": originDate
              ,"利率": bndInterestInfo
              ,"债券类型": bndType} | \
              {"balance": bndBalance
              ,"rate": bndRate
              ,"originBalance": originBalance
              ,"originRate": originRate
              ,"startDate": originDate
              ,"rateType": bndInterestInfo
              ,"bondType": bndType}:
            return {bn: {"bndName": bn
                        ,"bndBalance": bndBalance
                          , "bndRate": bndRate
                          , "bndOriginInfo":
                           {"originBalance": originBalance
                               , "originDate": originDate
                               , "originRate": originRate}
                          , "bndInterestInfo": mkBondRate(bndInterestInfo)
                          , "bndType": mkBondType(bndType)
                          , "bndDuePrin": 0
                          , "bndDueInt": 0
                          , "bndDueIntDate": None }}

        case _:
            raise RuntimeError(f"Failed to match bond:{bn},{x}")

def mkLiqMethod(x):
    match x:
        case ["正常|违约",a,b]:
            return mkTag(("BalanceFactor",[a,b]))
        case ["正常|拖欠|违约",a,b,c]:
            return mkTag(("BalanceFactor2",[a,b,c]))
        case ["贴现|违约",a,b]:
            return mkTag(("PV",[a,b]))



def mkFeeCapType(x):
    match x:
        case {"应计费用百分比": pct}:
            return mkTag(("DuePct",pct))
        case {"应计费用上限": amt}:
            return mkTag(("DueCapAmt",amt))

def mkPDA(x):
    match x:
        case {"公式": ds}:
            return mkTag(("DS",mkDs(ds)))

def mkAccountCapType(x):
    match x:
        case {"余额百分比": pct}:
            return mkTag(("DuePct",pct))
        case {"金额上限": amt}:
            return mkTag(("DueCapAmt",amt))

def mkTransferLimit(x):
    match x:
        case {"余额百分比": pct}:
            return mkTag(("DuePct",pct))
        case {"金额上限": amt}:
            return mkTag(("DueCapAmt",amt))
        case {"公式": "ABCD" }:
            return mkTag(("Formula","ABCD"))
        case {"公式": formula}:
            return mkTag(("DS",mkDs(formula)))



def mkAction(x):
    match x:
        case ["账户转移", source, target] | ["transfer", source, target]:
            return mkTag(("Transfer",[source, target]))
        case ["按公式账户转移", _limit, source, target] | ["transferBy", _limit, source, target]:
            return mkTag(("TransferBy",[mkTransferLimit(_limit), source, target]))
        case ["计提费用", *feeNames] | ["calcFee", *feeNames]:
            return mkTag(("CalcFee",feeNames))
        case ["计提利息", *bndNames] | ["calcInt", *bndNames]:
            return mkTag(("CalcBondInt",bndNames))
        case ["支付费用", source, target] | ["payFee", source, target]:
            return mkTag(("PayFee",[source, target]))
        case ["支付费用收益", source, target, _limit] | ["payFeeResidual", source, target, _limit]:
            limit = mkAccountCapType(_limit)
            return mkTag(("PayFeeResidual",[limit, source, target]))
        case ["支付费用收益", source, target] | ["payFeeResidual", source, target]:
            return mkTag(("PayFeeResidual",[None, source, target]))
        case ["支付费用限额", source, target, _limit] | ["payFeeBy", source, target, _limit] :
            limit = mkFeeCapType(_limit)
            return mkTag(("PayFeeBy",[limit, source, target]))
        case ["支付利息", source, target] | ["payInt", source, target]:
            return mkTag(("PayInt",[source, target]))
        case ["支付本金", source, target, _limit] | ["payPrin", source, target, _limit]:
            pda = mkPDA(_limit)
            return mkTag(("PayPrinBy",[pda, source, target]))
        case ["支付本金", source, target] | ["payPrin", source, target]:
            return mkTag(("PayPrin",[source, target]))
        case ["支付剩余本金", source, target] | ["payPrinResidual", source, target]:
            return mkTag(("PayPrinResidual",[source, target]))
        case ["支付期间收益", source, target]:
            return mkTag(("PayTillYield",[source, target]))
        case ["支付收益", source, target, limit] | ["payResidual", source, target, limit]:
            return mkTag(("PayResidual",[limit, source, target]))
        case ["支付收益", source, target] | ["payResidual", source, target]:
            return mkTag(("PayResidual",[None, source, target]))
        case ["储备账户转移", source, target, satisfy] | ["transferReserve", source, target, satisfy]:
            _map = {"源储备":"Source", "目标储备": "Target"}
            return mkTag(("TransferReserve",[_map[satisfy], source, target]))
        case ["出售资产", liq, target] | ["sellAsset", liq, target]:
            return mkTag(("LiquidatePool",[mkLiqMethod(liq), target]))
        case ["流动性支持",source, target, limit] | ["liqSupport",source, target, limit]:
            return mkTag(("LiqSupport",[ mkTag(("DS",mkDs(limit))), source, target]))
        case ["流动性支持",source, target] | ["liqSupport",source, target]:
            return mkTag(("LiqSupport",[None, source, target]))
        case ["流动性支持偿还",source, target] | ["liqRepay",source, target]:
            return mkTag(("LiqRepay",[None, source, target]))
        case ["流动性支持报酬",source, target]| ["liqRepayResidual",source, target]:
            return mkTag(("LiqYield",[None, source, target]))


def mkWaterfall2(x):
    match x:
        case (pre, *_action) if isPre(pre) and len(x)>2: # pre with multiple actions
            _pre = mkPre(pre)
            return [[ _pre, mkAction(a) ] for a in _action ]
        case (pre, _action) if isPre(pre) and len(x)==2: # pre with 1 actions
            _pre = mkPre(pre)
            return [[ _pre, mkAction(_action) ]]
        case _:
            return [[ None,mkAction(x) ]]

