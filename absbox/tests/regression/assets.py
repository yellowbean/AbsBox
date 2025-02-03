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
