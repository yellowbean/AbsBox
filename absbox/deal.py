from rich.console import Console
from lenses import lens
import toolz as tz
from itertools import product
import dataclasses

from .local.component import * 
from .local.util import * 
from .local.generic import Generic
from .exception import AbsboxError

console = Console()

def _require(m: dict, ks: list, label: str):
    """Return the first present key among `ks`, raising if none is found."""
    v = getValWithKs(m, ks)
    if v is None:
        raise AbsboxError(f"❌ {label} is required but not found in deal")
    return v

def mkDeal(x:dict, preCheck=True):
    name = getValWithKs(x, ['name', "名称", "comment", '备注'], defaultReturn="")
    
    dates = _require(x, ['dates', "date", "日期"], "dates")
    
    accs = list(_require(x, ['accounts', "account", "账户", "帐户"], "accounts").items())
    
    fees = list((fn,fv|{"name":fn,"名称":fn})
                for (fn,fv) in getValWithKs(x
                                            , ['expense', 'expenses', 'fee', "fees", "费用"]
                                            , defaultReturn={}).items())
    
    pool = getValWithKs(x, ['pool', "collateral", "资产池"])

    bonds = list(_require(x, ['bond', "bonds", "notes", "债券", "支持证券"], "bonds").items())

    waterfall = _require(x, ['waterfall', "现金流分配", "分配规则"], "waterfall")
    
    collection = _require(x,['collect','colleciton', 'collectionRule', 'aggregation', '归集规则', '归集'], "collection")

    liqFacility = getValWithKs(x, ['liqFacility', 'liqProvider', "insurance"
                                    ,"cashAdvance", "liquidity", "流动性支持"
                                    , "流动性提供方", "增信方", "担保"], defaultReturn=None)
    
    rateSwap = getValWithKs(x, ['rateSwap','rateSwaps', "IRSwap", "利率互换"])
    
    rateCap = getValWithKs(x, ['rateCap',"rateCaps", "IRCap", "利率上限互换"])
    
    currencySwap = None  #TODO 

    trigger = getValWithKs(x, ['trigger', "triggers", "事件", "触发事件"], defaultReturn=None)
    
    status = getValWithKs(x, ['status', 'stage', "状态", "阶段"], defaultReturn="Amortizing")
    
    custom = getValWithKs(x, ['custom', "自定义"])
    
    ledgers = getValWithKs(x, ['ledger', "ledgers", "科目"])
    
    deal = Generic(
        name
        ,dates 
        ,pool
        ,accs
        ,bonds
        ,fees
        ,waterfall
        ,collection
        ,liqFacility
        ,rateSwap
        ,currencySwap
        ,trigger
        ,status
        ,None
        ,ledgers
        ,rateCap
    )

    return deal


def mkDealsBy(d, m: dict)->dict:
    "Input a deal, permunations, lenses ,and return a list of deals with variety"
    return {k: dataclasses.replace(d, **v) for k, v in m.items()} 


def setDealsBy(d, *receipes: list, init=None, **kwargs):
    "input a deal object, a list of tweaks( path, values) ,return an updated deal"
    if init:
        receipes = [(init & _[0], _[1]) for _ in receipes]
    for (p, v) in receipes:
        d &= p.set(v)
    return d


def prodDealsBy(d, *receipes, **kwargs) -> dict:
    inflated = [[(p, _) for _ in vs] for (p, vs) in receipes]
    permus = product(*inflated)
    if kwargs.get('guessKey', False) == True:
        return {strFromPath(v): setDealsBy(d, *v, **kwargs) for v in permus}
    return {v: setDealsBy(d, *v, **kwargs) for v in permus}


def setAssumpsBy(a, *receipes: list, init=None):
    if init:
        receipes = [(init & _[0], _[1]) for _ in receipes]
    for (p, v) in receipes:
        a &= p.set(v)
    return a


def prodAssumpsBy(a, *receipes, **kwargs):
    inflated = [[(p, _) for _ in vs] for (p, vs) in receipes]
    permus = product(*inflated)
    return {str(v): setAssumpsBy(a, *v, **kwargs) for v in permus}



