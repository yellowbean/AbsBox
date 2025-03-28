from absbox.local.generic import Generic

test01 = Generic(
    "Custom Pay Dates"
     ,{"cutoff":"2021-02-28","closing":"2021-03-15","firstCollect":"2021-04-02","firstPay":"2021-04-15"
      ,"poolFreq":["CustomDate","2021-05-26","2021-06-26","2022-01-26"]
      ,"payFreq":["CustomDate","2021-05-26","2021-07-26","2022-03-26"]
      ,"stated":"2030-01-01"}
    ,{'清单':[["按揭贷款"
              ,{"放款金额":120,"放款利率":["固定",0.045],"初始期限":30
                ,"频率":"每月","类型":"等额本息","放款日":"2021-02-01"}
                ,{"当前余额":120
                ,"当前利率":0.08
                ,"剩余期限":30
                ,"状态":"正常"}]]
     ,'发行':{"资产池规模":150}}
    ,(("账户01",{"余额":0}),)
    ,(("A1",{"当前余额":100
             ,"当前利率":0.07
             ,"初始余额":100
             ,"初始利率":0.07
             ,"起息日":"2020-01-03"
             ,"利率":{"固定":0.08}
             ,"债券类型":{"过手摊还":None}})
      ,("B",{"当前余额":20
             ,"当前利率":0.0
             ,"初始余额":100
             ,"初始利率":0.07
             ,"起息日":"2020-01-03"
             ,"利率":{"固定":0.00}
             ,"债券类型":{"权益":None}
             }))
    ,(("信托费用",{"type":{"年化费率":[("债券余额",),0.02]},"feeStart":"2021-03-15"}),)
    ,{"未违约":[
         ["支付费用","账户01",['信托费用']]
         ,["计提支付利息","账户01",["A1"]]
         ,["支付本金","账户01",["A1"]]
         ,["支付本金","账户01",["B"]]
         ,["支付收益","账户01","B"]
     ]}
    ,(["利息回款","账户01"]
      ,["本金回款","账户01"]
      ,["早偿回款","账户01"]
      ,["回收回款","账户01"])
)
