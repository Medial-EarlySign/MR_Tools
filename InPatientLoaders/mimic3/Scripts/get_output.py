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

# Reading - Config File
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
		
	required = ["IdsFile","OutDir","DataDir","LogFile","OutputInstructions"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
			
	defaults = {"DataFile":"Output","Suffix":"output"}
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
		code = fields[0]
		
		instructions[code] = {"name" : fields[3], "type" : fields[2]}

		if (instructions[code]["type"] != "VALUE"):
			raise ValueError("Unknown type \'%s\' for code %d in \'%s\'\n"%(code,instructions[code]["type"],fileName))
		
		counter += 1
		
	print("Read instructions for %d files from %s"%(counter,fileName))	
	
# Get Admissions
def getAdmissions(dir,inId,admissions):
	
	lines,header = readers.read_lines(dir,"ICUSTAYS",inId) 
		
	for line in lines:	
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		admissions.append(line[header["INTIME"]])

# Handle Output 
def writeOutput(dir,inId,outId,outputInstructions,admissions,outFile,signals,logger):

	lines,header = readers.read_lines(dir,"OUTPUTEVENTS",inId)

	# Collect
	outputInfo = defaultdict(list)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = line[header["ITEMID"]]
		if (itemId in outputInstructions.keys()):
			outputInfo[itemId].append(line)

	# Analyze
	timeIndex = header["CHARTTIME"]
	for itemId in outputInfo.keys():
		signal = outputInstructions[itemId]["name"]
		signals[signal] = 1
		entries = sorted(outputInfo[itemId],key=lambda l : l[timeIndex])
	
		prevTime = -1 ;
		admissionIdx = 0
		for line in entries:
			time = line[timeIndex]
			
			# Are we in a new admission ?
			while (admissionIdx < len(admissions) and time > admissions[admissionIdx]):
				admissionIdx +=1
				prevTime = -1
			
			if (line[header["STOPPED"]] != "" and not line[header["STOPPED"]].isspace()):
				raise ValueError("Stopped: %s/%s for %d at %s : %s\n"%(signal,itemId,id,time,line[header["STOPPED"]]))
			if (line[header["NEWBOTTLE"]] != "" and not line[header["NEWBOTTLE"]].isspace()):
				raise ValueError("NewBottle: %s/%s for %d at %s : %s\n"%(signal,itemId,id,time,line[header["NEWBOTTLE"]]))
			if (line[header["ISERROR"]] != "" and not line[header["ISERROR"]].isspace()):
				raise ValueError("Error: %s/%s for %d at %s : %s\n"%(signal,itemId,id,time,line[header["ISERROR"]]))

			value = line[header["VALUE"]]
			unit = line[header["VALUEUOM"]].upper()
			if (value == "0" and unit == ""):
				logger.write("NULL entry: %s/%s for %d at %s\n"%(signal,itemId,id,time))
			else:
				if (value == "" or value.isspace()):
					logger.write("Empty value: %s/%s for %d at %s\n"%(signal,itemId,id,time))
					value = "-1"

				outFile.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,signal,prevTime,time,value,unit,itemId))
			prevTime = time 

# Write Signals File
def writeSignalsFile(signalsFile,signals,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for output\n")
	signalsFile.write("#####################################################################\n")
	
	for signal in signals.keys():
		signalsFile.write("SIGNAL\t%s\t%d\t3\n"%(signal,signalId))
		signalId += 1
	
def generate_output_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Read intructions
	outputInstructions = {}
	readInstructions(config["OutputInstructions"], outputInstructions) 
	
	# Prepare output files
	outFileName = config["OutDir"] + "/" + config["DataFile"]
	outFile = open(outFileName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")

	logFileName = config["LogFile"]
	logger = open(logFileName,"w")
	
	
	# Loop and extract info
	n = len(ids)
	cnt = 0 
	signals = {}

	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%250 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		# admissions
		admissions = []
		getAdmissions(config["DataDir"],id,admissions)
		
		# output
		writeOutput(config["DataDir"],id,newId,outputInstructions,admissions,outFile,signals,logger)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signals,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 diagnosis file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=40)


args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_output_files(config,args.signalId)

