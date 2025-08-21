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
		
	required = ["IdsFile","OutDir","DataDir","LogFile"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))

	defaults = {"DataFile":"Transfers","Suffix":"transfers"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
			
	return config

# Handle Transfers
def writeTransfersInfo(dir,inId,outId,outFile,logger,dict):
	
	# Transfers
	lines,header = readers.read_lines(dir,"TRANSFERS",inId) 
		
	stays = []
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		event = line[header["EVENTTYPE"]]
		if (event == "discharge"):
			continue
		
		unit = line[header["CURR_CAREUNIT"]]
		if (unit == ""):
			unit = "WARD"
		unit += line[header["CURR_WARDID"]]
		dict[unit] = 1

		inTime = line[header["INTIME"]]
		outTime = line[header["OUTTIME"]]
		if (inTime == "" or outTime == ""):
			logger.write("Cannot find in/out time for transfer-event %s for %d\n"%(event,id))
		else:
			stays.append([inTime,outTime,unit,"NA"])
	dict["NA"]=1
	
	# ICU stays
	lines,header = readers.read_lines(dir,"ICUSTAYS",inId) 
		
	sortedStays = sorted(stays)
	for line in lines:	
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
			
		dbSource = line[header["DBSOURCE"]]
		inTime = line[header["INTIME"]]
		outTime = line[header["OUTTIME"]]
		stayId = line[header["ICUSTAY_ID"]]
		
		# Can we find corresponding stays
		start = end = -1
		for index in range(len(sortedStays)):
			if (sortedStays[index][0] == inTime):
				start = index
			if (sortedStays[index][1] == outTime):
				end = index
				break
		
		if (start != -1 and end != -1):
			for index in range(start,end+1):
				sortedStays[index][3] = dbSource
			dict[dbSource] = 1
		else:
			if (start == -1):
				logger.write("Cannot find transfer information for start of %d/%s\n"%(id,stayId))
			if (end == -1):
				logger.write("Cannot find transfer information for end of %d/%s\n"%(id,stayId))
				
	for stay in sortedStays:
		outFile.write("%d\tSTAY\t%s\t%s\t%s\t%s\n"%(outId,stay[0],stay[1],stay[2],stay[3]))
		
# Write transfers dictionary
def writeDictionary(dictFile,dict):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for transfers/stays\n")
	dictFile.write("#####################################################################\n")
	
	dictFile.write("SECTION\tSTAY\n")
	index = 1000
	for key in dict.keys():
		dictFile.write("DEF\t%d\t%s\n"%(index,key))
		index +=1
	
# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for transfers/stays\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tSTAY\t%d\t12\tStay information\t11\n"%signalId)

			
def generate_transfers_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Prepare output filse
	outFileName = config["OutDir"] + "/" + config["DataFile"]
	outFile = open(outFileName,"w")

	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")
	
	logFileName = config["LogFile"]
	logger = open(logFileName,"w")	
	
	# Loop and extract info
	dict = {}
	for rec in ids:
		(id,newId) = rec
		writeTransfersInfo(config["DataDir"],id,newId,outFile,logger,dict)

	# Generate Dictionary
	writeDictionary(outDict,dict)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 transfers file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=20)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_transfers_files(config,args.signalId)

