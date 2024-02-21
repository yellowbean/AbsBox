from absbox import API

localAPI = API("https://absbox.org/api/latest")

myPool = {'assets':[
            ["AdjustRateMortgage"
            ,{"originBalance": 240.0
             ,"originRate": ["floater"
                             ,0.03
                             ,{"index":"LIBOR1M"
                               ,"spread":0.01
                               ,"reset":["EveryNMonth","2023-11-01",2]}]
             ,"originTerm": 30 ,"freq": "monthly","type": "level"
             ,"originDate": "2023-05-01"
             ,"arm":{"initPeriod":6,"firstCap":0.015} }
            ,{"currentBalance": 240.0
             ,"currentRate": 0.08
             ,"remainTerm": 19
             ,"status": "current"}]],
         'cutoffDate':"2021-03-01"}

localAPI.runPool(myPool,
                 runAssump=[("interest"
                             ,("LIBOR1M",[["2021-01-01",0.05]
                                          ,["2022-02-01",0.055]
                                          ,["2022-07-01",0.0525]
                                          ,["2023-09-01",0.06]
                                          ,["2023-12-15",0.07]
                                          ,["2024-01-15",0.08]
                                          ,["2024-10-15",0.10]]))],
                  read=True)