import pandas as pd
from lenses import lens
import toolz as tz
import pytest
import re, math

from absbox.tests.regression.assets import *


m = ["Mortgage"
        ,{"originBalance": 12000.0
            ,"originRate": ["fix",0.045]
            ,"originTerm": 80
            ,"freq": "Monthly"
            ,"type": "Level"
            ,"originDate": "2021-02-01"}
        ,{"currentBalance": 10000.0
            ,"currentRate": 0.075
            ,"remainTerm": 80
            ,"status": "Current"}]

m1 = ["Mortgage"
        ,{"originBalance": 12000.0
            ,"originRate": ["fix",0.045]
            ,"originTerm": 18
            ,"freq": "Monthly"
            ,"type": "Level"
            ,"originDate": "2021-02-01"}
        ,{"currentBalance": 10000.0
            ,"currentRate": 0.075
            ,"remainTerm": 12
            ,"status": "Current"}]

l1 = ["Lease"
        ,{"rental":("byDay", 12.0, ["DayOfMonth",15])
        ,"originTerm": 12
        ,"originDate": "2022-01-05"}
        ,{"status":"Current" ,"remainTerm":6 ,"currentBalance":150}]