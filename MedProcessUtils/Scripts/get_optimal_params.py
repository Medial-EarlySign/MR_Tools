#!/usr/bin/python

# Analyze results of Optimizer run and get optimal parameters
import numpy as np
import csv
import sys
import collections
import pandas as pd

if (len(sys.argv) != 2):
	raise ValueError("file name required\n")
	
resFile = sys.argv[1]
res = pd.read_csv(resFile,sep='\t')
cols = list(res.columns)
means = [name for name in cols if (name.endswith('_Mean'))]

res['idx'] = 0
for name in means:
	res = res.sort_values(name,ascending=False)
	#res[name + '_idx']  = range(res.shape[0])
	res.idx += range(res.shape[0])

res = res.sort_values('idx',ascending=True)

splits = [idx for idx in range(len(cols)) if (cols[idx].endswith('_Split0'))]

params = []

for idx in range(1,splits[0]):
	params.append("%s=%s"%(cols[idx],res.iloc[0,idx]))
print(";".join(params))




