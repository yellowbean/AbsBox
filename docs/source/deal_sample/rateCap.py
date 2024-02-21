deal_data = {
    "name":"Sample with Interest Cap"
    ,"dates":{"cutoff":"2021-06-01"
              ,"closing":"2021-07-15"
              ,"firstPay":"2021-08-26"
              ,"payFreq":["DayOfMonth",20]
              ,"poolFreq":"MonthEnd"
              ,"stated":"2030-01-01"}
    ,"pool":{'assets':[["Mortgage"
                        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
                          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
                          ,{"currentBalance":2200
                          ,"currentRate":0.08
                          ,"remainTerm":30
                          ,"status":"current"}]]
            }
    ,"accounts":{"acc01":{"balance":0}}
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
    ,"fees":{"trusteeFee":{"type":{"fixFee":30}}}
    ,"collect":[["CollectedCash","acc01"]]
    ,"waterfall":{"Amortizing":[
         ['settleCap',"acc01","cap1"]
         ,["payFee","acc01",['trusteeFee']]         
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}

from absbox import API,mkDeal
localAPI = API("http://localhost:8081",check=False)

cap = {
    "cap1":{"index":"LIBOR6M"
            ,"strike":[("2022-01-01",0.02)
                       ,("2023-01-01",0.03)
                       ,("2024-01-01",0.05)]
            ,"base":{"fix":10000}
            ,"start":"2022-01-01"
            ,"end":"2025-01-01"
            ,"settleDates":"QuarterEnd"
            ,"rate":0.035
            ,"lastSettleDate":None
            ,"netCash":100
            }
}

deal = mkDeal(deal_data|{"rateCap":cap})

r = localAPI.run(deal
                 ,poolAssump = ("Pool"
                                ,("Mortgage"
                                 ,{"CDR":0.02} ,None, None, None)
                                 ,None
                                 ,None)
                 ,runAssump = [("interest"
                               ,("LIBOR6M",0.04))]
                 ,read=True)

#r['rateCap']['cap1']
