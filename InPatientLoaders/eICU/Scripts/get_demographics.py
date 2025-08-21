#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
import random
import os
from datetime import datetime, date, time, timedelta

path  = os.environ['MR_ROOT'] + "/Tools/InPatientLoaders/mimic3/Scripts"
sys.path.append(path)
from indexer import *

readers = mimic3_readers()
readers.identifier = "patientunitstayid"
readers.maxId = 201000

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
	
	defaults = {"DataFile":"Demographics","Suffix":"demographics"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
	
	return config

# Update rec
def update_value(patientInfo,id,key,rec,logFile):
	if (key in patientInfo[id].keys() and patientInfo[id][key][-1] != rec[-1]):
		logFile.write("Inconsistency for %s:%s - %s vs %s\n"%(id,key,patientInfo[id][key][-1],rec[-1]))
	else:
		patientInfo[id][key] = rec
	
# Handle Patients 
def getPatientInfo(dir,inId,outId,patientInfo,logFile):
	
	# PATIENTS
	lines,header = readers.read_lines(dir,"patient",inId)
	if (len(lines) > 1):
		raise ValueError("More than one PATIENTS lines for %d"%inId)
	
	if (len(lines)==0):
		print("No Lines found")
		
	for line in lines:
		id = int(line[header["patientunitstayid"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		# Gender
		update_value(patientInfo,outId,"GENDER",[line[header["gender"]]],logFile)

		# Train
		if ("TRAIN" not in patientInfo[outId].keys()):
			r = random.random()
			if (r > 0.9):
				patientInfo[outId]["TRAIN"] = 3
			elif (r>0.7):
				patientInfo[outId]["TRAIN"] = 2
			else:
				patientInfo[outId]["TRAIN"] = 1
		
		# Times
		if (line[header["hospitaldischargeyear"]] == ""):
			raise ValueError("Cannot set year for id %d"%id)
		
		# Hopsital Admission set at 01/01/hospitaldischargeyear at hospitaladmittime24
		year = int(line[header["hospitaldischargeyear"]])
		time = line[header["hospitaladmittime24"]]
		admissionTime_s = "%s-01-01 %s"%(year,time)
		admissionTime = datetime.strptime(admissionTime_s, "%Y-%m-%d %H:%M:%S")
		unitAdmitTime = admissionTime + timedelta(minutes=-int(line[header["hospitaladmitoffset"]]))
		unitDischargeTime = unitAdmitTime + timedelta(minutes = int(line[header["unitdischargeoffset"]]))
		dischargeTime = unitAdmitTime + timedelta(minutes = int(line[header["hospitaldischargeoffset"]]))

		# Age
		if (line[header["age"]] == ""):
			logFile.write("Cannot set age for id %d\n"%id)
		else:
			if (line[header["age"]] == "> 89"):
				age = 300
			else:
				age = int(line[header["age"]])
				
			yob = year - age
			update_value(patientInfo,outId,"BDATE",["%s-07-01 00:00:00"%yob],logFile)
			update_value(patientInfo,outId,"BYEAR",[yob],logFile)

		# Admission
		update_value(patientInfo,outId,"ADMISSION",[admissionTime,dischargeTime,line[header["hospitalid"]]],logFile)

		# Further info
		if (line[header["hospitaladmitsource"]] != ""):
			update_value(patientInfo,outId,"ADMISSION_LOCATION",[admissionTime,line[header["hospitaladmitsource"]]],logFile)
		if (line[header["hospitaldischargelocation"]] != ""):
			update_value(patientInfo,outId,"DISCHARGE_LOCATION",[dischargeTime,line[header["hospitaldischargelocation"]]],logFile)
		if (line[header["ethnicity"]] != ""):
			update_value(patientInfo,outId,"ETHNICITY",[admissionTime,line[header["ethnicity"]]],logFile)

		# Death
		unitDischargeStatus = line[header["unitdischargestatus"]]
		hospitalDischargeStatus = line[header["hospitaldischargestatus"]]
		status = 1
		if (unitDischargeStatus == "" and hospitalDischargeStatus == ""):
			logFile.write("Cannot find discharge status for id %d"%id)
		elif (unitDischargeStatus == "Expired" or hospitalDischargeStatus == "Expired"):
			if (unitDischargeStatus == "Expired" and unitDischargeTime < dischargeTime):
				deathTime = unitDischargeTime
			else:
				deathTime = dischargeTime
			update_value(patientInfo,outId,"DEATH",[deathTime],logFile)
			status = 0

		update_value(patientInfo,outId,"DISCHARGE_STATUS",[dischargeTime,status],logFile)
		
		# Stays
		if ("STAY" not in patientInfo[outId].keys()):
			patientInfo[outId]["STAY"] = []
		
		# Previous :
		if (line[header["unitadmitsource"]] != ""):
			if (len(patientInfo[outId]["STAY"]) == 0 or patientInfo[outId]["STAY"][-1][-2] != line[header["unitadmitsource"]] ):
				patientInfo[outId]["STAY"].append([-1,unitAdmitTime,line[header["unitadmitsource"]],"NA"])
			else:
				patientInfo[outId]["STAY"][-1][1] = unitAdmitTime
			
		# Current : 
		patientInfo[outId]["STAY"].append([unitAdmitTime,unitDischargeTime,line[header["unittype"]],"Philips"])
		
		# Next
		if (line[header["unitdischargelocation"]] != ""):
			destination = line[header["unitdischargelocation"]]
			if (unitDischargeTime != dischargeTime and destination != "Home" and destination != "Death"):
				patientInfo[outId]["STAY"].append([unitDischargeTime,-1,destination,"NA"])

def write_data(id,field,rec,outFile):
	outFile.write("%s\t%s"%(id,field))
	for subRec in rec:
		outFile.write("\t%s"%subRec)
	outFile.write("\n")
		
def writePatientInfo(patientInfo,dictionary,outFile,logFile):
	
	for id in patientInfo.keys():
		if ("GENDER" not in patientInfo[id].keys()):
			logFile.write("Cannot find gender for %d\n"%id)
		elif (patientInfo[id]["GENDER"][0] == "Male"):
			outFile.write("%s\tGENDER\t1\n"%id)
		elif (patientInfo[id]["GENDER"][0] == "Female"):
			outFile.write("%s\tGENDER\t2\n"%id)
		else:
			logFile.write("Cannot parse gender \'%s\' for %d\n"%(patientInfo[id]["GENDER"],id))
	
		outFile.write("%s\tTRAIN\t%s\n"%(id,patientInfo[id]["TRAIN"]))

		for field in ("BDATE","BYEAR","ADMISSION","DISCHARGE_STATUS"):
			if (field not in patientInfo[id].keys()):
				logFile.write("Cannot find %s for %d\n"%(field,id))
			else:
				write_data(id,field,patientInfo[id][field],outFile)

		for field in ("ADMISSION_LOCATION","DISCHARGE_LOCATION","ETHNICITY"):
			if (field not in patientInfo[id].keys()):
				logFile.write("Cannot find %s for %d\n"%(field,id))
			else:
				write_data(id,field,patientInfo[id][field],outFile)
				dictionary[patientInfo[id][field][-1]] = 1
				
		if ("DEATH" in patientInfo[id].keys()):
			outFile.write("%s\tDEATH\t%s\n"%(id,patientInfo[id]["DEATH"][0]))
			
		if ("STAY" not in patientInfo[id].keys()):
			logFile.write("Cannot find STAY for %d\n"%id)
		else:
			for stay in patientInfo[id]["STAY"]:
				write_data(id,"STAY",stay,outFile)
				dictionary[stay[-1]] = 1
				dictionary[stay[-2]] = 1

# Write demographics dictionary
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for demographics\n")
	dictFile.write("#####################################################################\n")
	
	signals = ("ADMISSION_LOCATION","DISCHARGE_LOCATION","ETHNICITY","STAY")
	
	index = 1000
	dictFile.write("SECTION\t%s\n"%",".join(signals))
	for key in dictionary.keys():
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
	signalsFile.write("SIGNAL\tADMISSION_LOCATION\t%d\t1\tSource of admission to hospital\t1\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tDISCHARGE_LOCATION\t%d\t1\tDestination of discharge from hospital\t1\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tETHNICITY\t%d\t1\t\t1\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tSTAY\t%d\t12\tStay information\t11\n"%signalId)

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
	
	logFileName = config["LogFile"]
	logFile = open(logFileName,"w")
	
	# Loop and extract info
	dictionary = defaultdict(dict)
	train = {}
	patientInfo = defaultdict(dict)
	
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%500 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		
		# Patients
		getPatientInfo(config["DataDir"],id,newId,patientInfo,logFile)

	# Write
	writePatientInfo(patientInfo,dictionary,outFile,logFile)
	
	# Generate Dictionary
	writeDictionary(outDict,dictionary)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare eICU demographics file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=1)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_dem_files(config,args.signalId)

