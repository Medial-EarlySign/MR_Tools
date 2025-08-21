#!/usr/bin/python

##################################################
# Unite mixed signals which appears as BG_, LAB_,
# and CHART_
# When contradiction occur - precedence is -
# LAB, BG > CHART
##################################################

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict

#Utilities
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def sort_key(line):
	if (line[1][0:4] == "CHART_"):
		return(line[2],1)
	else:
		return(line[2],0)
	
def handle_single_id(idInfo,outFile,logFile):

	sortedInfo = sorted(idInfo,key=sort_key)
	indices = [0]
	
	for i in range(1,len(sortedInfo)):
		index = len(indices)-1
		remove = 0
		while (index > 0):
			if (sortedInfo[i][2] != sortedInfo[indices[index]][2]):
				break
			else:
				if (sortedInfo[i][-1] == sortedInfo[indices[-1]][-1]):
					logFile.write("Removing-Equal %s (%f) for %s (%f) at %s %s\n"% \
						(sortedInfo[i][1],sortedInfo[i][-1],sortedInfo[indices[index]][1],sortedInfo[indices[index]][-1],sortedInfo[i][0],sortedInfo[i][2]))
					remove = 1
				elif (sortedInfo[i][1] != sortedInfo[indices[-1]][1]):
					logFile.write("Removing-Different %s (%f) with %s (%f) at %s %s\n"% \
						(sortedInfo[i][1],sortedInfo[i][-1],sortedInfo[indices[index]][1],sortedInfo[indices[index]][-1],sortedInfo[i][0],sortedInfo[i][2]))
					remove = 1
				else:
					logFile.write("Keeping-Different %s (%f) with %s (%f) at %s %s\n"% \
						(sortedInfo[i][1],sortedInfo[i][-1],sortedInfo[indices[index]][1],sortedInfo[indices[index]][-1],sortedInfo[i][0],sortedInfo[i][2]))				
				index -= 1
		if (remove == 0):
			indices.append(i)

	id = sortedInfo[0][0]
	name = sortedInfo[0][1].replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
	for index in indices:
		outFile.write("%s\t%s\t%s\t%s\t%f\n"%(id,name,sortedInfo[index][2],sortedInfo[index][3],sortedInfo[index][4]))
	
def handle_mixed_signals(inFileName,outFileName,loggerFileName):

	inFile = open(inFileName,"r")
	outFile = open(outFileName,"w")
	logFile = open(loggerFileName,"w")
	
	idInfo = []
	prevId = -1
	for line in inFile:
		[id,signal,time1,time2,value] = str.split(line.rstrip("\r\n"),"\t")
		if (prevId != -1 and id != prevId):
			handle_single_id(idInfo,outFile,logFile)
			idInfo = []
		idInfo.append((id,signal,time1,time2,float(value)))
		prevId = id

	handle_single_id(idInfo,outFile,logFile)

# ======= MAIN ======
parser = ap.ArgumentParser(description = "handle mixed signals")
parser.add_argument("--input",help="input file")
parser.add_argument("--output",help="output file")
parser.add_argument("--log",help="logger file")

args = parser.parse_args() 

# Do your stuff
handle_mixed_signals(args.input,args.output,args.log)

