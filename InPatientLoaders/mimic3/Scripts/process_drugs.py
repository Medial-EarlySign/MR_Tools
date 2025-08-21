#!/usr/bin/python

##################################################
# Read a file, find all values belonging to a
# certain signal (may be given by more than one
# name), Apply unit transformation.
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

def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False
		
# Reading units info
def readUnits(unitsFileName, signalInfo):

	file = open(unitsFileName,"r")
	
	# Units transformation
	for line in file:
		if (line[0:1] == "#"):
			continue
			
		fields = str.split(line.rstrip("\r\n"),"\t")
		signal = fields[0]
		route = fields[1]
		unit= fields[2] 
		factor = fields[3]
		signalInfo[signal + "\t" + route][unit] = float(factor)


# Handling units and resolution
def handleData(inFileName,outFileName,logFileName,signalInfo):

	# Open files
	inFile = open(inFileName,"r")
	outFile = open(outFileName,"w")
	logFile = open(logFileName,"w")
	
	# in and out
	for line in inFile:
		fields = str.split(line.rstrip("\r\n"),"\t")
		
		entry = fields[4]
		value_s = fields[5]
		unit = fields[7].upper()
		
		matchObj = re.match(r'\S+:(.+)\|\S+\|(.+)',entry, re.M|re.I)
		if (not matchObj):
			raise ValueError("Cannot parse entry %s\n"%entry)
			
		key = (matchObj.group(1) + "\t" + matchObj.group(2)).upper()
		if (unit not in signalInfo[key].keys()):
			logFile.write("Cannot find unit conversion for %s\t%s\n"%(key,unit))
			value = -1.0
		else:
			if (not is_number(value_s)):
				# Try one more thing
				matchObj = re.match(r'(\d+),(\d+)',value_s, re.M|re.I)
				if (matchObj):
					value = float(matchObj.group(1)+matchObj.group(2))
				else :
					logFile.write("Value %s for %s\t%s is not a valid dose\n"%(value_s,key,unit))
					value = -1.0
			else:
				value = float(value_s)*signalInfo[key][unit]
		fields[5] = "%f"%value
		outFile.write("%s\n"%"\t".join([fields[i] for i in range(6)]))

	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 prescriptions files for loading - second stage (units)")
parser.add_argument("--input",help="input file")
parser.add_argument("--output",help="output file")
parser.add_argument("--log",help="log file")
parser.add_argument("--units",help="units file")
args = parser.parse_args() 

# Read instructions
signalInfo = defaultdict(dict)
readUnits(args.units,signalInfo)

# Do your stuff
handleData(args.input,args.output,args.log,signalInfo)

