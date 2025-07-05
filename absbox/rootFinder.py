from .local.interface import mkTag
from .validation import vStr,vBool,vNum
from .local.component import mkDs

def mkTweak(x):
    match x:
        case "stressDefault":
            return mkTag(("StressPoolDefault", [1.0, 500]))
        case ("stressDefault",l,h):
            return mkTag(("StressPoolDefault", [l, h]))
        case "stressPrepayment":
            return mkTag(("StressPoolPrepayment",  [1.0, 500]))
        case ("stressPrepayment", l, h):
            return mkTag(("StressPoolPrepayment", [l, h]))
        case ("maxSpread", bn):
            return mkTag(("MaxSpreadTo", [ vStr(bn), (1.0, 500)]))
        case ("maxSpread", bn, l, h):
            return mkTag(("MaxSpreadTo", [ vStr(bn), (l, h)]))
        case ("splitBalance", bn1 ,bn2):
            return mkTag(("SplitFixedBalance", [vStr(bn1), vStr(bn2), (1.0, 500)]))
        case ("splitBalance", bn1, bn2, l, h):
            return mkTag(("SplitFixedBalance", [vStr(bn1), vStr(bn2), (l, h)]))
        case _:
            raise RuntimeError(f"failed to match {x}:mkTweak")

def mkStop(x):
    match x:
        case ("bondIncurLoss", bn):
            return mkTag(("BondIncurLoss", vStr(bn)))
        case ("bondIncurPrinLoss", bn, amt):
            return mkTag(("BondIncurPrinLoss", [vStr(bn), vNum(amt)]))
        case ("bondIncurIntLoss", bn, amt):
            return mkTag(("BondIncurIntLoss", [vStr(bn), vNum(amt)]))
        case ("bondPricingEqOriginBal", bn, f1, f2):
            return mkTag(("BondPricingEqOriginBal", [vStr(bn), vBool(f1), vBool(f2)] ))
        case ("bondMetTargetIrr", bn, irr):
            return mkTag(("BondMetTargetIrr", [vStr(bn), vNum(irr)]))
        case ("byFormula", ds, target):
            return mkTag(("BalanceFormula", [mkDs(ds), vNum(target)]))
        case _:
            raise RuntimeError(f"failed to match {x}:mkStop")
