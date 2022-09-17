import sys,warnings

if (sys.version_info.major >= 3 and sys.version_info.minor < 10):
    raise ImportError("AbsBox support Python with version 3.10+ only")

from absbox.client import API,save,init_jupyter
from absbox.local.china import 信贷ABS
from absbox.local.generic import Generic


