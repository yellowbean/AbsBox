import sys

if (sys.version_info.major >= 3 and sys.version_info.minor < 10):
    raise ImportError("AbsBox support Python with version 3.10+ only")

from absbox.client import API, Endpoints, EnginePath, PickApiFrom
from absbox.local.util import guess_pool_flow_header, unifyTs, mkTbl
from absbox.local.base import *
from absbox.local.cmp import comp_engines
from absbox.local.china import 信贷ABS, SPV
from absbox.local.generic import Generic
from absbox.deal import mkDeal, mkDealsBy, setDealsBy, prodDealsBy, setAssumpsBy, prodAssumpsBy
from absbox.local.analytics import run_yield_table, flow_by_scenario, runYieldTable
from absbox.validation import *
from absbox.local.chart import viz
from importlib.metadata import version
from absbox.local.cf import readBondsCf,readToCf,readFeesCf,readAccsCf,readPoolsCf,readFlowsByScenarios,readMultiFlowsByScenarios,readFieldsByScenarios
from absbox.local.cf import readInspect

import absbox.examples as examples

__version__ = version("absbox")