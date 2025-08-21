#!/usr/bin/python

import sys
import numpy as np
import pandas as pd
import os
root = os.environ['MR_ROOT']

sys.path.insert(0,root+'/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')

import medpython as med
from collections import defaultdict

rep = med.PidRepository()
sigs = ['Hemoglobin','Albumin','Bilirubin','Creatinine','INR_PT_','PH']
rep.read_all('/home/Repositories/MIMIC/Mimic3/mimic3.repository',[],sigs)

print med.cerr()

data = defaultdict(list)
for sig in sigs:
	sig_data = rep.get_sig(sig)
	print("Collecting %s"%sig)
	for i in range(len(sig_data)):
		data[sig_data['pid'][i]].append({'sig':sig,'time':sig_data['date_start'][i]})
	print("Done Collecting")

deltaHist = {sig: defaultdict(int) for sig in sigs}
for pid in data.keys():
	pidData_s= sorted(data[pid],key=lambda x:x['time'])
	lastHgbTime = -1
	for i in range(len(pidData_s)):
		if (pidData_s[i]['sig'] != 'Hemoglobin'):
			sig = pidData_s[i]['sig']
			minDist = -121
			j = i-1
			while (j>=0):
				delta = pidData_s[i]['time'] - pidData_s[j]['time']
				if (delta > 120):
					break
				if (pidData_s[j]['sig'] == 'Hemoglobin'):
					minDist = -delta
				j -=1
			j=i+1
			while (j<len(pidData_s)):
				delta = pidData_s[j]['time'] - pidData_s[i]['time']
				if (delta > 120 or delta > -minDist):
					break
				if (pidData_s[j]['sig'] == 'Hemoglobin'):
					minDist = delta
				j+=1
			if (minDist != -121):
				deltaHist[sig][minDist] += 1
			
			
with open("LabDeltaHists","w") as outFile:
	for sig in sigs:
		if (sig != 'Hemoglobin'):
			sum = 0
			for delta in (sorted(deltaHist[sig].keys())):
				sum += deltaHist[sig][delta]
			for delta in (sorted(deltaHist[sig].keys())):
				outFile.write("%s HIST\t%d\t%d\t%.2f%%\n"%(sig,delta,deltaHist[sig][delta],100.0*deltaHist[sig][delta]/sum))
		outFile.write('\n')

