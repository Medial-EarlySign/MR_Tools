#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random

readers = mimic3_readers()
susceptCode = {"S":"Sensitive", "P":"NA", "I":"Intermediate", "R":"Resistent"}

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
		
	required = ["IdsFile","OutDir","DataDir","MicrobiologySpecimens","MicrobiologyOrganisms","MicrobiologyAntiBiotics","ATCInstructions"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))

	defaults = {"DataFile":"Microbiology","Suffix":"micro"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
			
	return config

		
# Read Descriptions file
def readDescFile(fileName,idx):
	descMap = {}
	with open(fileName,"r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			descMap[fields[0]] = fields[idx]
	return descMap

	
# Write Microbiology info
def writeMicrobiology(dir,inId,outId,specimens,organisms,antibiotics,atcInstructions,outFile,dictionary):

	lines,header = readers.read_lines(dir,"MICROBIOLOGYEVENTS",inId)

	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
			
		time = line[header["CHARTTIME"]]
		if (time == ""):
			time = line[header["CHARTDATE"]]
		if (time==""):
			raise ValueError("No Time given at all for %s"%(" ".join(line)))
			
		spec = line[header["SPEC_TYPE_DESC"]]
		if (spec == ""):
			spec = "NoSpecimenGiven"
		elif (spec in specimens.keys()):
			spec = specimens[spec]
		else:
			raise ValueError("Cannot find spec %s in file\n"%spec)
		
		org = line[header["ORG_NAME"]].rstrip(" ")
		if (org == ""):
			org = "NoOrganism"
		elif (org in organisms.keys()):
			org = organisms[org]
		else:
			raise ValueError("Cannot find org %s in file\n"%org)
		entry1 = "Culture:%s|%s"%(spec,org)
		dictionary["MICROBIOLOGY"][entry1] = 1
		
		ab = line[header["AB_NAME"]]
		if (ab == ""):
			ab = "NoAntiBiotics"
		elif (ab in antibiotics.keys()):
			atc = antibiotics[ab]
		else:
			raise ValueError("Cannot find ab %s in file\n"%ab)
		
		if (ab == "NoAntiBiotics"):
			sensitivity = "NA"
		else:
			sensitivity = susceptCode[line[header["INTERPRETATION"]]]
		
		if (ab in atcInstructions.keys()):
			entry2 = "Test:%s|%s|%s"%(ab,atcInstructions[ab],sensitivity)
		else:
			entry2 = "Test:%s|%s|%s"%(ab,"NA",sensitivity)
		outFile.write("%d\tMICROBIOLOGY\t%s\t%s\t%s\t%s\n"%(outId,time,time,entry1,entry2))
		dictionary["MICROBIOLOGY"][entry2] = 1

		
# Write dictionary
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for microbiology\n")
	dictFile.write("#####################################################################\n")
	
	
	index = 1000
	negativeCultureEntries = []
	for signal in dictionary.keys():
		dictFile.write("SECTION\t%s\n"%signal)
		for key in dictionary[signal].keys():
			dictFile.write("DEF\t%d\t%s\n"%(index,key))
			index +=1
			
			if (key.find("NoOrganism")>0):
				negativeCultureEntries.append(key)
	
	dictFile.write("DEF\t%d\tNoGrowth\n"%index)
	for entry in negativeCultureEntries:
		dictFile.write("SET\tNoGrowth\t%s\n"%entry)
	
# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for microbiology\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tMICROBIOLOGY\t%d\t12\tIndicating a microbiology test\t11\n"%signalId)
	
	
def generate_microbiology_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Prepare output files
	outFileName = config["OutDir"] + "/" + config["DataFile"]
	outFile = open(outFileName,"w")

	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")
	
	# Read descriptions
	specimens = readDescFile(config["MicrobiologySpecimens"],2)
	organisms = readDescFile(config["MicrobiologyOrganisms"],2)
	antibiotics = readDescFile(config["MicrobiologyAntiBiotics"],2)
	atcInstructions = readDescFile(config["ATCInstructions"],1)

	# Loop and extract info
	dictionary = defaultdict(dict)
	
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%1000 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		# Microbiolgy
		writeMicrobiology(config["DataDir"],id,newId,specimens,organisms,antibiotics,atcInstructions,outFile,dictionary)
		
	# Generate Dictionary
	writeDictionary(outDict,dictionary)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)

	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 microbiology file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=75)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_microbiology_files(config,args.signalId)

