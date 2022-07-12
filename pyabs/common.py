from enum import Enum
import pandas as pd
import numpy as np


class Period(Enum):
    Year = 1
    Quarter = 4
    Month = 12
    Week = 52


def read_bond_flow()->pd.DataFrame:
    pass

def read_fee_flow()->pd.DataFrame:
    pass

def read_account_flow()->pd.DataFrame:
    pass

def read_pool_flow()->pd.DataFrame:
    pass




