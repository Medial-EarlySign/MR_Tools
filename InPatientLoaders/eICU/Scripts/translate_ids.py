#!/usr/bin/python
import sys
from collections import defaultdict
import argparse as ap
import re
import numpy as np

parser = ap.ArgumentParser(description = "translate ids in eICU files")
parser.add_argument("--inFile",help="input file")
parser.add_argument("--outFile",help="output file")
parser.add_argument("--idKey",help="name of id identifier",default="patientunitstayid")
parser.add_argument("--map",help="mapping file")

args = parser.parse_args() 
inFile = args.inFile
outFile = args.outFile
idKey = args.idKey
mapFile = args.map

#Read Map
file = open(mapFile,"r")
map = {}
for line in file:
	fields = str.split(line.rstrip("\r\n"),"\t")
	map[fields[0]] = fields[1]

# Translate	
print("Working on %s"%inFile)

file = open(inFile,"r")
out_file = open(outFile,"w")
idCol = -1
header = 1

for line in iter(file.readline, ''):
	fields = str.split(line.rstrip("\r\n"),",")
	if (header == 1):
		for i in range(len(fields)):
			if (fields[i].find(idKey)>=0):
				idCol = i
				break
		if (idCol != -1):
			print("Identified column of %s at %d (%s)"%(idKey,idCol,fields[idCol]))
		header = 0
	else:
		if (idCol != -1):
			fields[idCol] = map[fields[idCol]]
	outLine = ",".join(fields)
	out_file.write("%s\n"%outLine)

