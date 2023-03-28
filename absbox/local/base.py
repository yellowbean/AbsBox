
# Bond 
china_bondflow_fields = ["日期", "余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bondflow_fields_s = ["余额", "利息", "本金", "执行利率", "本息合计", "备注"]
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
china_liq_flow_fields_d = ["日期", "限额", "变动额", "已提供","备注"]
english_liq_flow_fields_d = ["date", "balance", "change", "used","memo"]


