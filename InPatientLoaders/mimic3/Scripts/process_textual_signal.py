#!/usr/bin/python

##################################################
# Read a file, find all values belonging to a
# certain signal (may be given by more than one
# name), Apply unit transformation and fix 
# resolution, and match histograms  
##################################################

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from graphs import *
from math import sqrt

#Utilities
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	

# Handling units and resolution
def handleData(inFileName,outFileName,logFileName,signalsList,nTimes):

	# Prepare signals list
	signalsDict = {signal:1 for signal in str.split(signalsList,",")}
	
	# Open files
	inFile = open(inFileName,"r")
	outFile = open(outFileName,"w")
	logFile = open(logFileName,"w")
	
	# Collect Data
	counterPerType = defaultdict(int)
	nMissing = 0 
	for line in inFile:
		fields = str.split(line.rstrip("\r\n"),"\t")
		signal = fields[1]
		if (signalsList=="" or signal in signalsDict.keys()):
			name = signal.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
			itemId = fields[4+nTimes]
			unit = fields[3+nTimes]
			value = fields[2+nTimes]
			
			if (value==name+"_"):
				nMissing += 1
			else:
				type = signal + "_" + itemId + "_" + unit + "_" + value
				counterPerType[type] += 1
					
				# Print
				fields.pop()
				fields.pop()
				outFile.write("%s\n"%"\t".join(fields))
			
	# Comparison and summary
	for type in counterPerType.keys():
		logFile.write("Counter\t%s\t%d\n"%(type,counterPerType[type]))
	logFile.write("Also found %d missing entries\n"%(nMissing))
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 lab/chart files for loading - second stage (units and resolution)")
parser.add_argument("--input",help="input file")
parser.add_argument("--output",help="output file")
parser.add_argument("--log",help="log file")
parser.add_argument("--nTimes",help="# of time columns", default=2)
parser.add_argument("--signals",help="comma separated list of files to consider (take all if not given)",default="")
args = parser.parse_args() 

# Do your stuff
handleData(args.input,args.output,args.log,args.signals,int(args.nTimes))

