
from absbox.local.util import mkTag,DC,mkTs,query

datePattern = {"月末":"MonthEnd"
              ,"季度末":"QuarterEnd"
              ,"年末":"YearEnd"
              ,"月初":"MonthFirst"
              ,"季度初":"QuarterFirst"
              ,"年初":"YearFirst"
              ,"每年":"MonthDayOfYear"
              ,"每月":"DayOfMonth"
              ,"每周":"DayOfWeek"}


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
        case {"封包日":a, "起息日":b,"首次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf}:
            return mkTag(("PatternInterval"
                          ,{"ClosingDate":[b,mkDatePattern(pf),d] ,"CutoffDate":[a,mkDatePattern(pf),d] 
                           ,"FirstPayDate":[c,mkDatePattern(bf),d]}))
        case {"回收期期初日":a, "起息日":b,"下次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf}:
            return mkDate({"封包日":a, "起息日":b,"首次兑付日":c,"法定到期日":d,"收款频率":pf,"付款频率":bf})
        case {"回款日":cdays, "分配日":ddays,"封包日":cutoffDate,"起息日":closingDate}:
            return mkTag(("CustomDates"
                          ,[cutoffDate
                            ,[ mkTag(("PoolCollection",[cd,""])) for cd in cdays]
                            ,closingDate
                            ,[ mkTag(("RunWaterfall",[dd,""])) for dd in ddays]]))
        case {"cutoff":a,"closing":b,"nextPay":c,"stated":d,"poolFreq":pf,"payFreq":bf}:
            return mkTag(("PatternInterval"
                          ,{"ClosingDate":[b,mkDatePattern(pf),d] ,"CutoffDate":[a,mkDatePattern(pf),d] 
                           ,"FirstPayDate":[c,mkDatePattern(bf),d]}))
        case {"cutoff":a,"closing":b,"firstPay":c,"stated":d,"poolFreq":pf,"payFreq":bf}:
            return mkDate({"cutoff":a,"closing":b,"nextPay":c,"stated":d,"poolFreq":pf,"payFreq":bf})
        case _:
            raise RuntimeError(f"对于产品发行建模格式为：{'封包日':a, '起息日': b,'首次兑付日':c,'法定到期日':e,'收款频率':f,'付款频率':g} ")
