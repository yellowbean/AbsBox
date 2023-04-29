import sys,warnings

if (sys.version_info.major >= 3 and sys.version_info.minor < 10):
    raise ImportError("AbsBox support Python with version 3.10+ only")

from absbox.client import API,save
from absbox.local.util import guess_pool_flow_header
from absbox.local.base import *
from absbox.local.china import 信贷ABS,SPV
from absbox.local.cmp import comp_engines
from absbox.local.generic import Generic


from importlib.metadata import version

__version__ = version("absbox")