import enum 


# Bond 
china_bondflow_fields = ["日期", "余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bondflow_fields_s = ["余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bond_cashflow = ["本金","利息","本息合计"]
english_bondflow_fields = ["date", "balance", "interest", "principal", "rate", "cash", "memo"]
english_bondflow_fields_s = ["balance", "interest", "principal", "rate", "cash", "memo"]

# Cumulative
china_cumStats = ["累计还款", "累计早偿", "累计拖欠", "累计违约", "累计回收", "累计损失"]
english_cumStats = ["CumPrincipal", "CumPrepay", "CumDelinq", "CumDefault", "CumRecovery", "CumLoss"]

# Pool
## mortgage
china_mortgage_flow_fields = ["余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失金额", "利率", "债务人数量","早偿手续费"]
english_mortgage_flow_fields = ["Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC","BorrowerNum","PrepayPenalty"]

china_mortgage_delinq_flow_fields = ["余额", "本金", "利息", "早偿金额", "拖欠金额", "违约金额", "回收金额", "损失金额", "利率", "债务人数量","早偿手续费"]
english_mortgage_delinq_flow_fields = ["Balance", "Principal", "Interest", "Prepayment", "Delinquency", "Default", "Recovery", "Loss", "WAC","BorrowerNum","PrepayPenalty"]

china_mortgage_flow_fields_d = ["日期"]+ china_mortgage_flow_fields
english_mortgage_flow_fields_d = ["Date"] + english_mortgage_flow_fields

china_mortgage_delinq_flow_fields_d = ["日期"] + china_mortgage_delinq_flow_fields
english_mortgage_delinq_flow_fields_d = ["Date"] + english_mortgage_delinq_flow_fields

## Rental
china_rental_flow = ['待收金额', '租金']
english_rental_flow = ['Balance', 'Rental']
china_rental_flow_d = ["日期"] + china_rental_flow
english_rental_flow_d = ["Date"] + english_rental_flow
## Loan flow
china_loan_flow = ["余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失金额", "利率"]
english_loan_flow = ["Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC"]
china_loan_flow_d = ["日期"] + china_loan_flow
english_loan_flow_d = ["Date"] + english_loan_flow

## Fixed flow 
china_fixed_flow = ["余额", "折旧", "累计折旧", "单元", "现金"]
english_fixed_flow = ["Balance", "Depreciation", "CumuDepreciation", "Unit", "Cash"]
china_fixed_flow_d = ["日期"] + china_fixed_flow
english_fixed_flow_d = ["Date"] + english_fixed_flow

## Underlying Bond Flow
china_uBond_flow = ["余额", "本金", "利息"]
english_uBond_flow = ["Balance", "Principal", "Interest"]
china_uBond_flow_d = ["日期"] + china_uBond_flow
english_uBond_flow_d = ["Date"] + english_uBond_flow

# Fee 
china_fee_flow_fields_d = ["日期", "余额", "支付", "剩余支付", "备注"]
english_fee_flow_fields_d = ["date", "balance", "payment", "due", "memo"]

# Account
china_acc_flow_fields_d = ["日期", "余额", "变动额", "备注"]
english_acc_flow_fields_d = ["date", "balance", "change", "memo"]


# LiqProvider
china_liq_flow_fields_d = ["日期", "限额", "变动额", "已提供", "利息", "费用", "备注"]
english_liq_flow_fields_d = ["date", "balance", "change", "used", "int", "premium", "memo"]

# Rate Swap 
china_rs_flow_fields_d = ["日期", "面额", "变动额", "支付", "收取", "净额", "备注"]
english_rs_flow_fields_d = ["date", "balance", "amount", "pay", "receive", "due", "memo"]

# Ledger
china_ledger_flow_fields_d = ["日期", "余额", "变动额", "备注"]
english_ledger_flow_fields_d = ["date", "balance", "amount", "comment"]

# deal status



datePattern = {"月末": "MonthEnd", "季度末": "QuarterEnd", "年末": "YearEnd", "月初": "MonthFirst",
               "季度初": "QuarterFirst", "年初": "YearFirst", "每年": "MonthDayOfYear", "每月": "DayOfMonth", "每周": "DayOfWeek"}

freqMap = {"每月": "Monthly", "每季度": "Quarterly", "每半年": "SemiAnnually", "每年": "Annually", "Monthly": "Monthly", "Quarterly": "Quarterly", "SemiAnnually": "SemiAnnually", "Annually": "Annually", "monthly": "Monthly", "quarterly": "Quarterly", "semiAnnually": "SemiAnnually", "annually": "Annually" }

rateLikeFormula = set(["bondFactor", "poolFactor", "cumPoolDefaultedRate","poolWaRate","bondWaRate", "资产池累计违约率", "债券系数", "资产池系数"])
intLikeFormula = set(["borrowerNumber", "monthsTillMaturity", "periodNum"])
boolLikeFormula = set(["trigger", "事件", "isMostSenior", "最优先", "isPaidOff","清偿完毕","rateTest","allTest","anyTest","比率测试","任一测试","所有测试"])

op_map = {">": "G", ">=": "GE", "<": "L", "<=": "LE", "=": "E"}

#Deal Cycle
chinaDealCycle = {"回收后":"EndCollection"
                 ,"回收动作后":"EndCollectionWF"
                 ,"分配前":"BeginDistributionWF"
                 ,"分配后":"EndDistributionWF"
                 ,"分配中":"InWF"}

englishDealCycle = {"BeforeCollect":"EndCollection"
                 ,"AfterCollect":"EndCollectionWF"
                 ,"BeforeDistribution":"BeginDistributionWF"
                 ,"AfterDistribution":"EndDistributionWF"
                 ,"InDistribution":"InWF"}

dealCycleMap = chinaDealCycle | englishDealCycle

#Asset pricing 
assetPricingHeader = {
    "chinese":["估值", "WAL", "Duration", "Convexity", "AccruedInterest"]
    ,"english":["Pricing", "WAL", "Duration", "Convexity", "AccruedInterest"]
}

#account fields
accountHeader = {
    "chinese": {"idx": "日期", "change": "变动额", "bal": ("期初余额", '余额', "期末余额")}
    ,"english": {"idx": "date", "change": "change", "bal": ("begin balance", 'balance', "end balance")}
}


validCutoffFields = {
    "资产池规模": "IssuanceBalance"
    ,"IssuanceBalance": "IssuanceBalance"
    ,"CumulativeDefaults":"HistoryDefaults"
    ,"累计违约余额":"HistoryDefaults"
}

dealStatusLog = {'cn': ["日期", "旧状态", "新状态"], 'en': ["Date", "From", "To"]}

dealStatusMap = {"en": {'amort': "Amortizing", 'def': "Defaulted", 'acc': "Accelerated", 'end': "Ended",
                        'called': "Called",
                        'pre': "PreClosing",'revol':"Revolving"
                        ,'ramp':"RampUp"}
                , "cn": {'amort': "摊销", 'def': "违约", 'acc': "加速清偿", 'end': "结束", 'pre': "设计","revol":"循环"
                        ,'called':"清仓回购"
                        ,'ramp':"RampUp"}}

cfIndexMap = {'cn':"日期",'en':"Date","english":"Date","chinese":"日期"}


class DC(enum.Enum):  # TODO need to check with HS code
    DC_30E_360 = "DC_30E_360"
    DC_30Ep_360 = "DC_30Ep_360"
    DC_ACT_360 = "DC_ACT_360"
    DC_ACT_365A = "DC_ACT_365A"
    DC_ACT_365L = "DC_ACT_365L"
    DC_NL_365 = "DC_NL_365"
    DC_ACT_365F = "DC_ACT_365F"
    DC_ACT_ACT = "DC_ACT_ACT"
    DC_30_360_ISDA = "DC_30_360_ISDA"
    DC_30_360_German = "DC_30_360_German"
    DC_30_360_US = "DC_30_360_US"


class InspectTags(str, enum.Enum):
    """ Inspect Tag when reading deal run logs """
    InspectBal = "InspectBal"
    InspectBool = "InspectBool"
    InspectRate = "InspectRate"
    InspectInt = "InspectInt"


class ValidationMsg(str, enum.Enum):
    """ Validation Message Type """
    Warning = "WarningMsg"
    Error = "ErrorMsg"