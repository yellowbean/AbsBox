from absbox import Generic
import toolz as tz
from lenses import lens

def insert_functional(lst, index, element):
    return lst[:index] + [element] + lst[index:]


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
                "startDate": "2021-04-15",
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
                "startDate": "2021-04-15",
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
                
                     
accruedDeal = test01 & lens.name.set("TEST10 - AccruedDeal")\
                     & lens.waterfall['default'][0][0].set('payInt')\
                     & lens.dates.modify(lambda x : ("accrued", x) )

test01Fee = test01 & lens.name.set("TEST11 - With Fix Fee")\
                   & lens.fees.modify(lambda x: x + (("issuance_fee"
                                                      ,{"type":{"fixFee":400}
                                                       ,"feeStart":"2021-04-15"})
                                                     ,))\
                   & lens.waterfall['default'].modify(lambda xs: [["calcAndPayFee","acc01",["issuance_fee"]]]+xs)

test02Fee = test01 & lens.name.set("TEST12 - With Recur Fee")\
                   & lens.fees.modify(lambda x: x + (("test_fee"
                                                        ,{"type":("recurFee","QuarterEnd",20)
                                                        ,"feeStart":"2021-04-15"})
                                                        ,))\
                   & lens.waterfall['default'].modify(lambda xs: [["calcAndPayFee","acc01",["test_fee"]]]+xs)

test03Fee = test02Fee & lens.name.set("TEST13 - With pct fee")\
                    & lens.fees.modify(lambda x: x + (("test_fee"
                                                            ,{"type":("pctFee",("bondBalance","A1"),0.01)
                                                            ,"feeStart":"2021-04-15"})
                                                            ,))

test04Fee = test02Fee & lens.name.set("TEST14 - With annual pct fee")\
                    & lens.fees.modify(lambda x: x + (("test_fee"
                                                            ,{"type":("annualPctFee",("poolBalance","A1"),0.02)
                                                            ,"feeStart":"2021-04-15"})
                                                            ,))
                    


test05Fee = test02Fee & lens.name.set("TEST15 - With custom fee")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("customFee",[["2021-08-01",100]
                                                              ,["2021-12-20",50]])
                                        ,"feeStart":"2021-04-15"})
                                        ,))

test06Fee = test02Fee & lens.name.set("TEST16 - flow by bond period")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("flowByBondPeriod",[ [1,50],[2,80],[3,85] ])
                                        ,"feeStart":"2021-07-26"})
                                        ,))

test07Fee = test02Fee & lens.name.set("TEST17 - With count type fee")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("numFee",["DayOfMonth",20],("activeBondNum",), 8)
                                        ,"feeStart":"2021-07-26"})
                                        ,))


test08Fee = test02Fee & lens.name.set("TEST18 - With target fee")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("targetBalanceFee"
                                                  , ("*"
                                                     , ("cumPoolCollection", None, "Interest")
                                                     , 0.03)
                                                  , ("feeTxnAmt",None,"test_fee"))
                                        ,"feeStart":"2021-04-15"})
                                        ,))\
                      & lens.waterfall['default'][0].set(["calcAndPayFee","acc01",["test_fee"]])


test09Fee = test02Fee & lens.name.set("TEST19 - With pool period fee")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("byPeriod",15)
                                        ,"feeStart":"2021-04-15"})
                                        ,))
                      
test10Fee = test02Fee & lens.name.set("TEST20 - With custom fee")\
                      & lens.fees.set((("test_fee"
                                        ,{"type":("byTable"
                                                    ,"MonthEnd"
                                                    ,("*",("poolBalance",),0.02)
                                                    ,[(0,5),(15,10),(30,15)]
                                                 ),
                                          "feeStart":"2021-04-15"
                                          })
                                        ,))\
                      & lens.waterfall['default'][0].set(["payFee","acc01",["test_fee"]])
                      

test11Fee = test01 & lens.name.set("TEST21 - With two fees")\
                   & lens.fees.modify(lambda x: x + (("fee1",{"type":{"fixFee":400},"feeStart":"2021-04-15"})
                                                 ,("fee2",{"type":{"fixFee":400},"feeStart":"2021-04-15"})))\
                   & lens.waterfall['default'].modify(lambda xs: [["calcFee","fee1","fee2"],["payFeeBySeq","acc01",["fee1","fee2"]]]+xs)


test2Bonds = Generic(
    "TEST01- PreClosing-Two Bonds",
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
                "balance": 400,
                "rate": 0.07,
                "originBalance": 400,
                "originRate": 0.07,
                "startDate": "2021-04-15",
                "rateType": {"Fixed": 0.07},
                "bondType": {"Sequential": None},
            },
        ),
        (
            "A2",
            {
                "balance": 600,
                "rate": 0.08,
                "originBalance": 600,
                "originRate": 0.08,
                "startDate": "2021-04-15",
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
                "startDate": "2021-04-15",
                "rateType": {"Fixed": 0.00},
                "bondType": {"Equity": None},
            },
        ),
    ),
    (("issuance_fee"
        ,{"type":{"fixFee":10}
        ,"feeStart":"2021-04-15"})
     ,),
    {
        "default": [
            ["payFee", "acc01", ["issuance_fee"]],
            ["accrueAndPayInt", "acc01", ["A1","A2"]],
            ["payPrin", "acc01", ["A1","A2"]],
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

test2BondsIntBySeq = test2Bonds & lens.name.set("TEST01- PreClosing-Two Bonds")\
                                & lens.fees[0][1]['type']['fixFee'].set(305)\
                                & lens.waterfall['default'][1][0].set("accrueAndPayIntBySeq")
                                
                                
threeAccounts = test01 & lens.name.set("TEST03- PreClosing- Three Accounts")\
                    & lens.accounts.modify(lambda x: x+(('acc02', {'balance': 50}),('acc03', {'balance': 30})))\
                    & lens.waterfall['default'].modify(lambda xs: insert_functional(xs, 0, ["transferM"
                                                                                            ,[("acc02",{"formula": ("const",10)})
                                                                                                ,("acc03",{"formula": ("const",10)})]
                                                                                            ,"acc01"]) )