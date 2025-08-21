#!/usr/bin/python
import sys
from collections import defaultdict
import argparse as ap
import re
import numpy as np

parser = ap.ArgumentParser(description = "Create an indexed file from aMimic-3 data file")
parser.add_argument("--inFile",help="input file")
parser.add_argument("--outFile",help="output file")
parser.add_argument("--idKey",help="name of id identifier",default="SUBJECT_ID")
parser.add_argument("--maxId",help="maximal allowed id",default=100000)

args = parser.parse_args() 
inFile = args.inFile
outFile = args.outFile
idKey = args.idKey
maxId = int(args.maxId)

print("Working on %s"%inFile)

file = open(inFile,"r")
pos = np.full(maxId,-1)
done = {}

idCol = -1
prevId = -1
position = file.tell()
nIds = 0

for line in iter(file.readline, ''):
	fields = str.split(line.rstrip("\r\n"),",")
	if (idCol == -1):
		for i in range(len(fields)):
			if (fields[i].find(idKey)>=0):
				idCol = i
				break
		print("Identified column of SUBJECT_ID at %d (%s)"%(idCol,fields[idCol]))
	else:
		if (fields[idCol] == idKey):
			continue
			
		id = int(fields[idCol])
		if (id > maxId):
			raise ValueError("ID %d is too large (max=%d)"%(id,maxId))

		if (id != prevId):
			if (id in done.keys()):
				raise ValueError("Messed up file for %d. Quitting"%id)

			pos[id] = position
			done[id] = 1
			nIds += 1
		prevId = id ;

	position = file.tell()

print("DONE Reading %d ids in [0,%d]"%(nIds,maxId))
np.save(outFile,pos)
