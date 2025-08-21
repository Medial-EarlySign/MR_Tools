#!/usr/bin/python

##################################################
# Read a file, find all values belonging to a
# certain signal (may be given by more than one
# name). Apply unit transformation and fix
# resolutions. Plot histograms for manual
# inspection
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

# Fix resolution
def fixResolution(value,res):
	bin = int(value/res + 0.5)
	return bin*res
	
# Special converions
def convert(value,rule):
	if (rule == "Fahrenheit2Celsius"):
		return (value-32)*5.0/9.0
	elif(rule=="HbA1cRule"):
		return(value/10.929+2.15)
	else:
		raise ValueError("Unknown extra unit conversion \'%s\'"%rule)


# Reading - read units and resolution info
def readUnitsAndResolutions(unitsFileName,resFileName, signalInfo,utf8):

	file = open(unitsFileName,"r")
	
	# Units transformation
	for line in file:
		if (line[0:1] == "#"):
			continue
			
		if (utf8):
			line = line.decode('utf-8').encode('utf-8')
		
		fields = str.split(line.rstrip("\r\n"),"\t")
		signal = fields[0]
		unit= fields[1] 
		factor = fields[2]
		
		if (signal not in signalInfo.keys()):
			signalInfo[signal] = {"factors":{}, "conversions":{}}
			
		unit = unit.upper()
		signalInfo[signal]["factors"][unit] = float(factor)
		if (float(factor) == 1 and "original" not in signalInfo[signal].keys()):
			signalInfo[signal]["original"] = unit
		
		# Extra info ...
		if (len(fields)>3):
			extraInfo = fields[3]
			if (extraInfo != "" and extraInfo[0:1] != "#"):
				signalInfo[signal]["conversions"][unit] = extraInfo

	file = open(resFileName,"r")
	
	# Resolutions
	for line in file:
		if (line[0:1] == "#"):
			continue
		
		if (utf8):
			line = line.decode('utf-8').encode('utf-8')
			
		signal,res = str.split(line.rstrip("\r\n"),"\t")
		if (signal not in signalInfo.keys()):
			continue
			
		signalInfo[signal]["resolution"] = float(res)

# Plot histograms
def doPlot(dataPerType,types,graphFileName,plotlyPath):
	
	all_x = []
	all_y = []
	names = []
	for type in types:
		names.append(type)
		vec = throwOutlyers(dataPerType[type])
		
		d = hist(vec)
		xy = []
		for k,v in d.items():
			xy.append([k,v])
		xy = sorted(xy, key=lambda kv: kv[0], reverse = False)
		x = list(map(lambda v : v[0] ,xy))
		y = list(map(lambda v : v[1] ,xy))
		
		fx = []
		fy = []
		for k in range(len(y)):
			if (1 or x[k] > 0):
				fy.append(y[k])
				fx.append(x[k])

		all_x.append(fx)
		fy = normVec(fy)    
		all_y.append(fy)

	createHtmlGraph(all_x, all_y, graphFileName, plotlyPath, 'Values', 'Prob', names)

# Get Moments
def getMoments(vec,moments):
	
	moments["size"] = len(vec)
	clean = sorted(throwOutlyers(vec))
	
	moments["q1"] = clean[int(len(clean)*0.25)]
	moments["q2"] = clean[int(len(clean)*0.50)]
	moments["q3"] = clean[int(len(clean)*0.75)]
	
	var = 0.0
	for v in clean:
		var += (v - moments["q2"])*(v - moments["q2"])/moments["size"]
	moments["var"] = var
	
# Compare data and plot histograms
def compareAndPlot(dataPerType,logFile,graphFileName,plotlyPath):

	# Comparison
	moments = defaultdict(dict) # number, 1/4,1/2,3/4-quantile, approx-var
	for type in dataPerType.keys():
		getMoments(dataPerType[type],moments[type])
		
	types =sorted(moments.keys(),key=lambda x:moments[x]["size"], reverse=True)
	for type in types:
		sdv = sqrt((moments[types[0]]["var"] + moments[type]["var"])/2)
		if sdv == 0:
			eprint("SDV for type", type, " == 0!")
			sdv = 0.00001
		logFile.write("Type %s\t%d\t%.3f\t%.3f\t%.3f\t\t%.3f\t"%(type,moments[type]["size"],moments[type]["q1"],moments[type]["q2"],moments[type]["q3"],sdv))
		for q in ("q1","q2","q3"):
			logFile.write("\t%.3f"%abs((moments[type][q] - moments[types[0]][q])/sdv))
		logFile.write("\n")
		
	# Plot histograms
	doPlot(dataPerType,types,graphFileName,plotlyPath)
	
# Handling units and resolution
def handleData(inFileName,outFileName,logFileName,signalsList,graphFileName,plotlyPath,nTimes,signalInfo,utf8):

	# Prepare signals list
	signalsDict = {signal:1 for signal in str.split(signalsList,",")}
	
	# Open files
	inFile = open(inFileName,"r")
	outFile = open(outFileName,"w")
	logFile = open(logFileName,"w")
	
	# Collect Data
	dataPerType = defaultdict(list)
	missingUnits = defaultdict(int)
	for line in inFile:
		if (utf8):
			line = line.decode('utf-8').encode('utf-8')
		fields = str.split(line.rstrip("\r\n"),"\t")
		signal = fields[1]
		if (signalsList=="" or signal in signalsDict.keys()):
			if (len(fields)==nTimes+5):
				itemId = fields[4+nTimes]
			else:
				itemId=""
			unit = fields[3+nTimes].upper()
			value = float(fields[2+nTimes])
			
			if (unit not in signalInfo[signal]["factors"]):
				missingUnits[unit] += 1
			else:
				# Convert
				if (unit in signalInfo[signal]["conversions"]):
					value = convert(value,signalInfo[signal]["conversions"][unit])
				else:
					value *= signalInfo[signal]["factors"][unit]
				
				if ("resolution" in signalInfo[signal].keys()):
					value = fixResolution(value,signalInfo[signal]["resolution"])
			
				# Print
				fields.pop()
				if (len(fields)==nTimes+4):
					fields.pop()
				fields[-1] = "%f"%value
				outFile.write("%s\n"%"\t".join(fields))
			
				type = signal + "_" + itemId + "_" + unit
				dataPerType[type].append(value)
	
	# Comparison and summary
	for unit in missingUnits.keys():
		logFile.write("Ignored unit %s %d times\n"%(unit,missingUnits[unit]))
	
	compareAndPlot(dataPerType,logFile,graphFileName,plotlyPath) ;

	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 lab/chart files for loading - second stage (units and resolution)")
parser.add_argument("--input",help="input file")
parser.add_argument("--output",help="output file")
parser.add_argument("--log",help="log file")
parser.add_argument("--units",help="units file")
parser.add_argument("--resolution",help="resolution file")
parser.add_argument("--graph",help="graph file")
parser.add_argument("--nTimes",help="# of time columns", default=2)
parser.add_argument("--signals",help="comma separated list of files to consider (take all if not given)",default="")
parser.add_argument("--plotly", help="plotly infra path", default = '\\\\nas3\\Work\\Graph_Infra')
parser.add_argument('--utf8', action='store_true', help = 'read files as utf8')
args = parser.parse_args() 

# Read instructions
signalInfo = {}
readUnitsAndResolutions(args.units,args.resolution,signalInfo,args.utf8)

# Do your stuff
handleData(args.input,args.output,args.log,args.signals,args.graph,args.plotly,int(args.nTimes),signalInfo,args.utf8)

