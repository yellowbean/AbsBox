from absbox import mkDeal, API

deal_data = {
    "name":"Sample with Interest Swap"
    ,"dates":{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,"pool":{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]}
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
    ,"collect":[["CollectedInterest","acc01"]
              ,["CollectedPrincipal","acc01"]
              ,["CollectedPrepayment","acc01"]
              ,["CollectedRecoveries","acc01"]]
    ,"waterfall":{"amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["settleSwap","acc01","swap1"]
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
}


if __name__ == '__main__':
    from absbox import API
    localAPI = API("http://localhost:8081")

    swap = {
        "swap1":{"settleDates":"MonthEnd"
                ,"pair":[("LPR5Y",0.01),0.05]
                ,"base":{"formula":("poolBalance",)}
                ,"start":"2021-06-25"
                ,"balance":2093.87}
    }

    deal = mkDeal(deal_data|{"rateSwap":swap})

    r = localAPI.run(deal
                    ,runAssump = [("interest"
                                    ,("LPR5Y",[["2022-01-01",0.05]
                                              ,["2023-01-01",0.06]]))]
                    ,read=True)

    r['rateSwap']['swap1']