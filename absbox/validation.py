import json
from pyspecter import S,query
from absbox.local.util import flat


def inSet(xs,validSet):
    if set(xs).issubset(validSet):
        return True
    else:
        return False

def valDeal(d, error, warning) -> list:
    acc_names = set(d['accounts'].keys())
    bnd_names = set(d['bonds'].keys())
    fee_names = set(d['fees'].keys())
    swap_names = set([]) if d['rateSwap'] is None else set(d['rateSwap'].keys())
    w = d['waterfall']
    #optional
    if d['ledgers']:
        ledger_names = set(d['ledgers'].keys())
    assert w is not None ,"Waterfall is None"
    
    def validateAction(action):
        rnt = ""
        match action:
           case {"tag":'PayFee', "contents":[_, acc, fees, _]}:
               if not inSet([acc],acc_names):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if not inSet(fees,fee_names):
                   rnt += f"Fees {fees} is not in deal fees {fee_names};"
           case {"tag":'CalcAndPayFee', "contents":[_, acc, fees, _]}:
               if not inSet([acc],acc_names):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if not inSet(fees,fee_names):
                   rnt += f"Fees {fees} is not in deal fees {fee_names};"
           case {"tag":'PayInt', "contents":[_, acc, bonds, _]} | {"tag":'AccrueAndPayInt', "contents":[_, acc, bonds, _]}:
               if not inSet([acc],acc_names):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if not inSet(bonds,bnd_names):
                   rnt += f"Bonds {bonds} is not in deal bonds {bnd_names};"
           case {"tag":'PayPrin', "contents":[_, acc, bonds, _]}:
               if (not inSet([acc],acc_names)): 
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if (not inSet(bonds,bnd_names)):
                   rnt += f"Bonds {bonds} is not in deal bonds {bnd_names};"
           case {"tag":'PayPrinResidual', "contents":[acc, bonds]}:
               if (not inSet([acc],acc_names)):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if (not inSet(bonds,bnd_names)):
                   rnt += f"Bonds {bonds} is not in deal bonds {bnd_names};"
           case {"tag":'Transfer',"contents":[_,acc1,acc2,_]}:
               if (not inSet([acc1,acc2],acc_names)):
                   rnt += f"Account {acc1,acc2} is not in deal account {acc_names};"
           case {"tag":'PayFeeResidual',"contents":[_,acc,fee]}:
               if (not inSet([acc],acc_names)):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if (not inSet([fee],fee_names)):
                   rnt += f"Fee {fee} is not in deal fees {fee_names};"
           case {"tag":'PayIntResidual',"contents":[_,acc,bnd_name]}:
               if (not inSet([acc],acc_names)):
                   rnt += f"Account {acc} is not in deal account {acc_names};"
               if (not inSet([bnd_name],bnd_names)):
                   rnt += f"Bond {bnd_name} is not in deal bonds {bnd_names};"
           case {"tag":'CalcFee',"contents": fs}:
               if (not inSet(fs,fee_names)):
                   rnt += f"Fee {fs} is not in deal fees {fee_names};"
           case {"tag":'CalcBondInt',"contents": bs}:
               if (not inSet(bs,bnd_names)):
                   rnt += f"Bond {bs} is not in deal bonds {bnd_names};"
           case {"tag":'SwapSettle',"contents": [acc, swap_name]}:
               if (not inSet([acc], acc_names)):
                   rnt += f"Account: {acc} is not in deal accounts {acc_names};"
               if (not inSet([swap_name],swap_names)):
                   rnt += f"Swap: {swap_name} is not in deal swap list {swap_names};"
           case _:
               pass
        return rnt
    

    for wn,waterfallActions in w.items():
        for idx,action in enumerate(waterfallActions):
            if (vr:=validateAction(action)) != "":
                error.append(">".join((wn,str(idx),vr)))
    
    #if preclosing deal ,must have a preClosing status
    if d['dates']['tag'] == 'PreClosingDates':
        if d['status']['tag'] != 'PreClosing':
            error.append(f"Deal Date is preClosing, but status is not PreClosing")

    return (error,warning)

def valReq(reqSent) -> list:
    error = []
    warning = []
    req = json.loads(reqSent)
    match req :
        case {"tag":"SingleRunReq","contents":[{"contents":d}, ma, mra]}:
            error, warning = valDeal(d, error, warning)
            error, warning = valAssumption(d, ma, error, warning)
            error, warning = valNonPerfAssumption(d, mra, error, warning)
        case {"tag":"MultiScenarioRunReq","contents":[{"contents":d}, mam, mra]}:
            error, warning = valDeal(d, error, warning)
        case {"tag":"MultiDealRunReq","contents":[dm, ma, mra]}:
            error, warning = valAssumption(ma, error, warning)
            error, warning = valNonPerfAssumption(d, ma, error, warning)
        case _:
            raise RuntimeError(f"Failed to match request:{req}")

    return error, warning

def valNonPerfAssumption(d, nonPerfAssump, error, warning) -> list:
    e = []
    w = []
    # floater index required
    indexRequired = set()
    ## from bond 
    bndIndx = set([ _['contents'][1] for _ in  query(d,['bonds',S.MVALS,S.ALL,'bndInterestInfo']) if _['tag']=='Floater'])
    ## from asset
    ## from account
    ## from ir swap
    indexSupplied = set([ _['contents'][0] for _ in nonPerfAssump['interest'] ]) if 'interest' in nonPerfAssump else set()
    assert isinstance(indexSupplied,set),f"indexSupplied should be set but got type {type(indexSupplied)}  value: {indexSupplied}"
    if not indexSupplied.issuperset(indexRequired):
        e.append(f"Missing floater index:{indexRequired - indexSupplied}")
    return error+e,warning+w



def valAssumption(d, ma , error, warning) -> list:
    def _validate_single_assump(z):
        match z:
            case {'tag': 'PoolLevel'}:
                return [],[]
            case {'tag': 'ByIndex', 'contents':[assumps, _]}:
                _e = []
                _w = []
                _ids = set(flat([ assump[0] for assump in assumps ]))
                if not _ids.issubset(asset_ids):
                    _e.append(f"Not Valid Asset ID:{_ids - asset_ids}")
                if len(missing_asset_id := asset_ids - _ids) > 0:
                    _w.append(f"Missing Asset to set assumption:{missing_asset_id}")            
                return _e,_w
            case _:
                raise RuntimeError(f"Failed to match:{z}")
    
    asset_ids = set(range(len(list(query(d, ['pool', 'assets'])))))
    if ma is None:
        return error,warning
    else:
        e,w = _validate_single_assump(ma)
        return error+e,warning+w
