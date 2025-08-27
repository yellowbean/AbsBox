from absbox import Generic
import toolz as tz
from lenses import lens


test01 = Generic(
    "TEST01- preclosing",
    {
        "cutoff": "2021-03-01",
        "closing": "2021-04-15",
        "firstPay": "2021-07-26",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ]
    },
    [
        ["CollectedInterest", "acc01"],
        ["CollectedPrincipal", "acc01"],
        ["CollectedPrepayment", "acc01"],
        ["CollectedRecoveries", "acc01"],
    ],
    None,
    None,
    None,
    None,
    ("PreClosing", "Amortizing"),
)


test02 = Generic(
    "TEST02- Amortizing Deal",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [
        ["CollectedInterest", "acc01"],
        ["CollectedPrincipal", "acc01"],
        ["CollectedPrepayment", "acc01"],
        ["CollectedRecoveries", "acc01"],
    ],
    None,
    None,
    None,
    None,
    "Amortizing",
)


test03 = Generic(
    "PAC 01",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [["CollectedCash", "acc01"]],
    None,
    None,
    None,
    None,
    "Amortizing",
)

test04 = Generic(
    "TEST04- preclosing - multi-assets",
    {
        "cutoff": "2021-03-01",
        "closing": "2021-04-15",
        "firstPay": "2021-07-26",
        "firstCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 1400,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 1400,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ],
            [
                "Mortgage",
                {
                    "originBalance": 800,
                    "originRate": ["fix", 0.045],
                    "originTerm": 36,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 800,
                    "currentRate": 0.05,
                    "remainTerm": 36,
                    "status": "current",
                },
            ]            
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ]
    },
    [
        ["CollectedInterest", "acc01"],
        ["CollectedPrincipal", "acc01"],
        ["CollectedPrepayment", "acc01"],
        ["CollectedRecoveries", "acc01"],
    ],
    None,
    None,
    None,
    None,
    ("PreClosing", "Amortizing"),
)

test05 = Generic(
    "TEST05- preclosing - multi-assets- revolving",
    {
        "cutoff": "2021-03-01",
        "closing": "2021-04-15",
        "firstPay": "2021-07-26",
        "firstCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 1400,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 1400,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ],
            [
                "Mortgage",
                {
                    "originBalance": 800,
                    "originRate": ["fix", 0.045],
                    "originTerm": 36,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 800,
                    "currentRate": 0.05,
                    "remainTerm": 36,
                    "status": "current",
                },
            ]            
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["if", ["date", "<", "2021-09-30"]
                 , ["buyAsset",["Current|Defaulted", 1.0, 0] , "acc01"]
            ],
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ]
    },
    [
        ["CollectedInterest", "acc01"],
        ["CollectedPrincipal", "acc01"],
        ["CollectedPrepayment", "acc01"],
        ["CollectedRecoveries", "acc01"],
    ],
    None,
    None,
    None,
    None,
    ("PreClosing", "Amortizing"),
)


Irr01 = Generic(
    "IRR Case",
    {
        "cutoff": "2021-03-01",
        "closing": "2021-04-01",
        "firstPay": "2021-06-20",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthFirst",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 20,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 20,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2021-04-01",
                "rateType": {"Fixed": 0.08},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2021-04-01",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    tuple(),
    {
        "amortizing": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrin", "acc01", ["A1"]],
            ["payPrin", "acc01", ["B"]],
            ["payIntResidual", "acc01", "B"],
        ]
    },
    [
        ["CollectedInterest", "acc01"],
        ["CollectedPrincipal", "acc01"],
        ["CollectedPrepayment", "acc01"],
        ["CollectedRecoveries", "acc01"],
    ],
    None,
    None,
    None,
    None,
    ("PreClosing", "Amortizing"),
)

pac01 = Generic(
    "PAC 01",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "bondType": {
                    "PAC": [
                        ["2021-07-20", 800],
                        ["2021-08-20", 750],
                        ["2021-09-20", 700],
                        ["2021-10-20", 650],
                        ["2021-11-20", 0],
                    ]
                },
                "lastAccrueDate": "2021-04-15",
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "lastAccrueDate": "2021-04-15",
                "bondType": "Equity",
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1"]],
            ["payPrinBySeq", "acc01", ["A1", "B"]],
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [["CollectedCash", "acc01"]],
    None,
    None,
    None,
    None,
    "Amortizing",
)


pac02 = Generic(
    "PAC 02",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A1",
            {
                "balance": 1000,
                "rate": 0.07,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "bondType": {
                    "PAC": [
                        ["2021-07-20", 800],
                        ["2021-08-20", 750],
                        ["2021-09-20", 700],
                        ["2021-10-20", 650],
                        ["2021-11-20", 0],
                    ],
                    "anchorBonds": ["A2"],
                },
                "lastAccrueDate": "2021-04-15",
            },
        ),
        (
            "A2",
            {
                "balance": 150,
                "rate": 0.07,
                "originBalance": 150,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "bondType": "Seq",
                "lastAccrueDate": "2021-04-15",
            },
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "lastAccrueDate": "2021-04-15",
                "bondType": "Equity",
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayInt", "acc01", ["A1", "A2"]],
            ["payPrinBySeq", "acc01", ["A1", "A2"]] ,
            ["payPrin", "acc01", ["A1"]],
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [["CollectedCash", "acc01"]],
    None,
    None,
    None,
    None,
    "Amortizing",
)

pac03 = Generic(
    "PAC 03 - Pac on Group"
    ,{"lastCollect":"2021-03-01","lastPay":"2021-04-15"
      ,"nextPay":"2021-07-26","nextCollect":"2021-04-28"
     ,"payFreq":["DayOfMonth",20] ,"poolFreq":"MonthEnd"
     ,"stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":30
          ,"status":"current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A", ("bondGroup", 
             {"A1":{"balance":1000
             ,"rate":0.07
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":("fix",0.08)
             ,"bondType":"Seq"
             ,"lastAccrueDate":"2021-04-15"
            },
             "A2":{"balance":200
             ,"rate":0.07
             ,"originBalance":200
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":("fix",0.08)
             ,"bondType":"Seq"
             ,"lastAccrueDate":"2021-04-15"
            },}
            ,{"PAC":
               [["2021-07-20",1050]
               ,["2021-08-20",980]
               ,["2021-09-20",915]
               ,["2021-10-20",880]
               ,["2021-11-20",0]
               ]
            #,"anchorBonds":["A2"]
             }))
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":("fix",0.08)
             ,"lastAccrueDate":"2021-04-15"
             ,"bondType":"Equity"
             }))
    ,tuple()
    ,{"default":[
         ["accrueAndPayIntByGroup","acc01","A", "byName"]
         ,["payPrinByGroup","acc01","A", "byName"]
         ,["payIntResidual","acc01","B"]
     ],
     }
    ,[["CollectedCash","acc01"]]
    ,None
    ,None
    ,None
    ,None
    ,"Amortizing"
    )

pac04 = Generic(
    "PAC 04 - Pac on Group with anchor bonds",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A",
            (
                "bondGroup",
                {
                    "A1": {
                        "balance": 1000,
                        "rate": 0.07,
                        "originBalance": 1000,
                        "originRate": 0.07,
                        "startDate": "2020-01-03",
                        "rateType": ("fix", 0.08),
                        "bondType": "Seq",
                        "lastAccrueDate": "2021-04-15",
                    },
                    "A2": {
                        "balance": 200,
                        "rate": 0.07,
                        "originBalance": 200,
                        "originRate": 0.07,
                        "startDate": "2020-01-03",
                        "rateType": ("fix", 0.08),
                        "bondType": "Seq",
                        "lastAccrueDate": "2021-04-15",
                    },
                },
                {
                    "PAC": [
                        ["2021-07-20", 1050],
                        ["2021-08-20", 980],
                        ["2021-09-20", 915],
                        ["2021-10-20", 880],
                        ["2021-11-20", 850],
                        ["2021-12-20", 0],
                    ]
                    ,"anchorBonds":["M"]
                },
            ),
        ),
        ("M", {"balance": 250, "rate": 0.0, "originBalance": 250, "originRate": 0.07
               , "startDate": "2020-01-03", "rateType": ("fix", 0.08), "lastAccrueDate": "2021-04-15"
               , "bondType": "Seq"}),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "lastAccrueDate": "2021-04-15",
                "bondType": "Equity",
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayIntByGroup", "acc01", "A", "byName"],
            ["payPrinByGroup", "acc01", "A", "byName"],
            ["accrueAndPayInt","acc01",["M"]],
            ["payPrinByGroup", "acc01", "A", "byName"],
            ["payPrin","acc01",["M"]]
            
            # ,["payPrin","acc01",["A1"]]
            ,
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [["CollectedCash", "acc01"]],
    None,
    None,
    None,
    None,
    "Amortizing",
)


bondGrp = Generic(
    "Bond Group",
    {
        "lastCollect": "2021-03-01",
        "lastPay": "2021-04-15",
        "nextPay": "2021-07-26",
        "nextCollect": "2021-04-28",
        "payFreq": ["DayOfMonth", 20],
        "poolFreq": "MonthEnd",
        "stated": "2030-01-01",
    },
    {
        "assets": [
            [
                "Mortgage",
                {
                    "originBalance": 2200,
                    "originRate": ["fix", 0.045],
                    "originTerm": 30,
                    "freq": "Monthly",
                    "type": "Level",
                    "originDate": "2021-02-01",
                },
                {
                    "currentBalance": 2200,
                    "currentRate": 0.08,
                    "remainTerm": 30,
                    "status": "current",
                },
            ]
        ]
    },
    (("acc01", {"balance": 0}),),
    (
        (
            "A",
            (
                "bondGroup",
                {
                    "A1": {
                        "balance": 1000,
                        "rate": 0.07,
                        "originBalance": 1000,
                        "originRate": 0.07,
                        "startDate": "2020-01-03",
                        "rateType": ("fix", 0.08),
                        "bondType": "Seq",
                        "lastAccrueDate": "2021-04-15",
                    },
                    "A2": {
                        "balance": 800,
                        "rate": 0.07,
                        "originBalance": 800,
                        "originRate": 0.07,
                        "startDate": "2020-01-03",
                        "rateType": ("fix", 0.08),
                        "bondType": "Seq",
                        "lastAccrueDate": "2021-04-15",
                    },
                },
            ),
        ),
        (
            "B",
            {
                "balance": 1000,
                "rate": 0.0,
                "originBalance": 1000,
                "originRate": 0.07,
                "startDate": "2020-01-03",
                "rateType": ("fix", 0.08),
                "lastAccrueDate": "2021-04-15",
                "bondType": "Equity",
            },
        ),
    ),
    tuple(),
    {
        "default": [
            ["accrueAndPayIntByGroup", "acc01", "A", ("byName", "A2","A1")],
            ["payPrinByGroup", "acc01", "A", ("byName", "A2","A1")],
            ["accrueAndPayInt","acc01",["B"]],
            ["payPrin","acc01",["B"]],
            ["payIntResidual", "acc01", "B"],
        ],
    },
    [["CollectedCash", "acc01"]],
    None,
    None,
    None,
    None,
    "Amortizing",
)

import datetime
from dateutil.relativedelta import relativedelta


cf = [[ (datetime.datetime.strptime("2021-03-01", "%Y-%m-%d") + relativedelta(months=_)).strftime("%Y-%m-%d"), (29-_)*75] 
      for _ in range(30) ]

fixPct = (1.00,0.07)
floatPcts = []
projCf =  ["ProjectedByFactor", cf, "MonthEnd", fixPct, floatPcts] 

test06 = test01 & lens.name.set("TEST06 - ProjectByFactor")\
                & lens.pool['assets'].set([projCf])

### current deal 

currentDates = {"collect":["2021-04-01","2021-06-01"]
                ,"pay":["2021-04-26","2021-07-15"]
                ,"stated":"2030-01-01"
                ,"poolFreq":"MonthEnd"
                ,"payFreq":["DayOfMonth",20]
                }

test07 = test01 & lens.name.set("TEST07 - CurrentDeal")\
                & lens.status.set("amortizing")\
                & lens.pool.modify(lambda x: tz.assoc(x
                                                      , "issuanceStat"
                                                      ,{"IssuanceBalance":1800}))\
                & lens.dates.set(currentDates)
                
test08 = test01 & lens.name.set("TEST08 - CurrentDeal&CustomeDate")\
                & lens.status.set("amortizing")\
                & lens.pool.modify(lambda x: tz.assoc(x
                                                      , "issuanceStat"
                                                      ,{"IssuanceBalance":1800}))\
                & lens.dates.set({"collect":["2021-04-01","2021-06-01"]
                                ,"pay":["2021-04-26","2021-07-15"]
                                ,"stated":"2030-01-01"
                                ,"poolFreq":["CustomDate","2021-07-01","2021-08-01","2021-09-01","2021-10-01"]
                                ,"payFreq":["CustomDate","2021-08-15","2021-09-15","2021-10-15"]
                                })
                
test09 = test01 & lens.name.set("TEST09 - PreClosingDeal&CustomeDate")\
                & lens.status.set(("PreClosing","amortizing"))\
                & lens.pool.modify(lambda x: tz.assoc(x
                                                      , "issuanceStat"
                                                      ,{"IssuanceBalance":1800}))\
                & lens.dates.set({
                                "cutoff": "2021-03-01",
                                "closing": "2021-04-15",
                                "firstPay": "2021-07-26",
                                "payFreq": ["CustomDate","2021-08-15","2021-09-15","2021-10-15"],
                                "poolFreq": ["CustomDate","2021-07-01","2021-08-01","2021-09-01","2021-10-01"],
                                "stated": "2030-01-01",
                                })\
                & lens.pool.modify(lambda x: tz.assoc(x
                                                      , "issuanceStat"
                                                      ,{"IssuanceBalance":1800}))