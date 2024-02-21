from absbox import Generic

test01 = Generic(
    "TEST01"
    ,{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":30
          ,"status":"current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":1000
             ,"rate":0.07
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,(("trusteeFee",{"type":{"fixFee":30}}),)
    ,{"Amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]
     ]
     ,"Accelerated":[
         ["accrueAndPayInt","acc01",["A1"]]
         ,["payPrinResidual","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]         
     ]}
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None
    ,None
    ,{"AfterCollect":{
        "lowerThanBndTrigger": 
         {"condition":[("bondBalance",),">"
                       ,("sum"
                         ,("accountBalance",)
                         ,("poolBalance",)
                         ,("factor"
                           ,("cumPoolCollection","Delinquencies")
                           ,0.5)
                        )]
          ,"effects":("newStatus","Accelerated")
          ,"status":False
          ,"curable":False}}}
    ,("PreClosing","Amortizing")
    )


#r = localAPI.run(test01
#               ,poolAssump = ("Pool",("Mortgage","Delinq"
#                                      ,{"DelinqCDR":0.17715,"Lag":2,"DefaultPct":0.8}
#                                      ,None
#                                      ,{"Rate":0.7,"Lag":3}
#                                      ,None)
#                                       ,None
#                                       ,None)
#               ,runAssump = [("inspect"
#                              ,("MonthEnd",("status",("Amortizing")))
#                              ,("MonthEnd",("accountBalance",))
#                              ,("MonthEnd",("poolBalance",))
#                              ,("MonthEnd",("factor"
#                                               ,("cumPoolCollection","Delinquencies")
#                                               ,0.5))
#                              ,("MonthEnd",("bondBalance",))
#                              ,("MonthEnd",("trigger","AfterCollect","lowerThanBndTrigger"))
#                             )]
#               ,read=True)