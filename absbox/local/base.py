
# Bond 
china_bondflow_fields = ["日期", "余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bondflow_fields_s = ["余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bond_cashflow = ["本金","利息","本息合计"]
english_bondflow_fields = ["date", "balance", "interest", "principal", "rate", "cash", "memo"]
english_bondflow_fields_s = ["balance", "interest", "principal", "rate", "cash", "memo"]

# Pool
## mortgage
china_mortgage_flow_fields = ["余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失金额", "利率", "债务人数量"]
english_mortgage_flow_fields = ["Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC","BorrowerNum"]
china_mortgage_flow_fields_d = ["日期"]+ china_mortgage_flow_fields
english_mortgage_flow_fields_d = ["Date"] + english_mortgage_flow_fields
## Rental
china_rental_flow = ['待收金额','租金']
english_rental_flow = ['Balance','Rental']
china_rental_flow_d = ["日期"] + china_rental_flow
english_rental_flow_d = ["Date"] + english_rental_flow
## Loan flow
china_loan_flow = ["余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失金额", "利率"]
english_loan_flow = ["Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC"]
china_loan_flow_d = ["日期"] + china_loan_flow
english_loan_flow_d = ["Date"] + english_loan_flow

# Fee 
china_fee_flow_fields_d = ["日期", "余额", "支付", "剩余支付", "备注"]
english_fee_flow_fields_d = ["date", "balance", "payment", "due", "memo"]

# Account
china_acc_flow_fields_d = ["日期", "余额", "变动额", "备注"]
english_acc_flow_fields_d = ["date", "balance", "change", "memo"]


# LiqProvider
china_liq_flow_fields_d = ["日期", "限额", "变动额", "已提供","利息","费用","备注"]
english_liq_flow_fields_d = ["date", "balance", "change", "used","int","premium","memo"]

# Rate Swap 
china_rs_flow_fields_d = ["日期", "面额", "变动额", "支付","收取","净额","备注"]
english_rs_flow_fields_d = ["date", "balance", "amount", "pay","receive","due","memo"]

# Ledger
china_ledger_flow_fields_d = ["日期", "余额", "变动额", "备注"]
english_ledger_flow_fields_d = ["date", "balance", "amount", "comment"]

# Index



# deal status



datePattern = {"月末": "MonthEnd", "季度末": "QuarterEnd", "年末": "YearEnd", "月初": "MonthFirst",
               "季度初": "QuarterFirst", "年初": "YearFirst", "每年": "MonthDayOfYear", "每月": "DayOfMonth", "每周": "DayOfWeek"}


freqMap = {"每月": "Monthly", "每季度": "Quarterly", "每半年": "SemiAnnually", "每年": "Annually", "Monthly": "Monthly", "Quarterly": "Quarterly", "SemiAnnually": "SemiAnnually", "Annually": "Annually", "monthly": "Monthly", "quarterly": "Quarterly", "semiAnnually": "SemiAnnually", "annually": "Annually"
           }

baseMap = {"资产池余额": "CurrentPoolBalance"
           , "资产池期末余额": "CurrentPoolBalance"
           , "资产池期初余额": "CurrentPoolBegBalance"
           , "资产池初始余额": "OriginalPoolBalance"
           , "初始资产池余额": "OriginalPoolBalance"
           , "资产池当期利息": "PoolCollectionInt"
           , "债券余额": "CurrentBondBalance"
           , "债券初始余额": "OriginalBondBalance"
           , "当期已付债券利息": "LastBondIntPaid"
           , "当期已付费用": "LastFeePaid"
           , "当期未付债券利息": "CurrentDueBondInt"
           , "当期未付费用": "CurrentDueFee"}
           
           
#pool income mapping
poolSourceMapping = {"利息回款": "CollectedInterest"
                    , "本金回款": "CollectedPrincipal"
                    , "早偿回款": "CollectedPrepayment"
                    , "回收回款": "CollectedRecoveries"
                    , "租金回款": "CollectedRental"
                    , "CollectedInterest": "CollectedInterest"
                    , "CollectedPrincipal": "CollectedPrincipal"
                    , "CollectedPrepayment": "CollectedPrepayment"
                    , "CollectedRecoveries": "CollectedRecoveries"
                    , "CollectedRental": "CollectedRental"
                     }

op_map = {
    ">":"G"
    ,">=":"GE"
    ,"<":"L"
    ,"<=":"LE"
    ,"=":"E"
}

dealStatusMap = {"摊还": "Current", "加速清偿": "Accelerated", "循环": "Revolving"}


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

#Asset pricing 
assetPricingHeader = {
    "chinese":["估值","WAL","Duration","Convexity","AccruedInterest"]
    ,"english":["Pricing","WAL","Duration","Convexity","AccruedInterest"]
}