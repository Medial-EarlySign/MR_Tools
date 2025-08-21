#!/usr/bin/python

##################################################
# Read a file, find all values belonging to a
# certain signal (may be given by more than one
# name)
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
		
# Amount units
def handle_unit(unit):

	unit = unit.replace("CC","ML").replace("MEQ.","MEQ").replace("MG/MG X ","")
	if (unit == "ML" or unit == "ML/ML X ML"):
		return 1,"ML"
	elif (unit == "DOSE"):
		return -1,"MG"
	elif (unit == "GM" or unit == "GRAMS"):
		return 1000,"MG"
	elif (unit == "MCG"):
		return 0.001,"MG"
	elif (unit == "MG" or unit == "MG/ML X ML" or unit == "MG/MEQ X MEQ"):
		return 1,"MG"
	elif (unit == "U" or unit == "UNITS" or unit == "U/ML X ML"):
		return 1,"UNIT"	
	elif (unit == "MMOL" or unit == "CAL" or unit == "MEQ"):
		return 1,unit
	elif (unit == "TSP"):
		return 5000,"MG"
	else:
		raise ValueError("Cannot parse unit %s"%unit)

# Rate units
def handle_rate_unit(unit):

	unit = unit.replace("CC","ML").replace("MG/MG X ","").replace("MEQ.","MEQ").replace("ML/ML X ML","ML").replace("MG/MEQ X MEQ","MG").replace("MG/ML X ML","MG").replace("/","")
	
	# Target unit = (UNIT/MG/ML/MEQ) (per Kg) per Hour
	factor = 1.0 
	if (unit[-3:] == "MIN"):
		factor = 60.0
		unit = unit[:-3]
	elif (unit[-4:] == "HOUR"):
		factor = 1.0
		unit = unit[:-4]
	elif (unit[-2:] == "HR"):
		factor = 1.0
		unit = unit[:-2]
	else:
		raise ValueError("Cannot parse unit %s"%unit)
	
	perWeight = 0
	if (unit[-2:] == "KG"):
		perWeight = 1
		unit = unit[:-2]
		
	if (unit == "MG"):
		base = "MG"
	elif (unit == "G" or unit == "GR" or unit == "GM" or unit == "GRAMS"):
		base = "MG"
		factor *= 1000
	elif (unit == "MCG"):
		base = "MG"
		factor /= 1000
	elif (unit == "ML"):
		base = "ML"
	elif (unit == "U" or unit == "UNITS"):
		base = "UNIT"
	elif (unit == "MEQ" or unit == "MEQ."):
		base = "MEQ"
	else:
		raise ValueError("Cannot parse unit %s"%unit)
		
	if (perWeight):
		targetUnit = base + "/KG/HR"
	else:
		targetUnit = base + "/HR"
	
	return factor,targetUnit
	
# Handling units
def handleData(inFileName,outFileName,logFileName):

	# Open files
	inFile = open(inFileName,"r")
	outFile = open(outFileName,"w")
	logFile = open(logFileName,"w")
	
	# in and out
	unitCounters = defaultdict(int)
	failsCounters = defaultdict(int)
	
	valueIdx = -2
	
	for line in inFile:
		fields = str.split(line.rstrip("\r\n"),"\t")
		itemId = fields.pop()
		if (fields[1] == "DRUG_ADMINISTERED"):
			key = fields.pop()
		else:
			key = "NA"
		unit = fields.pop().upper()
		fields.append(key)
		
		if (fields[1] == "FLUID_INTAKE"):
			if (unit != "ML" and unit != "CC"):
				logFile.write("Unknown unit for fluid intake for %s : %s\n"%(itemId,unit))
			else:
				outFile.write("%s\n"%"\t".join(fields))
				
		elif (fields[1] == "DRUG_ADMINISTERED_RATE"):
			if (float(fields[valueIdx]) != -1):
				factor,target = handle_rate_unit(unit)
				fields[valueIdx] = "%f"%(float(fields[valueIdx])*factor)
				unitCounters[fields[1] + "\t" + fields[3] + "\t" + target] += 1
			outFile.write("%s\n"%"\t".join(fields))
		elif (fields[1] == "DRUG_ADMINISTERED"):
			if (float(fields[valueIdx]) != -1):
				factor,target = handle_unit(unit)
				if (factor == -1):
					fields[valueIdx] = "-1.0"
					failsCounters[fields[4] + " : " + unit + "\t" + target] += 1
				else:
					fields[valueIdx] = "%f"%(float(fields[valueIdx])*factor)
				unitCounters[fields[1] + "\t" + fields[4] + "\t" + target] += 1
			outFile.write("%s\n"%"\t".join(fields))
		elif (fields[1] == "NUTRITION"):
			if (float(fields[valueIdx]) != -1):
				factor,target = handle_unit(unit)
				fields[valueIdx] = "%f"%(float(fields[valueIdx])*factor)
				unitCounters[fields[1] + "\t" + fields[4] + "\t" + target] += 1
			outFile.write("%s\n"%"\t".join(fields))
	
	for key in failsCounters.keys():
		logFile.write("Failed transforming\t%s\t%d\n"%(key,failsCounters[key]))
	for key in unitCounters.keys():
		logFile.write("Units counter\t%s\t%d\n"%(key,unitCounters[key]))
		
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 input files for loading - second stage (units)")
parser.add_argument("--input",help="input file")
parser.add_argument("--output",help="output file")
parser.add_argument("--log",help="log file")
args = parser.parse_args() 

# Do your stuff
handleData(args.input,args.output,args.log)

