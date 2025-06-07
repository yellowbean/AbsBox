from .local.interface import mkTag
from .validation import vStr

def mkTweak(x):
    match x:
        case "stressDefault":
            return mkTag(("StressPoolDefault"))
        case ("maxSpread", bn):
            return mkTag(("MaxSpreadTo", vStr(bn)))
        case _:
            raise RuntimeError(f"failed to match {x}:mkTweak")

def mkStop(x):
    match x:
        case ("bondIncurLoss", bn):
            return mkTag(("BondIncurLoss", vStr(bn)))
        case ("bondPricingEqOriginBal", bn, f1, f2):
            return mkTag(("BondPricingEqOriginBal", [vStr(bn), f1, f2] ))
        case _:
            raise RuntimeError(f"failed to match {x}:mkStop")