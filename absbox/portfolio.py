from collections import namedtuple
import pandas as pd 
import numpy as np
from client import API


Portfolio = namedtuple('Portfolio', ['positions'])

#def addPosition(p:Portfolio, bnd, size):
#    pass
#
#
#def calcStats(api:API, p:Portfolio, assumps):
#    ps = p.positions
#    result = {}
#    for p in ps:
#        assump = assumps.get(p)
#        pos = getPos(p)
#        r = api.run(p,assumptions=assump,position=pos)
#        result[p] = r
#    
#    return result
#
#
#def hypoBuy(p:Portfolio, assumps, (bnd, size, pAssump)):
#    currentStats = calcStats(api, p, assumps)
#
#    newAssump = assumps | pAssump
#    newP = p.add((bnd,size))
#    
#    futureStats = calcStats(api, p, assumps)
#    
#
#
#def hypoSell(p:Portfolio, bnd, size):
#    pass