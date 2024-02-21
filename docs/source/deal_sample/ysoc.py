from absbox import API

## make sure it is greater with 0.24.1
localAPI = API("http://localhost:8081",lang='english',check=False)

deal_data = {
    "name":"Yield Supplement Overcollateralization"
    ,"dates":{"cutoff":"2021-06-01"
              ,"closing":"2021-07-15"
              ,"firstPay":"2021-08-26"
              ,"payFreq":["DayOfMonth",20]
              ,"poolFreq":"MonthEnd"
              ,"stated":"2030-01-01"}
    ,"pool":{'assets':[["Mortgage"
                        ,{"originBalance":1300,"originRate":["fix",0.045],"originTerm":30
                          ,"freq":"Monthly","type":"Level","originDate":"2021-03-05"}
                          ,{"currentBalance":1300
                          ,"currentRate":0.08
                          ,"remainTerm":30
                          ,"status":"current"}]]}
    ,"accounts":{"acc01":{"balance":100}
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
    ,"fees":{}
    ,"collect":[["CollectedCash","acc01"]]
    ,"waterfall":{"Amortizing":[
          ["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]
           ,{"limit":
             {"formula":("-",("schedulePoolValuation",('PvRate',("poolWaRate",)))
                            ,("schedulePoolValuation",('PvRate',("max",("poolWaRate",),("const",0.09)))))
             }}]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}
if __name__ == '__main__':
    from absbox import API
    localAPI = API("https://absbox.org/api/latest")

    from absbox import mkDeal
    deal = mkDeal(deal_data) 

    r = localAPI.run(deal
                    ,poolAssump = None
                    ,runAssump = [("inspect",(["DayOfMonth",20],("schedulePoolValuation",('PvRate',0.08)))
                                              ,(["DayOfMonth",20],("schedulePoolValuation",('PvRate',("max",("poolWaRate",),("const",0.09)))))
                                              ,(["DayOfMonth",20],("-",("schedulePoolValuation",('PvRate',("poolWaRate",)))
                                                                ,("schedulePoolValuation",('PvRate',("max",("poolWaRate",),("const",0.09))))))
                                    
                                    )
                                  ]
                    ,read=True)

# from absbox.local.util import unifyTs
# unifyTs(r['result']['inspect'].values())
# r['bonds']['A1']