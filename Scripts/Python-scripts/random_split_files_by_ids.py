#!/usr/bin/env python

import sys
import random

fileName = sys.argv[1]
outFormat = sys.argv[2]
nFiles = int(sys.argv[3])

file = open(fileName,"r")

outFiles = []
for i in range(nFiles):
	newFileName = outFormat%(i+1)
	ifile = open(newFileName,"w")
	outFiles.append(ifile)

counter = 0
for line in file:
	fields = str.split(line,"\t")
	id = int(fields[0])
	fileId = random.randint(0,nFiles-1)
	outFiles[fileId].write(line)
	
	if (counter%50000 == 1):
		print(counter,fileId)
	counter = counter + 1

		
	
for file in outFiles:
	file.close()


