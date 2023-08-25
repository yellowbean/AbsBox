from local.china import *
from local.generic import * 
from local.component import * 




def mkDeal(c, x:dict):
    name = getValWithKs(x,['name',"名称","comment",'备注'],defaultReturn="")
    dates = getValWithKs(x,['dates',"date","日期"])
    accs = getValWithKs(x,['accounts',"account","账户","帐户"])
    fees = getValWithKs(x,['fee',"fees","费用"])
    pool = getValWithKs(x,['pool',"collateral","资产池"])
    bonds = getValWithKs(x,['bond',"bonds","债券","支持证券"])
    waterfall = getValWithKs(x,['waterfall',"现金流分配","分配规则"])
    liqFacility = getValWithKs(x,['liqFacility','liqProvider',"insurance","liquidity","流动性支持","流动性提供方"])
    collection = getValWithKs(x,['colleciton','collectionRule','aggregation','归集规则','归集'])
    rateSwap = getValWithKs(x,['rateSwap',"IRSwap","利率互换"])
    currencySwap = getValWithKs(x,['fxSwap',"currencySwap","汇率互换"])
    trigger = getValWithKs(x,['trigger',"triggers","事件","触发事件"])
    status = getValWithKs(x,['status','stage',"状态","阶段"],defaultReturn="Amorizing")
    custom = getValWithKs(x,['custom',"自定义"])
    ledgers = getValWithKs(x,['ledger',"ledgers","科目"])

    
    return Generic(
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
        ,custom
        ,ledgers
    )