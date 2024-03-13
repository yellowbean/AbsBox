from absbox.local.util import getValWithKs

def viz(x):
    """ visualized the waterfall (experiment) """
    import graphviz
    
    waterfall =  getValWithKs(x, ["分配规则","waterfall"])
    agg = getValWithKs(x, ["归集规则","collection"])
    accounts = getValWithKs(x, ["账户","accounts"])
    fees = getValWithKs(x, ["费用","fees"])
    bonds = getValWithKs(x, ["债券","bonds"])
    liqFacility = getValWithKs(x, ["流动性支持","liqFacility"])
    rateSwap = getValWithKs(x,[ "利率对冲","rateSwap"])
    currencySwap = getValWithKs(x, ["汇率对冲","currencySwap"])
    trigger = getValWithKs(x, ["触发事件","trigger"])
    name = getValWithKs(x, ["名称", "name"])
    #bonds = getattr(x,"状态","bonds")
    
    def build_agg(d, y):
        """ build aggregation rules ( how proceeds from pool are distributed to accounts)"""
        for s, a in y:
            d.node(a)
            d.node(s)
            d.edge(s, a)
            
    def build_action(action):
        match action:
            case ["账户转移", source, target] | ["transfer", source, target]:
                return f"{source} -> {target}"
            case ["按公式账户转移", _limit, source, target] | ["transferBy", _limit, source, target]:
                return f"{source} -> {_limit} -> {target}"
            case ["计提费用", *feeNames] | ["calcFee", *feeNames]:
                return f"{feeNames}"
            case ["计提利息", *bndNames] | ["calcInt", *bndNames]:
                return f"{bndNames}"
            case ["支付费用", source, target] | ["payFee", source, target]:
                return f"{source} -> {target}"
            case ["支付费用收益", source, target, _limit] | ["payFeeResidual", source, target, _limit]:
                return f"{source} -> {_limit} -> {target}"
            case ["支付费用收益", source, target] | ["payFeeResidual", source, target]:
                return f"{source} -> {target}"
            case ["支付费用限额", source, target, _limit] | ["payFeeBy", source, target, _limit]:
                return f"{source} -> {_limit} -> {target}"
            case ["支付利息", source, target] | ["payInt", source, target]:
                return f"{source} -> {target}"
            case ["支付本金", source, target, _limit] | ["payPrin", source, target, _limit]:
                return f"{source} -> {_limit} -> {target}"
            case ["支付本金", source, target] | ["payPrin", source, target]:
                return f"{source} -> {target}"
            case ["支付剩余本金", source, target] | ["payPrinResidual", source, target]:
                return f"{source} -> {target}"
            case ["支付期间收益", source, target]:
                return f"{source} -> {target}"
            case ["支付收益", source, target, limit] | ["payResidual", source, target, limit]:
                return f"{source} -> {_limit} -> {target}"
            case ["支付收益", source, target] | ["payResidual", source, target]:
                return f"{source} -> {target}"
            case ["储备账户转移", source, target, satisfy] | ["transferReserve", source, target, satisfy]:
                _map = {"源储备": "Source", "目标储备": "Target","Source":"Source","Target":"Target"}
                return f"{source} -> {satisfy} -> {target}"
            case ["出售资产", liq, target] | ["sellAsset", liq, target]:
                return f"{liq} -> {target}"
            case ["流动性支持", source, target, limit] | ["liqSupport", source, target, limit]:
                return f"{source} -> {limit} -> {target}"
            case ["流动性支持", source, target] | ["liqSupport", source, target]:
                return f"{source} -> {target}"
            case ["流动性支持偿还", rpt, source, target] | ["liqRepay", rpt, source, target]:
                return f"{source} -> {rpt} -> {target}"
            case ["流动性支持偿还", source, target] | ["liqRepay",  source, target]:
                return f"{source} -> {target}"
            case ["流动性支持报酬", source, target] | ["liqRepayResidual", source, target]:
                return f"{source} -> {target}"
            case ["流动性支持计提", target] | ["liqAccrue", target]:
                return f"{target}"
            case ["购买资产", liq, source, _limit] | ["buyAsset", liq, source, _limit]:
                return f"{source} -> {liq} -> {_limit} "
            case ["更新事件", idx] | ["runTrigger", idx]:
                return f"{idx}"
            case ["accrueAndPayIntBySeq", source, targets] | ["计提并支付利息", source, targets]:
                return f"{source} -> {targets}"
            case _:
                return f"{str(action)}"
            
    def build_waterfall2(d, st, lastNodeLabel, start_name:str, pre_names:list, index, actions, prevLabel=None):
        """ build waterfall actions for each deal status"""
        if_branching_id = ["条件执行", "If"]
        ifesle_branching_id = ["条件执行2", "IfElse"]
        new_index = index + 1
        _root_name = '@'.join(pre_names)
        if len(actions) == 0:
            return (start_name, lastNodeLabel)
        else:
            match actions:
                case [action, *rest_actions] if action[0] in set(if_branching_id+ifesle_branching_id) :
                    new_root_name = f"{st}-{_root_name}-{new_index}-{action[1]}"
                    d.node(new_root_name,f"{action[1]}",shape="diamond")
                    [ d.edge(root_name,new_root_name,label=prevLabel) for root_name in pre_names ]
                    if action[0] in if_branching_id:
                        if_true_actions = action[2:]
                        (_,last_action) = build_waterfall2(d, st, new_root_name, start_name, [f"{new_root_name}"], 0 ,if_true_actions, prevLabel="True")
                        #if len(rest_actions)>0:
                        return build_waterfall2(d, st, new_root_name, start_name, [last_action,new_root_name], 0 , rest_actions)
                    else:
                        if_true_actions = action[2]
                        if_false_actions = action[3]
                        (_,true_end_action) = build_waterfall2(d, st,new_root_name, start_name, [new_root_name], 0 ,if_true_actions, prevLabel="True")
                        (_,false_end_action) = build_waterfall2(d, st,new_root_name, start_name, [new_root_name], 0 ,if_false_actions, prevLabel="False")
                        #if len(rest_actions)>0:
                        return build_waterfall2(d, st, new_root_name, start_name, [true_end_action,false_end_action], 0 , rest_actions)
                case [action, *rest_actions] :
                    new_root_name = f"{st}-{_root_name}-{new_index}-{action[0]}"
                    d.node(new_root_name,f"{action[0]}:{build_action(action)}",shape="box")
                    [ d.edge(root_name, new_root_name, label=prevLabel) for root_name in pre_names ]
                    if start_name is None:
                        return build_waterfall2(d, st,new_root_name, new_root_name, [new_root_name], new_index ,rest_actions)
                    else:
                        return build_waterfall2(d, st,new_root_name, start_name, [new_root_name], new_index ,rest_actions)

    def build_subwaterfall(d, dealStatus, actions):
        """ build subwaterfall for each deal status """
        with d.subgraph(name=f"cluster_{dealStatus}", node_attr={'shape':'box'}) as c:
            c.attr(style='filled', color='lightgrey')
            c.node_attr.update(style='filled', color='white')
            (start_action, end_action) = build_waterfall2(c, dealStatus,None, None, [], 0, actions)
            c.attr(label=dealStatus)
            return (start_action, end_action)
            
    def build_waterfall(d, y):
        deal_status = y.keys()
        assert len(deal_status)>0,f"Waterfall shall be non-0, but {deal_status}"
        starts_ends_list = [build_subwaterfall(d, ds, waterfall[ds]) for ds in deal_status]
        return starts_ends_list
            
    dot = graphviz.Digraph('round-table', comment="", filename=name, format='svg')
    build_agg(dot, agg)
    starts_ends_list = build_waterfall(dot, waterfall)
    #dot.node("end",label="end")
    [ dot.edge('start',_[0], lhead = f"cluster_{_[0]}") for _ in starts_ends_list ]

    #[ dot.edge('end',_[1], ltail = f"cluster_{_[0]}") for _ in starts_ends_list ]
    return dot