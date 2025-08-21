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
	
	defaults = {"DataFile":"Diagnosis","Suffix":"diagnosis"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
	
	return config

# Write Diagnoses
def writeDiagnoses(dir,inId,outId,dictionary,outFile,logFile):
	
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
			
	# Hopsital Admission set at 01/01/hospitaldischargeyear at hospitaladmittime24
		year = int(line[header["hospitaldischargeyear"]])
		time = line[header["hospitaladmittime24"]]
		admissionTime_s = "%s-01-01 %s"%(year,time)
		admissionTime = datetime.strptime(admissionTime_s, "%Y-%m-%d %H:%M:%S")
		unitAdmitTime = admissionTime + timedelta(minutes=-int(line[header["hospitaladmitoffset"]]))

	# DIAGNOSIS
	lines,header = readers.read_lines(dir,"diagnosis",inId)
	for line in lines:
		id = int(line[header["patientunitstayid"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))	
	
		time = unitAdmitTime + timedelta(minutes=int(line[header["diagnosisoffset"]]))
		diagnosis = line[header["diagnosisstring"]]
		icd = line[header["icd9code"]]
		priority = line[header["diagnosispriority"]]
		if (diagnosis==""):
			logFile.write("Cannot find diagnosis string at %d/%s\n"%id,time)
		else:
			outFile.write("%s\tDIAGNOSIS\t%s\t%s\t%s\n"%(outId,time,diagnosis,priority))
			dictionary[priority] = []
			dictionary[diagnosis] = []
			if (icd != ""):
				fields = str.split(icd.replace(" " ,""),",")
				for i in range(len(fields)):
					if (fields[i][0] >= '0' and fields[i][0] <= '9'):
						dictionary[diagnosis].append("ICD9:" + fields[i] + ":" + diagnosis)
					else:
						dictionary[diagnosis].append("ICD10:" + fields[i] + ":" + diagnosis)

	# AdmissionDx
	lines,header = readers.read_lines(dir,"admissionDx",inId)
	for line in lines:
		id = int(line[header["patientunitstayid"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))		
		
		time = unitAdmitTime + timedelta(minutes=int(line[header["admitdxenteredoffset"]]))
		
		if (line[header["admitdxname"]] == line[header["admitdxtext"]]):
			diagnosis = "APACHE:" + line[header["admitdxpath"]]
		else:
			diagnosis = "APACHE:" + line[header["admitdxpath"]] + "=" + line[header["admitdxtext"]]
		
		outFile.write("%s\tDIAGNOSIS\t%s\t%s\tadmission\n"%(outId,time,diagnosis))
		dictionary[diagnosis] = []

	
# Write diganosis dictionary
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for diagnosis\n")
	dictFile.write("#####################################################################\n")
	
	index = 1000
	dictFile.write("SECTION\tDIAGNOSIS\n")
	for key in dictionary.keys():
		dictFile.write("DEF\t%d\t%s\n"%(index,key))
		for extra in dictionary[key]:
			dictFile.write("DEF\t%d\t%s\n"%(index,extra))
		index +=1

# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for diagnosis\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tDIAGNOSIS\t%d\t6\tfirst channel = diagnosis, second = priority\t11\n"%signalId)

def generate_diagnosis_files(config,signalId):

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
	dictionary = {"admission":[]}

	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%500 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		
		# Patients
		writeDiagnoses(config["DataDir"],id,newId,dictionary,outFile,logFile)

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
generate_diagnosis_files(config,args.signalId)

