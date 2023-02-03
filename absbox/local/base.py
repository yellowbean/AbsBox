
# Bond 
china_bondflow_fields = ["日期", "余额", "利息", "本金", "执行利率", "本息合计", "备注"]
china_bondflow_fields_s = ["余额", "利息", "本金", "执行利率", "本息合计", "备注"]
english_bondflow_fields = ["date", "balance", "interest", "principal", "rate", "cash", "memo"]
english_bondflow_fields_s = ["balance", "interest", "principal", "rate", "cash", "memo"]

# Pool
## mortgage
china_mortgage_flow_fields = ["余额", "本金", "利息", "早偿金额", "违约金额", "回收金额", "损失金额", "利率"]
english_mortgage_flow_fields = ["Balance", "Principal", "Interest", "Prepayment", "Default", "Recovery", "Loss", "WAC"]
china_mortgage_flow_fields_d = ["日期"]+ china_mortgage_flow_fields
english_mortgage_flow_fields_d = ["Date"] + english_mortgage_flow_fields
## Rental
china_rental_flow = ['租金']
english_rental_flow = ['Rental']
china_rental_flow_d = ["日期"] + china_rental_flow
english_rental_flow_d = ["Date"] + english_rental_flow