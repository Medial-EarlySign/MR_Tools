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
sigs = ['DRUG_ADMINISTERED','MICROBIOLOGY','STAY']
rep.read_all('/home/Repositories/MIMIC/Mimic3/mimic3.repository',[],sigs)

print med.cerr()

antibiotics = {}
with open ("/home/Repositories/MIMIC/Mimic3/dict.input","r") as file:
	for line in file:
		fields = str.split(line.rstrip("\r\n"),"\t")
		if (len(fields)==3 and fields[0] == 'DEF' and fields[2].startswith('DRUG_ADMINISTERED')):
			name,atc,route = str.split(fields[2],"|")
			if (atc[0:3] == 'J01'):
				antibiotics[int(fields[1])] = 1

icu_stays = {}
with open ("/home/Repositories/MIMIC/Mimic3/dict.transfers","r") as file:
	for line in file:
		fields = str.split(line.rstrip("\r\n"),"\t")
		if (len(fields)==3 and fields[0] == 'DEF'):
			if (fields[2].find("WARD")==-1 and fields[2]!="NA" and fields[2]!="carevue" and fields[2]!="metavision"):
				icu_stays[int(fields[1])]=1

print('Collecting Drugs ...')
all_drugs = rep.get_sig("DRUG_ADMINISTERED")
drugs = defaultdict(list)
for i in range(len(all_drugs)):
	if (int(all_drugs['val'][i]) in antibiotics.keys()):
		drugs[all_drugs['pid'][i]].append([all_drugs['date_start'][i],all_drugs['date_end'][i]])
print('Done')				
				
print('Collecting stays ...')
all_stays = rep.get_sig("STAY")
stays = defaultdict(list)
for i in range(len(all_stays)):
	if (int(all_stays['val'][i]) in icu_stays.keys() and int(all_stays['val2'][i]) == 1012):
		stays[all_stays['pid'][i]].append([all_stays['date_start'][i],all_stays['date_end'][i]])
print('Done')

print('Collecting microbiology')
all_mb = rep.get_sig("MICROBIOLOGY")
mb = defaultdict(list)
for i in range(len(all_mb)):
	mb[all_mb['pid'][i]].append(all_mb['date_start'][i])
print('Done')

count = defaultdict(int)
total = 0
for pid in mb.keys():
	if (pid in stays.keys() and len(stays[pid])==1):
		for time in mb[pid]:
			if (time < stays[pid][0][0]):
				count['before'] +=1
			elif (time > stays[pid][0][1]):
				count['after'] += 1
			else:
				count["%04d"%((time - stays[pid][0][0])/60)] += 1
			total += 1

with open("MicroBiologyDeltaHists","w") as outFile:			
	for key in sorted(count.keys()):
		outFile.write("%s\t%d\t%.1f%%\n"%(key,count[key],100.0*count[key]/total))
outFile.write("\n\n")



