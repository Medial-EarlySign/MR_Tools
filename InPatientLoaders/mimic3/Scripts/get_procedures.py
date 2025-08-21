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
		
	required = ["IdsFile","OutDir","DataDir","LogFile","Procedures","Items"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
			
	defaults = {"DataFile":"Procedures","Suffix":"procedures"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
			
	return config

# Read Procedues Descriptions
def read_d_procedures(fileName,desc):
	
	with open(fileName,"r") as file:
		reader = csv.reader(file)
		header = reader.next()
		cols = {header[i] : i for i in range(len(header))}
		
		for row in reader:
			desc["ICD9:"+row[cols["ICD9_CODE"]]] = row[cols["SHORT_TITLE"]]

# Read items map
def read_d_items(fileName,desc):
	
	procId = ""
	with open(fileName,"r") as file:
		reader = csv.reader(file)
		header = reader.next()
		cols = {header[i] : i for i in range(len(header))}
		
		for row in reader:
			desc[row[cols["ITEMID"]]] = row[cols["LABEL"]]
			if (row[cols["LABEL"]] == "Procedures"):
				procId = row[cols["ITEMID"]]
				
	if (procId == ""):
		raise ValueError("Cannot find item-id for \"Procedures\"\n")
			
# find times of discharge (when diagnosis codes are given)
def getDischargeTime(dir,inId,dischargeTimes):
	
	lines,header = readers.read_lines(dir,"ADMISSIONS",inId) 
		
	done = {}
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
			
		adminId = line[header["HADM_ID"]]
		if (id in done.keys()):
			if (adminId in done[id].keys()):
				raise ValueError("Multiple Demographics info for %d/$%d"%(id,adminId))
			done[id][adminId] = 1
		else:
			done[id]= {adminId : 1}
			
		# Admission/Discharge
		dischargeTimes[adminId] = line[header["DISCHTIME"]]

# Handle ICD9 
def getICD9Codes(dir,inId,icd9):
	
	lines,header = readers.read_lines(dir,"PROCEDURES_ICD",inId)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		adminId = line[header["HADM_ID"]]
		code = line[header["ICD9_CODE"]]
		icd9[adminId].append(code)
		
# Write ICD9 procedures File
def writeICD9Codes(id,newId,procFile,icd9,dischargeTimes,dict):

	for adminId in icd9.keys():
		if (adminId not in dischargeTimes.keys()):
			raise ValueError("Cannot find discharge time for %s/%s\n"%(id,adminId))
		time = dischargeTimes[adminId]
		
		for code in icd9[adminId]:
			name = "ICD9:" + code
			procFile.write("%s\tPROCEDURE\t%s\t%s\t%s\tadmission\n"%(newId,time,time,name))
			dict[name] = 1		
		
# Handle PROCEDURES 
def writeProcedureEvents(dir,inId,outId,proc_desc,procFile,dict,logger):
	lines,header = readers.read_lines(dir,"PROCEDUREEVENTS_MV",inId)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		itemId = line[header["ITEMID"]]
		startTime = line[header["STARTTIME"]]
		endTime = line[header["ENDTIME"]]
		if (endTime < startTime):
			logger.write("Order problem for %s of %d : %s-%s\n"%(itemId,id,startTime,endTime))
		if (itemId not in proc_desc.keys()):
			raise ValueError("Cannot find %s in desc for %d at %s-%s\n"%(itemId,id,startTime,endTime))
		
		desc = proc_desc[itemId]
		procFile.write("%s\tPROCEDURE\t%s\t%s\t%s\tcurrent\n"%(outId,startTime,endTime,desc))
		dict[desc] = 1

# Handle Procedures in ChartEvents
def writeProcedureFromChartEvents(dir,inId,outId,procId,procFile,dict,logger):
	
	lines,header = readers.read_lines(dir,"CHARTEVENTS",inId) 
		
	done = {}
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = int(line[header["ITEMID"]])
		if (itemId != procId):
			continue
		
		time = line[header["CHARTTIME"]]
		proc = line[header["VALUE"]].replace('\"','') ;
		if (proc.isspace()):
			logger.write("Cannot find value for %s at %d at %s"%(signalName,id,time))
		procFile.write("%s\tPROCEDURE\t%s\t%s\t%s\tcurrent\n"%(outId,time,time,proc))
		dict[proc] = 1

		
# Write dictionary
def writeDictionary(dictFile,dict,icd9_desc):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for procedures\n")
	dictFile.write("#####################################################################\n")
	
	dictFile.write("SECTION\tPROCEDURE\n")
	index = 1000
	for key in dict.keys():
		dictFile.write("DEF\t%d\t%s\n"%(index,key))
		if (key in icd9_desc.keys()):
			dictFile.write("DEF\t%d\t%s:%s\n"%(index,key,icd9_desc[key]))
		index +=1		
	
# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for procedures\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tPROCEDURE\t%d\t12\tProcedures : ICD9 (admission, given at the end of admission) or direct description (current, given at time of proc.)\t11\n"%signalId)

def generate_proc_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Prepare output files
	procFileName = config["OutDir"] + "/" + config["DataFile"]
	procFile = open(procFileName,"w")

	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")

	logFileName = config["LogFile"]
	logger = open(logFileName,"w")
	
	# Descriptions
	icd9_desc = {}
	read_d_procedures(config["Procedures"],icd9_desc)

	proc_desc = {}
	procId = read_d_items(config["Items"],proc_desc)
	
	# Loop and extract info
	dict = {"admission":1, "current":1}
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%20 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		dischargeTimes = {}
		getDischargeTime(config["DataDir"],id,dischargeTimes)
		
		# ICD9
		icd9 = defaultdict(list)
		getICD9Codes(config["DataDir"],id,icd9)
	
		# Write ICD9
		writeICD9Codes(id,newId,procFile,icd9,dischargeTimes,dict)
		
		# PROCEDURE-EVENTS
		writeProcedureEvents(config["DataDir"],id,newId,proc_desc,procFile,dict,logger)

		# Procedure in CHART-EVENTS
		writeProcedureFromChartEvents(config["DataDir"],id,newId,procId,procFile,dict,logger)
		
	# Generate Dictionary
	writeDictionary(outDict,dict,icd9_desc)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 procedures file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=80)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_proc_files(config,args.signalId)

