#!/usr/bin/python

##################################################
# Generate signal-specifc files:
# id	SignalName	Time1	Time2	Value	Unit
# Where SignalName keeps the LAB_/BG_/CHART_ prefix,
# No Units conversion or resolution fix is performed
# And no uniting of mixed signals (e.g. BiCarbonate,
# which appears as BG_, LAB_, and CHART_
# -- All this is kept for the next stages
##################################################

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random

readers = mimic3_readers()

#Utilities
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False	

# Reading - config file	
def read_config_file(name):

	config = {}
	with open(name,"r") as file:
		for line in file:
			line = line.rstrip("\r\n")
			if (line != '' and line[:1] != "#"):
				fields = str.split(line,"\t")
				if (len(fields) != 2):
					 raise ValueError("Cannot parse line \'%s\' in config file \'%s\'\n"%(line,name))
				else:
					config[fields[0]] = fields[1]
		
	required = ["IdsFile","OutDir","DataDir","LogFile","LabInstructions","LabTextValues","ChartInstructions","ChartTextValues"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
			
	defaults = {"Suffix":"LabAndVitalSigns"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
			
	return config

# Reading - instructions file
def readInstructions(fileName, instructions):

	file = open(fileName,"r")
	
	counter=0
	for line in file:
		fields = str.split(line.rstrip("\r\n"),"\t")
		code = int(fields[0])
		
		instructions[code] = {"name" : fields[3], "type" : fields[2]}

		if (instructions[code]["type"] != "VALUE" and instructions[code]["type"] != "TEXT"):
			raise ValueError("Unknown type \'%s\' for code %d in \'%s\'\n"%(code,instructions[code]["type"],fileName))
		
		counter += 1
		
	print("Read instructions for %d files from %s"%(counter,fileName))
	
# Reading - non numeric values translations
def readNonNumericValues(fileName, instructions, nonNumericValues):
	
	# Some common non-numeric values
	for signal in instructions.keys():
		nonNumericValues[instructions[signal]["name"]] = {}
		if (instructions[signal]["type"] == "VALUE"):
			nonNumericValues[instructions[signal]["name"]]["none"] = 0
			nonNumericValues[instructions[signal]["name"]]["neg"] = 0

	file = open(fileName,"r")
	
	for line in file:
		fields = str.split(line.rstrip("\r\n"),"\t")
		if (fields[0] in nonNumericValues.keys()):
			nonNumericValues[fields[0]][fields[1].lower()] = float(fields[2])

# Handle Lab 
def getLabInfo(dir,inId,info,instructions,nonNumericValues,signalInfo,logger):
	
	lines,header = readers.read_lines(dir,"LABEVENTS",inId) 
		
	done = {}
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = int(line[header["ITEMID"]])
		if (itemId not in instructions.keys()):
			continue
		
		time = line[header["CHARTTIME"]]
		
		# no two-values lab tests ...
		signalName = instructions[itemId]["name"] 
		origName = signalName.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
		if (instructions[itemId]["type"] == "TEXT"):
			nonNumericValue = line[header["VALUE"]].replace('\"','') ;
			if (nonNumericValue.isspace()):
				logger.write("Cannot find value for %s at %d at %s"%(signalName,id,time))
				continue
			else:
				nonNumericValue = origName + "_" + nonNumericValue.lower()
				signalInfo[signalName]["values"][nonNumericValue]=1
				unit = line[header["VALUEUOM"]].upper()
				info.append([signalName,time,-1,nonNumericValue,unit,itemId])
		else:
			value = line[header["VALUENUM"]] ;
			if (value == ""):
				nonNumericValue = line[header["VALUE"]].replace('\"','').lower() ;
				if (nonNumericValue.isspace()):
					logger.write("Cannot find value for %s at %d at %s\n"%(signalName,id,time))
					continue
				elif (nonNumericValue not in nonNumericValues[signalName]):
					logger.write("Cannot find non-numeric-value %s for %s at %d at %s\n"%(nonNumericValue,signalName,id,time))
					continue
				else:
					value = nonNumericValues[signalName][nonNumericValue]

			unit = line[header["VALUEUOM"]].upper()
			info.append([signalName,time,-1,value,unit,itemId])

# Handle Chart 
def getChartInfo(dir,inId,info,instructions,nonNumericValues,signalInfo,logger):
	
	lines,header = readers.read_lines(dir,"CHARTEVENTS",inId) 
		
	done = {}
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = int(line[header["ITEMID"]])
		if (itemId not in instructions.keys()):
			continue
		
		time = line[header["CHARTTIME"]]
		signalName = instructions[itemId]["name"] 
		origName = signalName.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
		if (instructions[itemId]["type"] == "TEXT"):
			nonNumericValue = line[header["VALUE"]].replace('\"','') ;
			if (nonNumericValue.isspace()):
				raise ValueError("Cannot find value for %s at %d at %s"%(signalName,id,time))
			else:
				nonNumericValue = origName + ":" + nonNumericValue.lower().replace(" ","_")
				signalInfo[signalName]["values"][nonNumericValue]=1
				unit = line[header["VALUEUOM"]].upper()
				info.append([signalName,time,-1,nonNumericValue,unit,itemId])
		else:
			value = line[header["VALUENUM"]] ;
			if (value == ""):
				nonNumericValue = line[header["VALUE"]].replace('\"','').lower() ;
				if (nonNumericValue=="" or nonNumericValue.isspace()):
					logger.write("Cannot find value for %s at %d at %s\n"%(signalName,id,time))
					continue
				if (signalName == "CHART_Total_Fluids"):
				# SPECIAL CARE OF TOTAL_FLUIDS
					matchObj = re.match(r'(min|max)\s*\.*\s*(\d+)',nonNumericValue, re.M|re.I)
					if (matchObj):
						unit = line[header["VALUEUOM"]].upper()
						info.append([signalName,time,time,float(matchObj.group(2)),unit,itemId])
					else:
						matchObj = re.match(r'(\d+)\s*\.*\s*(min|max)',nonNumericValue, re.M|re.I)
						if (matchObj):
							unit = line[header["VALUEUOM"]].upper()
							info.append([signalName,time,time,float(matchObj.group(1)),unit,itemId])
						else:
							logger.write("Cannot parse \'%s\' for %s for %s at %s\n"%(nonNumericValue,signalName,id,time))
				elif (signalName == "CHART_I_E_Ratio"): 
				# SPECIAL CARE OF I:E Ratio Data
					m = re.search('^(\S+?)(:|;|..)(\S+)$', nonNumericValue)
					if (m != None and is_number(m.group(1)) and is_number(m.group(3)) and float(m.group(3)) != 0):
						ratio = float(m.group(1))/float(m.group(3))
						unit = line[header["VALUEUOM"]].upper()
						info.append([signalName,time,time,ratio,unit,itemId])
					else:
						logger.write("Cannot parse \'%s\' for %s for %s at %s\n"%(nonNumericValue,signalName,id,time))
						continue
				elif (signalName == "CHART_BirthTime"):
					matchObj = re.match(r'(\d\d):?(\d\d)',nonNumericValue, re.M|re.I)
					if (matchObj):
						info.append([signalName,time,time,int(matchObj.group(1))*60+int(matchObj.group(2)),"minutes",itemId])
					else:
						logger.write("Cannot parse \'%s\' for %s for %s at %s\n"%(nonNumericValue,signalName,id,time))
				# SPECIAL CARE OF BirthTime
				elif (nonNumericValue in nonNumericValues[signalName]):
					value = nonNumericValues[signalName][nonNumericValue]
					unit = line[header["VALUEUOM"]].upper()
					info.append([signalName,time,time,value,unit,itemId])
				else:
					# Try to parse as Value[\s*]Unit
					matchObj = re.match(r'(\d+\.?\d*)\s*(\S+)',nonNumericValue, re.M|re.I)
					if (matchObj):
						logger.write("Parsed %s as %s %s for %s at %d at %s\n"%(nonNumericValue,matchObj.group(1),matchObj.group(2),signalName,id,time))
						info.append([signalName,time,time,float(matchObj.group(1)),matchObj.group(2),itemId])
					else:
						logger.write("Cannot find non-numeric-value %s for %s at %d at %s\n"%(nonNumericValue,signalName,id,time))
						continue

			elif (signalName == "CHART_I_E_Ratio"): 
				# SPECIAL CARE OF I:E Ratio Data
				unit = line[header["VALUEUOM"]].upper()
				if (float(value) == 0):
					logger.write("Cannot handle 0 for I:E Ratio at %d at %s\n"%(id,time))
				else:
					info.append([signalName,time,time,1.0/float(value),unit,itemId])
			else:
				unit = line[header["VALUEUOM"]].upper()
				info.append([signalName,time,time,value,unit,itemId])

# Write output files
def writeLabAndVitalSigns(id,info,fileNames,signalFiles,counters):
	for rec in info:
		[signalName,time1,time2,s_value,unit,itemId] = rec
		signalFiles[fileNames[signalName]].write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(id,signalName,time1,time2,s_value,unit,itemId))
		counters[fileNames[signalName]] += 1

# Write dictionary
def writeDictionary(dictFile,signalInfo):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for Labs and Vital Signs\n")
	dictFile.write("#####################################################################\n")
	
	dictionary = {}
	for signal in signalInfo.keys():
		if (len(signalInfo[signal]["values"].keys())>0):
			signalName = signal.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
			dictionary[signalName] = signalInfo[signal]["values"].keys()
	
	index = 1000
	signals = dictionary.keys()
	dictFile.write("SECTION\t%s\n"%",".join(signals))
	for signal in dictionary.keys():
		for value in dictionary[signal]:
			fixedValue = value.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
			dictFile.write("DEF\t%d\t%s\n"%(index,fixedValue))
			index +=1
		
# Write Signals File
def writeSignalsFile(signalsFile,counters,signalInfo,logger,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for lab and vital signs\n")
	signalsFile.write("#####################################################################\n")
	
	textual = {}
	for signal in signalInfo.keys():
		if (len(signalInfo[signal]["values"].keys())>0):
			signalName = signal.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
			if (len(signalInfo[signal]["values"].keys())> 0):
				textual[signalName] = 1	
	
	for signal in counters.keys():
		if (counters[signal] == 0):
			logger.write("Found 0 values for %s\n"%signal)
		else:
			# Check if textual
			if (signal in textual.keys()):
				type = 1
			else:
				type = 0
			signalsFile.write("SIGNAL\t%s\t%d\t3\t\t%d\n"%(signal,signalId,type))
			signalId += 1

def generate_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Read Files for Labs
	labInstructions = {}
	labNonNumericValues = {}
	signalInfo = {}
	readInstructions(config["LabInstructions"], labInstructions) 
	readNonNumericValues(config["LabTextValues"],labInstructions,labNonNumericValues) ;
	
	for signal in labInstructions.keys():
		signalInfo[labInstructions[signal]["name"]] = {"values":{}}
		
	# Read Files for Chart
	chartInstructions = {}
	chartNonNumericValues = {}	
	readInstructions(config["ChartInstructions"], chartInstructions) 
	readNonNumericValues(config["ChartTextValues"],chartInstructions,chartNonNumericValues) ;
	
	for signal in chartInstructions.keys():
		signalInfo[chartInstructions[signal]["name"]] = {"values":{}}

	# Prepare output files
	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	logFileName = config["LogFile"]
	logger = open(logFileName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")	
	
	fileNames = {}
	counters = {}
	for signal in signalInfo.keys():
		signalName = signal.replace("BG_","",1).replace("LAB_","",1).replace("CHART_","",1)
		fileNames[signal] = signalName
		counters[signalName] = 0
		
	signalFiles = {}
	for name in fileNames.values():
		signalFiles[name] = open(config["OutDir"] + "/" + name,"w")

	# Loop and extract info	
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%20 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))

		info = []
		# Lab
		getLabInfo(config["DataDir"],id,info,labInstructions,labNonNumericValues,signalInfo,logger)  ;

		# Chart
		getChartInfo(config["DataDir"],id,info,chartInstructions,chartNonNumericValues,signalInfo,logger) ;

		# write 
		writeLabAndVitalSigns(newId,info,fileNames,signalFiles,counters)

		
	# Generate Dictionary
	writeDictionary(outDict,signalInfo)
	
	# Write Signals
	writeSignalsFile(signalsFile,counters,signalInfo,logger,signalId)
	

# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 lab/chart files for loading - first stage (collections)")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=100)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_files(config,args.signalId)

