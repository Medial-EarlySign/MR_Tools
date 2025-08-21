#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random

readers = mimic3_readers()
signals = ["MARITAL_STATUS","ETHNICITY","INSURANCE","RELIGION","ADMISSION_TYPE","ADMISSION_LOCATION"]

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
		
	required = ["IdsFile","OutDir","DataDir"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
	
	defaults = {"DataFile":"Demographics","Suffix":"demographics"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
	
	return config

# Handle Demographics (one per admission)
def writeDemographicsInfo(dir,inId,outId,outFile,dictionary):
	
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
		time = line[header["ADMITTIME"]]

		outFile.write("%d\tADMISSION\t%s\t%s\t%s\n"%(outId,time,line[header["DISCHTIME"]],adminId))
		status = 1 - int(line[header["HOSPITAL_EXPIRE_FLAG"]])
		outFile.write("%d\tDISCHARGE_STATUS\t%s\t%d\n"%(outId,time,status))
		
		# Further info
		for signal in signals:
			if(line[header[signal]] != ""):
				entry = "%s:%s"%(signal,line[header[signal]])
				dictionary[signal][entry]=1
				outFile.write("%d\t%s\t%s\t%s\n"%(outId,signal,time,entry))

# Handle Patients (one per id)
def writePatientsInfo(dir,inId,outId,outFile):
	
	# PATIENTS
	lines,header = readers.read_lines(dir,"PATIENTS",inId)
	if (len(lines) > 1):
		raise ValueError("More than one PATIENTS lines for %d"%inId)
	
	if (len(lines)==0):
		print("No Lines found")
		
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		if (line[header["GENDER"]] == "M"):
			outFile.write("%s\tGENDER\t1\n"%outId)
		else:
			outFile.write("%s\tGENDER\t2\n"%outId)
			
		dob = line[header["DOB"]]
		outFile.write("%s\tBDATE\t%s\n"%(outId,dob))
		dobInfo = dob.split("-")
		outFile.write("%s\tBYEAR\t%s\n"%(outId,dobInfo[0]))
		
		if (line[header["DOD"]] != ""):
			outFile.write("%s\tDEATH\t%s\n"%(outId,line[header["DOD"]]))
		
		r = random.random()
		train = 1
		if (r > 0.9):
			train = 3
		elif (r>0.7):
			train = 2
		outFile.write("%s\tTRAIN\t%d\n"%(outId,train))

# Write demographics dictionary
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for demographics\n")
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
	signalsFile.write("# Signals for demographics\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tGENDER\t%d\t0\tGender (1=M, 2=F)\t0\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tBDATE\t%d\t4\tBirth Date (at midnight)\t0\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tBYEAR\t%d\t0\tBirth Year\t0\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tDEATH\t%d\t4\tDeath Date (at midnight)\t0\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tTRAIN\t%d\t0\tTrain Flag(70%% 1, 20%% 2, 10%% 3)\t0\n"%signalId)
	signalId += 1

	signalsFile.write("SIGNAL\tADMISSION\t%d\t3\tAdmission Period + id\t0\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tDISCHARGE_STATUS\t%d\t1\tDischarge from hospital (1 = Alive, 0 = Dead)\t0\n"%signalId)
	signalId += 1

	for signal in signals:
		signalsFile.write("SIGNAL\t%s\t%d\t1\t\t1\n"%(signal,signalId))
		signalId += 1

def generate_dem_files(config,signalId):

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
	
	# Loop and extract info
	dictionary = defaultdict(dict)
	for rec in ids:
		(id,newId) = rec
		
		# Patients
		writePatientsInfo(config["DataDir"],id,newId,outFile)

		# Demographics
		writeDemographicsInfo(config["DataDir"],id,newId,outFile,dictionary)

		
	# Generate Dictionary
	writeDictionary(outDict,dictionary)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 demographics file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=1)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_dem_files(config,args.signalId)

