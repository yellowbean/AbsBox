import sys
from importlib.metadata import version

if (sys.version_info.major >= 3 and sys.version_info.minor < 10):
    raise ImportError("AbsBox support Python with version 3.10+ only")

from .client import API, Endpoints, EnginePath, PickApiFrom
from .library import LIBRARY, LibraryEndpoints, LibraryPath
from .local.util import *
from .local.base import *
from .local.cmp import compResult,compDf
from .local.china import 信贷ABS, SPV
from .local.generic import Generic
from .deal import mkDeal, mkDealsBy, setDealsBy, prodDealsBy, setAssumpsBy, prodAssumpsBy
from .local.analytics import run_yield_table, flow_by_scenario, runYieldTable
from .validation import *
from .local.chart import viz
from .local.cf import readBondsCf,readToCf,readFeesCf,readAccsCf,readPoolsCf,readFlowsByScenarios,readMultiFlowsByScenarios,readFieldsByScenarios
from .local.cf import readInspect, readLedgers, readTriggers
from .local.cf import BondCfHeader
from .local.interface import readAeson 
from .report import toHtml,OutputType,toExcel

from . import examples

__version__ = version("absbox")
