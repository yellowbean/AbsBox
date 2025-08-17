import pandas as pd
from lenses import lens
import toolz as tz

from absbox.tests.regression.assets import *


myPool = {'assets':[ m, m1 ],
         'cutoffDate':"2022-03-01"}