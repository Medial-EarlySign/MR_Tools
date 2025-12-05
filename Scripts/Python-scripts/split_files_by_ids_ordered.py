#!/usr/bin/env python

import sys

fileName = sys.argv[1]
outFormat = sys.argv[2]

file = open(fileName,"r")

outFiles = []
nFiles = 20
for i in range(nFiles):
	newFileName = outFormat%i
	ifile = open(newFileName,"w")
	outFiles.append(ifile)

ids = {}
for line in file:
	fields = str.split(line,"\t")
	id = int(fields[0])
	ids[id] = 1;
	
file.close()

sortedIds = sorted(ids.keys())
nIds = len(sortedIds)
print("Found %d ids"%nIds) ;
blockSize = nIds/nFiles + 1

cnt = 0
fileIds = {}
for i in range(len(sortedIds)):
	fileIds[sortedIds[i]] = i/blockSize

counter = 0 ;	
file = open(fileName,"r")	
for line in file:
	fields = str.split(line,"\t")
	id = int(fields[0])	
	fileId = fileIds[id]

	outFiles[fileId].write(line)
	
	if (counter%50000 == 1):
		print(counter,fileId)
	counter = counter + 1

for file in outFiles:
	file.close()


