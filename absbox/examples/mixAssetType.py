from absbox import mkDeal

deal_data = {
    "name":"Multiple Pools with Mixed Asset"
    ,"dates":{"cutoff":"2021-06-01"
              ,"closing":"2021-07-15"
              ,"firstPay":"2021-08-26"
              ,"payFreq":["DayOfMonth",20]
              ,"poolFreq":"MonthEnd"
              ,"stated":"2030-01-01"}
    ,"pool":{"PoolA":{'assets':[["Mortgage"
                        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
                          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
                          ,{"currentBalance":2200
                          ,"currentRate":0.08
                          ,"remainTerm":30
                          ,"status":"current"}]]},
             "PoolB":{'assets':[["Loan"
                              ,{"originBalance": 80000
                                ,"originRate": ["floater",0.045,{"index":"SOFR3M"
                                                                ,"spread":0.01
                                                                ,"reset":"QuarterEnd"}]
                                ,"originTerm": 60
                                ,"freq": "Monthly"
                                ,"type": "i_p"
                                ,"originDate": "2021-02-01"}
                              ,{"currentBalance": 65000
                                ,"currentRate": 0.06
                                ,"remainTerm": 60
                                ,"status": "Current"}]]}
            }
    ,"accounts":{"acc01":{"balance":0}
                ,"acc02":{"balance":0}}
    ,"bonds":{"A1":{"balance":1000
                 ,"rate":0.07
                 ,"originBalance":1000
                 ,"originRate":0.07
                 ,"startDate":"2020-01-03"
                 ,"rateType":{"Fixed":0.08}
                 ,"bondType":{"Sequential":None}}
             ,"B":{"balance":1000
                     ,"rate":0.0
                     ,"originBalance":1000
                     ,"originRate":0.07
                     ,"startDate":"2020-01-03"
                     ,"rateType":{"Fixed":0.00}
                     ,"bondType":{"Equity":None}}}
    ,"fees":{"trusteeFee":{"type":{"fixFee":30}}
            ,"serviceFee":{"type":{"annualPctFee":[("poolBalance","PoolB"),0.02]}}
            ,"serviceFee2":{"type":{"byTable":["MonthEnd"
                                               ,("const",1)
                                               ,[(0,5),(2,10),(10,15)]]
                                   }}}
    ,"collect":[[["PoolA"],"CollectedCash","acc01"]
               ,[["PoolB"],"CollectedCash","acc02"]]
    ,"waterfall":{"Amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["calcAndPayFee","acc01",['serviceFee']]
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}


mixedAsset_test01 = mkDeal(deal_data)
