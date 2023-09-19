from absbox.local.china import *
from absbox.local.generic import * 
from absbox.local.component import * 
from absbox.local.util import * 
from absbox.validation import *
import rich
from rich.console import Console

console = Console()


def mkDeal(x:dict):
    name = getValWithKs(x, ['name', "名称", "comment", '备注'], defaultReturn="")
    
    dates = getValWithKs(x, ['dates', "date", "日期"])
    assert dates is not None, f"dates shouldn't be None"
    
    accs = list((accName,acc) for accName,acc in getValWithKs(x, ['accounts', "account", "账户", "帐户"]).items())
    assert accs is not None, f"accounts shouldn't be None"
    
    fees = list((fn,fv|{"name":fn,"名称":fn})
                for (fn,fv) in getValWithKs(x
                                            , ['expense', 'expenses', 'fee', "fees", "费用"]
                                            , defaultReturn={}).items())
    
    pool = getValWithKs(x, ['pool', "collateral", "资产池"])
    # _assets = [mkAsset(x) for x in getValWithKs(_pool
    #                                             , ['assets', 'loans', 'mortgages', "清单", "资产清单"])]
    # _asOfDate = getValWithKs(_pool, ["asOfDate", "asofDate", "封包日"])
    # _issuanceStat = readIssuance(_pool)
    # _futureCf = mkCf(getValWithKs(_pool,["归集表","现金流归集表","projected","cashflow"],defaultReturn=[]))

    bonds = list((bn,bo)
                for bn,bo in getValWithKs(x
                                         , ['bond', "bonds", "notes", "债券", "支持证券"]).items())
    assert bonds is not None, f"bonds shouldn't be None"
                      
    waterfall = getValWithKs(x, ['waterfall', "现金流分配", "分配规则"])
    assert waterfall is not None, f"waterfall shouldn't be None"
    
    collection = getValWithKs(x,['collect','colleciton', 'collectionRule', 'aggregation','归集规则','归集'])
    assert collection is not None , f"collection shouldn't be None"

    liqFacility = getValWithKs(x, ['liqFacility', 'liqProvider', "insurance"
                                  ,"cashAdvance", "liquidity", "流动性支持"
                                  , "流动性提供方", "增信方", "担保"], defaultReturn=None)
    
    rateSwap = getValWithKs(x, ['rateSwap', "IRSwap", "利率互换"])
    
    currencySwap = None  #TODO 

    trigger = None   
    if (_t:=getValWithKs(x ,['trigger', "triggers", "事件", "触发事件"])):
        trigger = _t
    else:
        trigger = None
    
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
    )
    errors,warnings = valDeal(deal.json['contents'],[],[])

    if len(errors)>0:
        for e in errors:
            console.print(f"❕[bold red]Warning in model :{e}")
        raise RuntimeError(f"Errors in deal")

    if len(warnings)>0:
        for w in warnings:
            console.print(f"❕[bold yellow]Warning in model :{w}")

    return deal