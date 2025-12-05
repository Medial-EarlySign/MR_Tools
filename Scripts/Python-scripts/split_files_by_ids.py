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

counter = 0
for line in file:
	fields = str.split(line,"\t")
	id = int(fields[0])
	fileId = id%nFiles
	outFiles[fileId].write(line)
	
	if (counter%50000 == 1):
		print(counter,fileId)
	counter = counter + 1

		
	
for file in outFiles:
	file.close()


