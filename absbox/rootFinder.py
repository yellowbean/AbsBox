from .local.interface import mkTag
from .validation import vStr

def mkTweak(x):
    match x:
        case "stressDefault":
            return mkTag(("StressPoolDefault"))
        case "stressPrepayment":
            return mkTag(("StressPoolPrepayment"))
        case ("maxSpread", bn):
            return mkTag(("MaxSpreadTo", vStr(bn)))
        case ("splitBalance", bn1 ,bn2):
            return mkTag(("SplitFixedBalance", [vStr(bn1), vStr(bn2)]))
        case _:
            raise RuntimeError(f"failed to match {x}:mkTweak")

def mkStop(x):
    match x:
        case ("bondIncurLoss", bn):
            return mkTag(("BondIncurLoss", vStr(bn)))
        case ("bondIncurPrinLoss", bn, amt):
            return mkTag(("BondIncurPrinLoss", [vStr(bn), amt]))
        case ("bondIncurIntLoss", bn, amt):
            return mkTag(("BondIncurIntLoss", [vStr(bn), amt]))
        case ("bondPricingEqOriginBal", bn, f1, f2):
            return mkTag(("BondPricingEqOriginBal", [vStr(bn), f1, f2] ))
        case ("bondMetTargetIrr", bn, irr):
            return mkTag(("BondMetTargetIrr", [vStr(bn), irr]))
        case _:
            raise RuntimeError(f"failed to match {x}:mkStop")