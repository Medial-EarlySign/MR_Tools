#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random

readers = mimic3_readers()

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

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
		
	required = ["IdsFile","OutDir","DataDir","LogFile","PoeMainMap","PoeBaseMap"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
			
	defaults = {"DataFile":"Drugs","Suffix":"drugs"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
	return config

def readMap(fileName,map,atcMap):

	with open(fileName,"r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			if (len(fields)==7):	# NO ATC GIVEN
				code = fields.pop()
				map["\t".join(fields)] = code
			else:
				atc = fields.pop()
				code = fields.pop()
				if (code in atcMap.keys() and atc != atcMap[code]):
					raise ValueError("Inconsistent atc code for %s"%code)
				atcMap[code]=atc
				map["\t".join(fields)] = code

# Handle Prescriptions 
def writePrescriptions(dir,inId,outId,mainComb2Code,baseComb2Code,outFile,dictionary,logger,atcMap):
	lines,header = readers.read_lines(dir,"PRESCRIPTIONS",inId)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		type = line[header["DRUG_TYPE"]]
		combFields = ["DRUG","DRUG_NAME_POE","DRUG_NAME_GENERIC","FORMULARY_DRUG_CD","GSN","NDC"]
		combIds = [header[f] for f in combFields]
		
		comb = "\t".join(line[id] for id in combIds)
		comb = comb.upper()
		
		if (type == "MAIN" or type == "ADDITIVE"):
			code = mainComb2Code[comb]
			section = "DRUG_PRESCRIBED"
			prefix = "DRUG"
		elif (type == "BASE"):
			code = baseComb2Code[comb]
			section = "BASE_PRESCRIBED"
			prefix = "BASE"
			
		route = line[header["ROUTE"]]
		if (route == ""):
			route = "NA"
		entry = "%s:%s|%s"%(prefix,code,route)
		
		if (code in atcMap.keys()):
			entry = "%s:%s|%s|%s"%(prefix,code,atcMap[code],route)
		else:
			entry = "%s:%s|%s|%s"%(prefix,code,"NA",route)
		dictionary[section][entry] = 1
		
		dose = line[header["DOSE_VAL_RX"]]
		unit = line[header["DOSE_UNIT_RX"]].upper()
		if (dose == "" or dose.isspace()):
			logger.write("Dose not available for \'%s\'\n"%("\t".join(line)))
			dose = 0

		startDate = line[header["STARTDATE"]]
		endDate = line[header["ENDDATE"]]
		if (startDate == "" and endDate == ""):
			logger.write("Ignoring entry for %d without start AND end date\n"%id)
		else:
			if (startDate == ""):
				startDate = "-1.0"
			elif (endDate == ""):
				endDate = "-1.0"
			outFile.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,section,startDate,endDate,entry,dose,route,unit,line[header["DRUG"]]))

# Write dictionary
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for prescriptions\n")
	dictFile.write("#####################################################################\n")

	index = 1000
	signals = dictionary.keys()
	dictFile.write("SECTION\t%s\n"%",".join(signals))
	for signal in signals:
		for key in dictionary[signal].keys():
			dictFile.write("DEF\t%d\t%s\n"%(index,key))
			index +=1
	
# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for prescriptions\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tDRUG_PRESCRIBED\t%d\t12\tPrescribed Drug. First Channel = Name+Route, Second = amount\t10\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tBASE_PRESCRIBED\t%d\t12\tPrescribed Solutions. First Channel = Name+Route, Second = amount\t10\n"%signalId)
	
def generate_pres_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Read maps
	atcMap = defaultdict(dict)
	mainComb2Code = {}
	readMap(config["PoeMainMap"],mainComb2Code,atcMap)
	
	baseComb2Code = {}
	readMap(config["PoeBaseMap"],baseComb2Code,atcMap)
	
	# Prepare output files
	outFileName = config["OutDir"] + "/" + config["DataFile"]
	outFile = open(outFileName,"w")

	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")

	logFileName = config["LogFile"]
	logger = open(logFileName,"w")
	
	
	# Loop and extract info
	dictionary = defaultdict(dict)
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%250 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		# Prescriptions
		writePrescriptions(config["DataDir"],id,newId,mainComb2Code,baseComb2Code,outFile,dictionary,logger,atcMap)
		
	# Generate Dictionary
	writeDictionary(outDict,dictionary)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 prescriptions file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=85)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_pres_files(config,args.signalId)

