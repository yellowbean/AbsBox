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
    w = d['waterfall']
    #optional
    if d['ledgers']:
        ledger_names = set(d['ledgers'].keys())
    assert w is not None ,"Waterfall is None"

    for wn,waterfallActions in w.items():
        for idx,(pre,action) in enumerate(waterfallActions):
            match action:
                case {"tag":'PayFeeBy', "contents":[_, accs, fees]}:
                    if (not inSet(accs,acc_names)) or (not inSet(fees,fee_names)):
                        error.append(f"{wn},{idx}")
                case {"tag":'PayFee', "contents":[accs, fees]}:
                    if (not inSet(accs,acc_names)) or (not inSet(fees,fee_names)):
                        error.append(f"{wn},{idx}")     
                case {"tag":'PayInt', "contents":[acc, bonds]}:
                    if (not inSet([acc],acc_names)) or (not inSet(bonds,bnd_names)):
                        error.append(f"{wn},{idx}")  
                case {"tag":'PayPrin', "contents":[acc, bonds]}:
                    if (not inSet([acc],acc_names)) or (not inSet(bonds,bnd_names)):
                        error.append(f"{wn},{idx}")  
                case {"tag":'PayPrinBy', "contents":[_, acc, bond]}:
                    if (not inSet([acc],acc_names)) or (not inSet([bond],bnd_names)):
                        error.append(f"{wn},{idx}")  
                case {"tag":'PayResidual', "contents":[_, acc, bond]}:
                    if (not inSet([acc],acc_names)) or (not inSet([bond],bnd_names)):
                        error.append(f"{wn},{idx}")  
                case {"tag":'Transfer',"contents":[acc1,acc2]}:
                    if (not inSet([acc1,acc2],acc_names)):
                        error.append(f"{wn},{idx}")
                case {"tag":'TransferBy',"contents":[_,acc1,acc2]}:
                    if (not inSet([acc1,acc2],acc_names)):
                        error.append(f"{wn},{idx}")
                case {"tag":'PayTillYield',"contents":[acc, bonds]}:
                    if (not inSet([acc],acc_names)) or (not inSet(bonds,bnd_names)):
                        error.append(f"{wn},{idx}")
                case {"tag":'PayFeeResidual',"contents":[_,acc,fee]}:
                    if (not inSet([acc],acc_names)) or (not inSet([fee],fee_names)):
                        error.append(f"{wn},{idx}")
                case _:
                    pass
    
    return (error,warning)

def valReq(reqSent) -> list:
    error = []
    warning = []
    req = json.loads(reqSent)
    match req :
        case {"tag":"SingleRunReq","contents":[{"contents":d}, ma, mp]}:
            error, warning = valDeal(d, error, warning)
            error, warning = valAssumption(d, ma, error, warning)
        case {"tag":"MultiScenarioRunReq","contents":[{"contents":d}, mam, mp]}:
            error, warning = valDeal(d, error, warning)
        case {"tag":"MultiDealRunReq","contents":[dm, ma, mp]}:
            error, warning = valAssumption(ma, error, warning)
        case _:
            raise RuntimeError(f"Failed to match request:{req}")

    return error, warning

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
    
    asset_ids = set(range(len(query(d, ['pool', 'assets']))))
    
    if ma is None:
        return error,warning
    else:
        e,w = _validate_single_assump(ma)
        return error+e,warning+w
