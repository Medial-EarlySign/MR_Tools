#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random

readers = mimic3_readers()
route2key = {"By Mouth":"By Mouth","Gastric/Feeding Tube":"Gastric/Tube","GU":"GU","Intravenous":"Infusion","Intravenous Infusion":"Infusion","Intravenous Push":"Push",\
			 "IV Drip":"IV DRIP", "Drip":"IV DRIP", "Nasogastric":"Nasogastric", "Oral or Nasogastric":"Nasogastric","IV Piggyback":"Piggyback","Oral":"Oral"}
route2out = {"By Mouth":"PO","Gastric/Feeding Tube":"Gastric/Tube","GU":"GU","Intravenous":"IV","Intravenous Infusion":"IV","Intravenous Push":"IV",\
			 "IV Drip":"IV DRIP", "Drip":"IV DRIP", "Nasogastric":"Nasogastric", "Oral or Nasogastric":"Oral or Nasogastric","IV Piggyback":"IV","Oral":"PO"}

units = {"CAL":"amount","CC":"volume","GM":"amount","MCG":"amount","MEQ":"amount","MG":"amount","ML":"volume","TSP":"amount","U":"amount",\
		 "GMHR":"rate","MCGHR":"rate","MCGKGHR":"rate","MCGKGMIN":"rate","MCGMIN":"rate","MGHR":"rate","MGKGHR":"rate","MGMIN":"rate","UHR":"rate","UMIN":"rate", "UKGHR":"rate", \
		 "GRAMS/HOUR":"rate","GRAMS/MIN":"rate","MCG/HOUR":"rate","MCG/KG/HOUR":"rate","MCG/KG/MIN":"rate","MEQ./HOUR":"rate","MG/HOUR":"rate","MG/KG/HOUR":"rate","MG/MIN":"rate", \
		 "GRAMS/KG/MIN":"rate","MCG/MIN":"rate","UNITS/MIN":"rate", "UNITS/HOUR":"rate", "ML/HOUR":"rate","DOSE":"amount","UNITS":"amount","GRAMS":"amount","MEQ.":"amount","MMOL":"amount",
		 }

type2key = {"01-Drips,02-Fluids (Crystalloids)":"IV DRIP","02-Fluids (Crystalloids),Additive (Crystalloid)":"Infusion","03-IV Fluid Bolus,":"Infusion","04-Fluids (Colloids),":"Infusion","05-Med Bolus,":"Infusion","06-Insulin (Non IV),":"NON_IV","07-Blood Products,":"Infusion","08-Antibiotics (IV),02-Fluids (Crystalloids)":"Infusion","09-Antibiotics (Non IV),":"NON_IV","10-Prophylaxis (IV),02-Fluids (Crystalloids)":"Infusion","11-Prophylaxis (Non IV),":"NON_IV","12-Parenteral Nutrition,Additives (PN)":"Infusion","13-Enteral Nutrition,Additives (EN)":"Enteral","14-Oral/Gastric Intake,":"Gastric/Tube","16-Pre Admission,":"Infusion"}
type2out = {"01-Drips,02-Fluids (Crystalloids)":"IV DRIP","02-Fluids (Crystalloids),Additive (Crystalloid)":"IV","03-IV Fluid Bolus,":"IV","04-Fluids (Colloids),":"IV","05-Med Bolus,":"IV","06-Insulin (Non IV),":"PO","07-Blood Products,":"IV","08-Antibiotics (IV),02-Fluids (Crystalloids)":"IV","09-Antibiotics (Non IV),":"PO","10-Prophylaxis (IV),02-Fluids (Crystalloids)":"IV","11-Prophylaxis (Non IV),":"PO","12-Parenteral Nutrition,Additives (PN)":"IV","13-Enteral Nutrition,Additives (EN)":"Enteral","14-Oral/Gastric Intake,":"Gastric/Tube","16-Pre Admission,":"IV"}

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
		
	required = ["IdsFile","OutDir","DataDir","LogFile","CareVueDescriptions","CareVueInputInstructions","ATCInstructions","CareVureReRouter","MetaVisionDescriptions","MetaVisionInputInstructions"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))
			
	defaults = {"DataFile":"Input","Suffix":"input"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
	return config

# Reading - instructions file
def readInstructions(DescriptionsFile,InstructionsFile,instructions,name2itemIds):
	# Descriptions
	
	with open(DescriptionsFile,"r") as file:
		for line in file:
			[itemId,description] = str.split(line.rstrip("\r\n").upper(),"\t")
			name2itemIds[description.upper().rstrip(" ")].append(itemId)

	# Instructions
	with open(InstructionsFile,"r") as file:
		for line in file:
			info = str.split(line.rstrip("\r\n"),"\t")
			name = info.pop(0).upper()
			route = info.pop(0)
			if (name not in name2itemIds.keys()):
				raise ValueError("Cannot find itemId for \'%s\'"%name)
			for itemId in name2itemIds[name]:
				if (route not in instructions[itemId]):
					instructions[itemId][route] = []
				instructions[itemId][route].append(info)
			
# Reading - more instructions
def readExtraInstructions(atcInstructionsFile,atcInstructions,reroutingFile,rerouting,name2itemIds):
	# Dict Instructions
	with open(atcInstructionsFile,"r") as file:
		for line in file:
			[name,atc] = str.split(line.rstrip("\r\n"),"\t")
			atcInstructions[name] = atc
				
	# Rerouting
	with open(reroutingFile,"r") as file:
		for line in file:
			[name,route] = str.split(line.rstrip("\r\n"),"\t")
			if (name not in name2itemIds.keys()):
				raise ValueError("Cannot find itemId for \'%s\'"%name)
			for itemId in name2itemIds[name]:
				rerouting[itemId] = route
	
# Get Admissions
def getAdmissions(dir,inId,admissions):
	
	lines,header = readers.read_lines(dir,"ICUSTAYS",inId) 
		
	for line in lines:	
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		admissions.append(line[header["INTIME"]])

# Add entry to dictionary
def addToDictionary(section,name,type,atcInstructions,dictionary,suffix=""):
	
	if (name in atcInstructions.keys()):
		fullName = "%s:%s%s|%s|%s"%(section,name,suffix,atcInstructions[name],type)
	else:
		fullName = "%s:%s%s|%s|%s"%(section,name,suffix,"NA",type)
	dictionary[section][fullName] = 1
	return fullName
	
# Handle Input - CareVue 
def writeCareVueInputs(dir,inId,outId,instructions,rerouting,admissions,outFile,logger,dictionary,atcInstructions):

	lines,header = readers.read_lines(dir,"INPUTEVENTS_CV",inId)

	# Collect
	inputInfo = defaultdict(lambda: defaultdict(list))
	inputKeys = defaultdict(dict)
	inputOutTypes = defaultdict(dict)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = line[header["ITEMID"]]
		if (itemId in instructions.keys()):
			route = line[header["ORIGINALROUTE"]].rstrip(" ")
			if (route == ""):
				if (itemId not in rerouting.keys()):
					logger.write("Cannot find instructions for %s/%s\n"%(itemId,route))
					continue
				key =  route2key[rerouting[itemId]]
				outType= route2out[rerouting[itemId]]
			else:
				key = route2key[route]
				outType= route2out[route]
				
			if (key in instructions[itemId].keys()):
				inputInfo[itemId][route].append(line)
				inputKeys[itemId][route] = key
				inputOutTypes[itemId][route] = outType
			else:
				logger.write("Cannot find instructions for %s/%s\n"%(itemId,route))
		else:
			logger.write("Missing itemId %s\n"%itemId)
			

	# Analyze
	timeIndex = header["CHARTTIME"]
	for itemId in inputInfo.keys():
		for route in inputInfo[itemId].keys():
			entries = sorted(inputInfo[itemId][route],key=lambda l : l[timeIndex])
			key = inputKeys[itemId][route]
			outType = inputOutTypes[itemId][route]
			entryInstructions = instructions[itemId][key]
			
			prevTime = -1 ;
			admissionIdx = 0
			for line in entries:
				time = line[timeIndex]
			
				# Are we in a new admission ?
				while (admissionIdx < len(admissions) and time > admissions[admissionIdx]):
					admissionIdx +=1
					prevTime = -1
			
				if (line[header["STOPPED"]] != "" and not line[header["STOPPED"]].isspace()):
					stopField = line[header["STOPPED"]]
					if (stopField == "D/C'd" or stopField == "Stopped"):
						prevTime = -1
					elif (stopField == "Restart"):
						prevTime = time
					elif (stopField != "NotStopd"):
						raise ValueError("Unknown STOPPED field \'%s\'"%stopField)
					continue
					
				# Check amount/rate 
				amount = line[header["AMOUNT"]]
				amountUnit = line[header["AMOUNTUOM"]]
				rate = line[header["RATE"]]
				rateUnit = line[header["RATEUOM"]]	
				
				if ((amount != "" and rate != "") or (amountUnit != "" and rateUnit != "")):
					logger.write("Both rate and amount given for %d %s %s %s\n"%(id,time,itemId,route))
					prevTime = time
					continue
				
				if (rate == "" and amount == ""): 
					if (amountUnit != "" and line[header["ORIGINALAMOUNT"]] != ""):
						amount = line[header["ORIGINALAMOUNT"]]
						amountUnit = line[header["ORIGINALAMOUNTUOM"]]
					elif (rateUnit != "" and line[header["ORIGINALRATE"]] != ""):
						rate = line[header["ORIGINALRATE"]]
						rateUnit = line[header["ORIGINALRATEUOM"]]	

				#AMOUNT
				if (amount != ""):
					unit = amountUnit.upper()
					if (unit not in units.keys()):
						logger.write("Unknown unit for %d %s %s : %s %s %s\n"%(id,time,itemId,route,amount,unit))
					else:
						# Take volume of fluids
						if (units[unit] == "volume"):
							outFile.write("%s\tFLUID_INTAKE\t%s\t%s\t%s\t%s\t%s\n"%(outId,prevTime,time,amount,unit,itemId))

							# Check instructions ...
						for inst in entryInstructions:
							# Only fluid intake
							if (inst[0] == "Fluid"):
								if (units[unit] != "volume"):
									logger.write("Problematic unit %s for fluid %s %s %s : %s %s\n"%(unit,id,time,itemId,route,amount,unit))
							# Nutrtion information
							elif (inst[0] == "NUTRITION"):
								outFile.write("%s\tNUTRITION\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,prevTime,time,inst[1],amount,unit,itemId))
								dictionary["NUTRITION"][inst[1]]=1
							# Drugs and Ions
							elif (inst[0] == "DRUG"):
								if (units[unit] == "volume" and len(inst)>2):
									if(float(inst[2])==-1):
										fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,prevTime,time,fullName,-1.0,unit,key,itemId))
									else:
										if (len(inst)!=4):
											raise ValueError("Problem at %s : %s\n",line,inst)
										fullUnit = inst[3] + " X " + unit
										amount = float(amount) * float(inst[2])
										fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,prevTime,time,fullName,amount,fullUnit,key,itemId))
								elif (units[unit] == "amount"):
									if (len(inst)==2):
										fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,prevTime,time,fullName,amount,unit,key,itemId))
									elif (float(inst[2])==-1):
										fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,prevTime,time,fullName,-1.0,unit,key,itemId))
									else:
										logger.write("Problematic unit %s for drug-amount %d %s %s %s : %s %s and inst=\'%s\'\n"%(unit,id,time,itemId,route,amount,unit,inst))
								else:
									logger.write("Problematic unit %s for drug-amount %d %s %s %s : %s %s and inst=\'%s\'\n"%(unit,id,time,itemId,route,amount,unit,inst))
				# RATE
				elif (line[header["RATE"]] != ""):
					if (key != "IV DRIP"):
						raise ValueError("Cannot handle rate for route \'%s\'"%key)
						
					unit = rateUnit.upper()
					if (unit not in units.keys()):
						logger.write("Unknown unit for %d %s %s : %s %s %s\n"%(id,time,itemId,route,rate,unit))
					else:
						unitType = units[unit]
						if (unitType != "rate"):
							logger.write("Problematic unit %s for rate %s %s %s : %s %s\n"%(unit,id,time,itemId,route,rate,unit))
						else:
							for inst in entryInstructions:
								# All instructions are "DRUG",drugName, but amount may or may not be per kg
								if (unit.find("KG")>0):
									name = inst[1] + "_PER_KG"
								else:
									name = inst[1]
								fullName = addToDictionary("DRUG_ADMINISTERED_RATE",name,outType,atcInstructions,dictionary)
								outFile.write("%s\tDRUG_ADMINISTERED_RATE\t%s\t%s\t%s\t%s\t%s\n"%(outId,time,fullName,rate,unit,itemId))
				# NEITHER
				else:
					logger.write("Neither amount for rate are given for %d %s %s %s\n"%(id,time,itemId,route))

				prevTime = time 

# Handle Input - MetaVision 
def writeMetaVisionInputs(dir,inId,outId,instructions,admissions,outFile,logger,dictionary,atcInstructions):

	lines,header = readers.read_lines(dir,"INPUTEVENTS_MV",inId)
	
	# Collect
	inputInfo = defaultdict(lambda: defaultdict(list))
	inputKeys = defaultdict(dict)
	inputOutTypes = defaultdict(dict)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = line[header["ITEMID"]]
		if (itemId in instructions.keys()):
			type = line[header["ORDERCATEGORYNAME"]]+","+ line[header["SECONDARYORDERCATEGORYNAME"]]
			if (type not in type2key.keys()):
				logger.write("Cannot identify type %s for itemId %s"%(type,itemId))
			else:
				key = type2key[type]
				outType= type2out[type]
				if (key in instructions[itemId].keys()):
					inputInfo[itemId][type].append(line)
					inputKeys[itemId][type] = key
					inputOutTypes[itemId][type] = outType
				else:
					logger.write("Cannot find instructions for %s/%s\n"%(itemId,type))
		else:
			logger.write("Missing itemId %s\n"%itemId)

	# Analyze
	timeIndices = (header["STARTTIME"],header["ENDTIME"])
	for itemId in inputInfo.keys():
		for type in inputInfo[itemId].keys():
			entries = sorted(inputInfo[itemId][type],key=lambda l : l[timeIndices[0]])
			key = inputKeys[itemId][type]
			outType = inputOutTypes[itemId][type] 
			entryInstructions = instructions[itemId][key]
			
			admissionIdx = 0
			for line in entries:
				times = [line[idx] for idx in timeIndices]
			
				# Are we in a new admission ?
				while (admissionIdx < len(admissions) and times[0] > admissions[admissionIdx]):
					admissionIdx +=1
					prevTime = -1

				if (line[header["STATUSDESCRIPTION"]] != "" and not line[header["STATUSDESCRIPTION"]].isspace()):
					status = line[header["STATUSDESCRIPTION"]]
					if (status == "Rewritten"):
						logger.write("Rewritten info for %d %s %s %s-%s. Ignoring\n"%(id,itemId,type,times[0],times[1]))
						continue

				# Check amount
				if (line[header["AMOUNT"]] == "" and line[header["RATE"]]== ""):
					logger.write("Neither amount nor rate are given for %d %s %s %s\n"%(id,time,itemId,type))
					continue
					
				# Amount
				if (line[header["AMOUNT"]] != ""):
					amount = line[header["AMOUNT"]]
					unit = line[header["AMOUNTUOM"]].upper()
					if (unit not in units.keys()):
						logger.write("Unknown unit for %d %s-%s %s : %s %s %s\n"%(id,times[0],times[1],itemId,type,amount,unit))
					else:
						# Take volume of fluids
						if (units[unit] == "volume"):
							outFile.write("%s\tFLUID_INTAKE\t%s\t%s\t%s\t%s\t%s\n"%(outId,times[0],times[1],amount,unit,itemId))
							
						# Check instructions ...
						for inst in entryInstructions:
							# Only fluid intake
							if (inst[0] == "Fluid"):
								if (units[unit] != "volume"):
									logger.write("Problematic unit %s amount rate %s %s-%s %s : %s %s\n"%(unit,id,times[0],times[1],itemId,type,amount,unit))
							# Nutrtion information
							elif (inst[0] == "NUTRITION"):
								outFile.write("%s\tNUTRITION\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,times[0],times[1],inst[1],amount,unit,itemId))
								dictionary["NUTRITION"][inst[1]]=1
							# Drugs and Ions
							elif (inst[0] == "DRUG"):
								if (units[unit] == "volume" and len(inst)>2):
									fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
									if (len(inst)!=4):
										fullUnit = "MG/ML X " + unit
									else:
										fullUnit = inst[3] + " X " + unit

									if (float(inst[2])==-1.0):
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,times[0],times[1],fullName,-1.0,fullUnit,key,itemId))
									else:
										amount = float(amount) * float(inst[2])
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,times[0],times[1],fullName,amount,fullUnit,key,itemId))
								elif (units[unit] == "amount"):
									fullName = addToDictionary("DRUG_ADMINISTERED",inst[1],outType,atcInstructions,dictionary)
									if (len(inst)==2):
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(outId,times[0],times[1],fullName,amount,unit,key,itemId))
									elif (float(inst[2])==-1):
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,times[0],times[1],fullName,-1.0,unit,key,itemId))
									else:
										if (len(inst)!=4):
											raise ValueError("Problem at %s : %s\n",line,inst)
										fullUnit = inst[3] + " X " + unit
										amount = float(amount) * float(inst[2])
										outFile.write("%s\tDRUG_ADMINISTERED\t%s\t%s\t%s\t%f\t%s\t%s\t%s\n"%(outId,times[0],times[1],fullName,amount,fullUnit,key,itemId))
								else:
									logger.write("Problematic unit %s amount rate %d %s-%s %s %s : %s %s and inst=\'%s\'\n"%(unit,id,times[0],times[1],itemId,type,amount,unit,inst))

				# Rate
				if (line[header["RATE"]] != ""):
					rate = line[header["RATE"]]
					unit = line[header["RATEUOM"]].upper()
					if (unit not in units.keys()):
						logger.write("Unknown unit for %d %s-%s %s : %s %s %s\n"%(id,times[0],times[1],itemId,type,amount,unit))
					elif (units[unit] != "rate"):
						logger.write("Problematic unit %s for rate %d %s-%s %s %s : %s %s and inst=\'%s\'\n"%(unit,id,times[0],times[1],itemId,type,amount,unit,inst))
					else:				
						# Check instructions ...
						for inst in entryInstructions:
							if (inst[0] == "DRUG"):
								# consider rate only for drugs (and ions)
								if (unit.find("KG")>0):
									name = inst[1] + "_PER_KG"
								else:
									name = inst[1]
								
								fullName = addToDictionary("DRUG_ADMINISTERED_RATE",name,outType,atcInstructions,dictionary)
								if (len(inst)==2): 
									outFile.write("%s\tDRUG_ADMINISTERED_RATE\t%s\t%s\t%s\t%s\t%s\n"%(outId,times[0],fullName,rate,unit,itemId))
								elif (float(inst[2])==-1):
									if (len(inst)==4):
										fullUnit = inst[3] + " X " + unit
									else:
										fullUnit = unit
									outFile.write("%s\tDRUG_ADMINISTERED_RATE\t%s\t%s\t%f\t%s\t%s\n"%(outId,times[0],fullName,-1.0,fullUnit,itemId))
								else:
									if (len(inst)!=4):
										raise ValueError("Problem at %s : %s\n",line,inst)
									fullUnit = inst[3] + " X " + unit
									rate = float(rate) * float(inst[2])
									outFile.write("%s\tDRUG_ADMINISTERED_RATE\t%s\t%s\t%f\t%s\t%s\n"%(outId,times[0],fullName,rate,fullUnit,itemId))

# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for input\n")
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tDRUG_ADMINISTERED\t%d\t12\tAdministered Drug. First Channel = Name+Route, Second = amount\t10\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tDRUG_ADMINISTERED_RATE\t%d\t13\tPrescribed Solutions. First Channel = Name+Route, Second = rate\t10\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tFLUID_INTAKE\t%d\t3\tFluid intake\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tNUTRITION\t%d\t12\tAdministered Drug. First Channel = Name, Second = amount\t10\n"%signalId)	

# Write Dictionary File
def writeDictionary(dictFile,dictionary):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for input\n")
	dictFile.write("#####################################################################\n")

	index = 1000
	signals = dictionary.keys()
	dictFile.write("SECTION\t%s\n"%",".join(signals))
	for signal in signals:
		for key in dictionary[signal].keys():
			dictFile.write("DEF\t%d\t%s\n"%(index,key))
			index +=1
			
def generate_input_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Read intruction files for CareVue
	cvInstructions = defaultdict(dict)
	atcInstructions = defaultdict(int)
	cvRerouting = {}
	name2itemIds = defaultdict(list)
	readInstructions(config["CareVueDescriptions"],config["CareVueInputInstructions"],cvInstructions,name2itemIds)
	readExtraInstructions(config["ATCInstructions"],atcInstructions,config["CareVureReRouter"],cvRerouting,name2itemIds)

	# Read instruction files for MetaVision
	mvInstructions = defaultdict(dict)
	name2itemIds = defaultdict(list)
	readInstructions(config["MetaVisionDescriptions"],config["MetaVisionInputInstructions"],mvInstructions,name2itemIds)
	
	# Prepare output files
	outFileName = config["OutDir"] + "/" + config["DataFile"]
	outFile = open(outFileName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")

	logFileName = config["LogFile"]
	logger = open(logFileName,"w")
	
	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	# Loop and extract info
	n = len(ids)
	cnt = 0 
	dictionary = defaultdict(dict)

	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%50 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		# admissions
		admissions = []
		getAdmissions(config["DataDir"],id,admissions)
		
		# CareVue inputs
		writeCareVueInputs(config["DataDir"],id,newId,cvInstructions,cvRerouting,admissions,outFile,logger,dictionary,atcInstructions)
	
		# Metavision inputs
		writeMetaVisionInputs(config["DataDir"],id,newId,mvInstructions,admissions,outFile,logger,dictionary,atcInstructions)

	# Write Dictionary
	writeDictionary(outDict,dictionary)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 diagnosis file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=90)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_input_files(config,args.signalId)

