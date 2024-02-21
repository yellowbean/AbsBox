deal_data = {
    "name":"Period Fee"
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
    ,"fees":{"trusteeFee":{"type":{"fixFee":30}}
            ,"serviceFee":{"type":{"byPeriod":15}}
            ,"serviceFee2":{"type":{"byTable":["MonthEnd"
                                               ,("*",("poolBalance",),0.01)
                                               ,[(0,5),(2,10),(10,15)]]
                                   }}}
    ,"collect":[["CollectedCash","acc01"]]
    ,"waterfall":{"Amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["payFee","acc01",['serviceFee2']]
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}

from absbox import API, mkDeal
localAPI = API("http://localhost:8081",check=False)

deal = mkDeal(deal_data)

r = localAPI.run(deal
                 ,poolAssump = ("Pool"
                                ,("Mortgage"
                                 ,{"CDR":0.02} ,None, None, None)
                                 ,None
                                 ,None)
                 ,runAssump = [("interest",("LIBOR6M",0.04))
                               ,("inspect"
                                 ,["MonthEnd",("factor",("poolBalance",),0.01)])
                              ]
                 ,read=True)