from project_convert import *
from convert import *

import os

os.system("rm -rf a")

#pc = ProjectConverter('tests/assembly')

# pc = ProjectConverter(root = 'tests/assembly/straight')

# pc.setOutputType('r')
# pc.setHex(True)

# res = pc.convert()
# print(res)

cnv = AssemblyConverter()
res = cnv.convert("tests/assembly/straight/a.s")
print(res)

print("\n".join(["{}: {}".format(p, len(res[p])) for p in res.keys()]))
print(pc.getFailedConvert())



#TEST CASES
# 1. w/ or w/o filepath
# 2. incorrect filepath raises error