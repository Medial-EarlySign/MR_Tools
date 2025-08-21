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
		
	required = ["IdsFile","OutDir","DataDir","Diagnosis","DiagnosisItems","LogFile"]
	for field in required:
		if (field not in config.keys()):
			raise ValueError("Cannot find required field \'%s\' in config file \'%s\'\n"%(field,name))

	defaults = {"DiagnosisFile":"Diagnosis","DrgFile":"DrgCodes","Suffix":"diagnosis"}
	for key in defaults.keys():
		if (key not in config.keys()):
			config[key] = defaults[key]
			
	return config

# Read items map
def read_d_items(fileName,desc):
	
	id = ""
	with open(fileName,"r") as file:
		reader = csv.reader(file)
		header = reader.next()
		cols = {header[i] : i for i in range(len(header))}
		
		for row in reader:
			desc[row[cols["ITEMID"]]] = row[cols["LABEL"]]
			
# Read Diagnosis item ids in ChartEvents
def read_diagnosis_items(fileName):
	items = {}
	with open(fileName,"r") as file:
		for line in file:
			[item,desc] = str.split(line.rstrip("\r\n"),"\t")
			items[int(item)] = 1
	return items
			
# Read Diagnosis Descriptions
def read_d_diagnosis(fileName,desc):
	
	with open(fileName,"r") as file:
		reader = csv.reader(file)
		header = reader.next()
		cols = {header[i] : i for i in range(len(header))}
		
		for row in reader:
			desc["ICD9:"+row[cols["ICD9_CODE"]]] = row[cols["SHORT_TITLE"]]
		
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
def parseICD9(code):

	if (code == ""):
		return {"num":-1, "alpha":"NULL"}

	matchObj = re.match(r'^(V|E)(\S+)$',code, re.M|re.I)
	if (matchObj):
		num = int(matchObj.group(2))
		alpha = matchObj.group(1)
	else:
		num = int(code)
		alpha = "NULL"

	if (num < 1000):
		return {"num":num, "alpha":"NULL"}
	elif (num < 10000):
		return {"num":num/10.0, "alpha":"NULL"}
	else:
		return {"num":num/100.0, "alpha":"NULL"}

def getICD9Codes(dir,inId,icd9):
	
	lines,header = readers.read_lines(dir,"DIAGNOSES_ICD",inId)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		adminId = line[header["HADM_ID"]]
		code = line[header["ICD9_CODE"]]
		icd9[adminId].append(code)
		
# Handle DRG 
def getDRGCodes(dir,inId,drg,desc):
	
	lines,header = readers.read_lines(dir,"DRGCODES",inId)
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
		
		adminId = line[header["HADM_ID"]]
		code = line[header["DRG_CODE"]]
		dsc = line[header["DESCRIPTION"]]
		drg[adminId].append(code)
		desc["DRG:"+code] = dsc
		
# Do Elixhauser
def getElixhauser(icd9,drg,elix,icd9Parser):

	for adminId in drg.keys():
		drgCodeTypes = defaultdict(int)
		for drgCode in drg[adminId]:
			drgCodeTypes["Cardiac"] +=  ((drgCode >= 103 and drgCode <= 108) or (drgCode >= 110 and drgCode <= 112) or (drgCode >= 115 and drgCode <= 118) or (drgCode >= 120 and drgCode <= 127) \
											or drgCode == 129 or (drgCode >= 132 and drgCode <= 133) or (drgCode >= 135 and drgCode <= 143)) 
			drgCodeTypes["Renal"] += ((drgCode >= 302 and drgCode <= 305) or (drgCode >= 315 and drgCode <= 333)) 
			drgCodeTypes["Liver"] += ((drgCode >= 199 and drgCode <= 202) or (drgCode >= 205 and drgCode <= 208)) 
			drgCodeTypes["LeukemiaLymphoma"] += ((drgCode >= 400 and drgCode <= 414) or drgCode == 473 or drgCode == 492) 
			drgCodeTypes["Cancer"] += (drgCode == 10 or drgCode == 11 or drgCode == 64 or drgCode == 82 or drgCode == 172 or drgCode == 173 or drgCode == 199 or drgCode == 203 or drgCode == 239 \
										or (drgCode >= 257 and drgCode <= 260) or drgCode == 274 or drgCode == 275 or drgCode == 303 or drgCode == 318 or drgCode == 319 or drgCode == 338 \
										or drgCode == 344 or drgCode == 346 or drgCode == 347 or drgCode == 354 or drgCode == 355 or drgCode == 357 or drgCode == 363 or drgCode == 366 \
										or drgCode == 367 or (drgCode >= 406 and drgCode <= 414))
			drgCodeTypes["Copd"] += (drgCode == 88) 
			drgCodeTypes["PeripherialVascular"] += (drgCode >= 130 and drgCode <= 131) 
			drgCodeTypes["HyperTension"] += (drgCode == 134) 
			drgCodeTypes["CerebroVascular"] += (drgCode >= 14 and drgCode <= 17) 
			drgCodeTypes["NervousSystem"] += (drgCode >= 1 and drgCode <= 35) 
			drgCodeTypes["Asthma"] += (drgCode >= 96 and drgCode <= 98) 
			drgCodeTypes["Diabetes"] += (drgCode >= 294 and drgCode <= 295) 
			drgCodeTypes["Thyroid"] += (drgCode == 290) 
			drgCodeTypes["Endocrine"] += (drgCode >= 300 and drgCode <= 301) 
			drgCodeTypes["KidneyTransplant"] += (drgCode == 302) 
			drgCodeTypes["RenalFailureDialysis"] += (drgCode >= 316 and drgCode <= 317) 
			drgCodeTypes["Endocrine"] += (drgCode >= 300 and drgCode <= 301) 
			drgCodeTypes["GiHemorrhageUlcer"] += (drgCode >= 174 and drgCode <= 178) 
			drgCodeTypes["HIV"] += (drgCode >= 488 and drgCode <= 490) 
			drgCodeTypes["ConnectiveTissue"] += (drgCode >= 240 and drgCode <= 241) 
			drgCodeTypes["Coagulation"] += (drgCode == 397) 
			drgCodeTypes["ObesityProcedure"] += (drgCode == 288) 
			drgCodeTypes["NutritionMetabolic"] += (drgCode >= 396 and drgCode <= 398) 
			drgCodeTypes["Anemia"] += (drgCode >= 395 and drgCode <= 396) 
			drgCodeTypes["AlcoholDrug"] += (drgCode >= 433 and drgCode <= 437) 
			drgCodeTypes["Psychoses"] += (drgCode == 430) 
			drgCodeTypes["Depression"] += (drgCode == 426) 
	   
		adminElix = {}
		for code in icd9[adminId]:
			if (code not in icd9Parser.keys()):
				icd9Parser[code] = parseICD9(code)
				
			num = icd9Parser[code]["num"]
			alpha = icd9Parser[code]["alpha"]

			if (drgCodeTypes["Cardiac"]==0 and ((alpha == "NULL") and (num == 398.91 or num == 402.11 or num == 402.91 or num == 404.11 or num == 404.13 or num == 404.91 or num == 404.93 or \
				(num >= 428 and num <= 428.9)))):
					adminElix["ELIXHAUSER:CONGESTIVE_HEART_FAILURE"] = 1
			if (drgCodeTypes["Cardiac"]==0 and (((alpha == "NULL") and (num == 426.1 or num == 426.11 or num == 426.13 or num == 427 or num == 427.2 or num == 427.31 or num == 427.6 or \
				num == 427.9 or num == 785 or (num >= 426.2 and num <= 426.53) or (num >= 426.6 and num <= 426.89))) or ((alpha == "V") and  (num == 45 or num == 53.3)))):
				adminElix["ELIXHAUSER:CARDIAC_ARRHYTHMIAS"] = 1
			if (drgCodeTypes["Cardiac"]==0 and (((alpha == "NULL") and (num >= 93.2 and num <= 93.24) or (num >= 394 and num <= 397.1) or (num >= 424 and num <= 424.91) or \
				(num >= 746.3 and num <= 746.6)) or ((alpha == "V") and (num == 42.2 or num == 43.3)))):
				adminElix["ELIXHAUSER:VALVULAR_DISEASE"] = 1
			if (drgCodeTypes["Cardiac"]==0 and (((alpha == "NULL") and (num >= 416 and num <= 416.9) or num == 417.9))):
				adminElix["ELIXHAUSER:PULMONARY_CIRCULATION"] = 1
			if (drgCodeTypes["PeripherialVascular"] == 0 and (((alpha == "NULL") and ((num >= 440 and num <= 440.9) or num == 441.2 or num == 441.4 or num == 441.7 or \
				num == 441.9 or (num >= 443.1 and num <= 443.9) or num == 447.1 or num == 557.1 or num == 557.9)) or ((alpha == "V") and (num == 43.4)))): 
				adminElix["ELIXHAUSER:PERIPHERAL_VASCULAR"] = 1
			if (drgCodeTypes["HyperTension"] == 0 and drgCodeTypes["Cardiac"]==0 and drgCodeTypes["Renal"]==0 and ((alpha == "NULL") and (num == 401.1 or num == 401.9 or num == 402.1 or \
				num == 402.9 or num == 404.1 or num == 404.9 or num == 405.11 or num == 405.19 or num == 405.91 or num == 405.99))):
				adminElix["ELIXHAUSER:HYPERTENSION"] = 1
			if (drgCodeTypes["CerebroVascular"] == 0 and ((alpha == "NULL") and ((num >= 342 and num <= 342.12) or (num >= 342.9 and num <= 344.9)))):
				adminElix["ELIXHAUSER:PARALYSIS"] = 1
			if (drgCodeTypes["NervousSystem"]==0 and ((alpha == "NULL") and (num == 331.9 or num == 332 or num == 333.4 or num == 333.5 or (num >= 334 and num <= 335.9) or num == 340 \
				or (num >= 341.1 and num <= 341.9) or (num >= 345 and num <= 345.11) or (num >= 345.5 and num <= 345.51) or (num >= 345.8 and num <= 345.91) or num == 348.1 or num == 348.3 or \
				num == 780.3 or num == 784.3))):
				adminElix["ELIXHAUSER:OTHER_NEUROLOGICAL"] = 1
			if (drgCodeTypes["Copd"] == 0 and drgCodeTypes["Asthma"] == 0 and ((alpha == "NULL") and ((num >= 490 and num <= 492.8) or (num >= 493 and num <= 493.91) or num == 494 or \
				(num >= 495 and num <= 505) or num == 506.4))):
				adminElix["ELIXHAUSER:CHRONIC_PULMONARY"] = 1
			if (drgCodeTypes["Diabetes"] == 0 and ((alpha == "NULL") and ((num >= 250 and num <= 250.33)))):
				adminElix["ELIXHAUSER:DIABETES_UNCOMPLICATED"] = 1
			if (drgCodeTypes["Diabetes"] == 0 and ((alpha == "NULL") and ((num >= 250.4 and num <= 250.73) or (num >= 250.9 and num <= 250.93)))):
				adminElix["ELIXHAUSER:DIABETES_COMPLICATED"] = 1
			if (drgCodeTypes["Thyroid"]==0 and drgCodeTypes["Endocrine"]==0 and ((alpha == "NULL") and ((num >= 243 and num <= 244.2) or num == 244.8 or num == 244.9))):
				adminElix["ELIXHAUSER:HYPOTHYROIDISM"] = 1
			if (drgCodeTypes["KidneyTransplant"] == 0 and drgCodeTypes["RenalFailureDialysis"]==0 and (((alpha == "NULL") and (num == 403.11 or num == 403.91 or num == 404.12 or \
				num == 404.92 or num == 585 or num == 586)) or ((alpha == "V") and (num == 42 or num == 45.1 or num == 56 or num == 56.8)))):
				adminElix["ELIXHAUSER:RENAL_FAILURE"] = 1
			if (drgCodeTypes["Liver"] == 0 and (((alpha == "NULL") and (num == 70.32 or num == 70.33 or num == 70.54 or num == 456 or num == 456.1 or num == 456.2 or num == 456.21 or \
				num == 571 or num == 571.2 or num == 571.3 or (num >= 571.4 and num <= 571.49) or num == 571.5 or num == 571.6 or num == 571.8 or num == 571.9 or num == 572.3 or \
				num == 572.8)) or ((alpha == "V") and (num == 42.7)))):
				adminElix["ELIXHAUSER:LIVER_DISEASE"] = 1
			if (drgCodeTypes["GiHemorrhageUlcer"]==0 and (((alpha == "NULL") and (num == 531.7 or num == 531.9 or num == 532.7 or num == 532.9 or num == 533.7 or num == 533.9 or \
				num == 534.7 or num == 534.9)) or ((alpha == "V") and (num == 12.71)))):
				adminElix["ELIXHAUSER:PEPTIC_ULCER"] = 1
			if (drgCodeTypes["HIV"] == 0 and ((alpha == "NULL") and ((num >= 42 and num <= 44.9)))):
				adminElix["ELIXHAUSER:AIDS"] = 1
			if (drgCodeTypes["LeukemiaLymphoma"] == 0 and (((alpha == "NULL") and ((num >= 200 and num <= 202.38) or (num >= 202.5 and num <= 203.01) or (num >= 203.8 and num <= 203.81) or \
				num == 238.6 or num == 273.3)) or ((alpha == "V") and (num == 10.71 or num == 10.72 or num == 10.79)))):
				adminElix["ELIXHAUSER:LYMPHOMA"] = 1
			if (drgCodeTypes["Cancer"] == 0 and ((alpha == "NULL") and ((num >= 196 and num <= 199.1)))):
				adminElix["ELIXHAUSER:METASTATIC_CANCER"] = 1
			if (drgCodeTypes["Cancer"] == 0 and (((alpha == "NULL") and ((num >= 140 and num <= 172.9) or (num >= 174 and num <= 175.9) or (num >= 179 and num <= 195.8))) or \
				((alpha == "V") and (num >= 10 and num <= 10.9)))):
				adminElix["ELIXHAUSER:SOLID_TUMOR"] = 1
			if (drgCodeTypes["ConnectiveTissue"] == 0 and (((alpha == "NULL") and (num == 701 or (num >= 710 and num <= 710.9) or (num >= 714 and num <= 714.9) or \
				(num >= 720 and num <= 720.9) or num == 725)))):
				adminElix["ELIXHAUSER:RHEUMATOID_ARTHRITIS"] = 1
			if (drgCodeTypes["Coagulation"] == 0 and ((alpha == "NULL") and ((num >= 2860 and num <= 2869) or num == 287.1 or (num >= 287.3 and num <= 287.5)))):
				adminElix["ELIXHAUSER:COAGULOPATHY"] = 1
			if (drgCodeTypes["ObesityProcedure"] == 0 and drgCodeTypes["NutritionMetabolic"] == 0 and ((alpha == "NULL") and (num == 278))):
				adminElix["ELIXHAUSER:OBESITY"] = 1
			if (drgCodeTypes["drgNutritionMetabolic"] == 0 and ((alpha == "NULL") and ((num >= 260 and num <= 263.9)))):
				adminElix["ELIXHAUSER:WEIGHT_LOSS"] = 1
			if (drgCodeTypes["drgNutritionMetabolic"] == 0 and ((alpha == "NULL") and ((num >= 276 and num <= 276.9)))):
				adminElix["ELIXHAUSER:FLUID_ELECTROLYTE"] = 1
			if (drgCodeTypes["Anemia"] == 0 and ((alpha == "NULL") and (num == 2800))):
				adminElix["ELIXHAUSER:BLOOD_LOSS_ANEMIA"] = 1
			if (drgCodeTypes["Anemia"] == 0 and ((alpha == "NULL") and ((num >= 280.1 and num <= 281.9) or num == 285.9))):
				adminElix["ELIXHAUSER:DEFICIENCY_ANEMIAS"] = 1
			if (drgCodeTypes["AlcoholDrug"] == 0 and (((alpha == "NULL") and (num == 291.1 or num == 291.2 or num == 291.5 or num == 291.8 or num == 291.9) or \
				(num >= 303.9 and num <= 303.93) or (num >= 305 and num <= 305.03)) or ((alpha == "V") and (num == 113)))):
				adminElix["ELIXHAUSER:ALCOHOL_ABUSE"] = 1
			if (drgCodeTypes["AlcoholDrug"] == 0 and ((alpha == "NULL") and (num == 292 or (num >= 292.82 and num <= 292.89) or num == 292.9 or (num >= 304 and num <= 304.93) or \
				(num >= 305.2 or num <= 305.93)))): 
				adminElix["ELIXHAUSER:DRUG_ABUSE"] = 1
			if (drgCodeTypes["Psychoses"] == 0 and ((alpha == "NULL") and ((num >= 295 and num <= 298.9) or (num >= 299.1 and num <= 299.11)))):
				adminElix["ELIXHAUSER:PSYCHOSES"] = 1
			if (drgCodeTypes["Depression"] == 0 and ((alpha == "NULL") and (num == 300.4 or num == 301.12 or num == 309 or num == 309.1 or num == 311))):
				adminElix["ELIXHAUSER:DEPRESSION"] = 1
		elix[adminId] = adminElix.keys()
	
# Look in ChartEvents
def getChartDiagnosis(dir,inId,items,diag_desc,chartDiagnosis,logger):

	lines,header = readers.read_lines(dir,"CHARTEVENTS",inId) 
		
	done = {}
	for line in lines:
		id = int(line[header["SUBJECT_ID"]])
		if (id != inId):
			raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))

		itemId = int(line[header["ITEMID"]])
		if (itemId not in  items.keys()):
			continue
		
		time = line[header["CHARTTIME"]]
		if (time != ""):
			diag = line[header["VALUE"]].replace('\"','') ;
			if (diag.isspace()):
				logger.write("Cannot find value for %s at %d at %s"%(signalName,id,time))
			else:
				chartDiagnosis.append([time,diag])

# Write Diagnosis File
def writeDiagnosis(id,newId,diagFile,icd9,elix,chart,dischargeTimes,dictionary):

	# From Chart
	for entry in chart:
		name = "CHART:" + entry[1]
		diagFile.write("%s\tDIAGNOSIS\t%s\t%s\tcurrent\n"%(newId,entry[0],name))
		dictionary["DIAGNOSIS"][name] = 1
		
	# Per Admission
	for adminId in icd9.keys():
		if (adminId not in dischargeTimes.keys()):
			raise ValueError("Cannot find discharge time for %s/%s\n"%(id,adminId))
		time = dischargeTimes[adminId]
		
		for code in icd9[adminId]:
			name = "ICD9:" + code
			diagFile.write("%s\tDIAGNOSIS\t%s\t%s\tadmission\n"%(newId,time,name))
			dictionary["DIAGNOSIS"][name] = 1
			
		for code in elix[adminId]:
			diagFile.write("%s\tDIAGNOSIS\t%s\t%s\tpast\n"%(newId,time,code))
			dictionary["DIAGNOSIS"][code] = 1

# Write DrgCodes File			
def writeDRG(id,newId,drgFile,drg,dischargeTimes,dictionary):

	for adminId in drg.keys():
		if (adminId not in dischargeTimes.keys()):
			raise ValueError("Cannot find discharge time for %s/%s\n"%(id,adminId))
		time = dischargeTimes[adminId]
		
		for code in drg[adminId]:
			name = "DRG:" + code
			drgFile.write("%s\tDRG\t%s\t%s\n"%(newId,time,name))
			dictionary["DRG"][name] = 1

# Write dictionary
def writeDictionary(dictFile,dictionary,desc):

	dictFile.write("#####################################################################\n")
	dictFile.write("# Dictionary for diagnosis\n")
	dictFile.write("#####################################################################\n")
	
	index = 1000
	dictFile.write("SECTION\tDIAGNOSIS,DRG\n")
	for signal in ("DIAGNOSIS","DRG"):
		for key in dictionary[signal].keys():
			dictFile.write("DEF\t%d\t%s\n"%(index,key))
			if (key in desc.keys()):
				dictFile.write("DEF\t%d\t%s:%s\n"%(index,key,desc[key]))
			index +=1
	
# Write Signals File
def writeSignalsFile(signalsFile,signalId):

	signalsFile.write("#####################################################################\n")
	signalsFile.write("# Signals for diagnosis + drg\n"										   )
	signalsFile.write("#####################################################################\n")
	
	signalsFile.write("SIGNAL\tDIAGNOSIS\t%d\t6\tICD9 + calculated Elixhauser codes (past = Comorbidities, admission = given at the end of admission)\t11\n"%signalId)
	signalId += 1
	signalsFile.write("SIGNAL\tDRG\t%d\t1\tDisease Related Group (given at the end of admission)\t1\n"%signalId)

def generate_diag_files(config,signalId):

	# Read required ids
	eprint("Reading ids from \'%s\'\n"%config["IdsFile"])
	
	ids = []
	with open(config["IdsFile"],"r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append((int(id),int(newId)))
	eprint("Read %d ids from \'%s\'"%(len(ids),config["IdsFile"]))

	# Prepare output files
	diagFileName = config["OutDir"] + "/" + config["DiagnosisFile"]
	diagFile = open(diagFileName,"w")
	
	drgFileName = config["OutDir"] + "/" + config["DrgFile"]
	drgFile = open(drgFileName,"w")	

	outDictName = config["OutDir"] + "/dict." + config["Suffix"]
	outDict = open(outDictName,"w")
	
	signalsFileName = config["OutDir"] + "/signals." + config["Suffix"]
	signalsFile = open(signalsFileName,"w")
	
	logFileName = config["LogFile"]
	logger = open(logFileName,"w")	
	
	# Read descriptions
	desc = {}
	read_d_diagnosis(config["Diagnosis"],desc)
	
	diag_desc = {}
	read_d_items(config["Items"],diag_desc)
	
	items = read_diagnosis_items(config["DiagnosisItems"])
	
	# Loop and extract info
	dictionary = {"DIAGNOSIS":{"admission":1, "past":1, "current":1},"DRG":{}}
	icd9Parser = {}	
	
	n = len(ids)
	cnt = 0 
	for rec in ids:
		(id,newId) = rec
		
		cnt += 1
		if (cnt%50 == 0):
			print("Work on subject %d : %d/%d"%(id,cnt,n))
		(id,newId) = rec
		
		dischargeTimes = {}
		getDischargeTime(config["DataDir"],id,dischargeTimes)
		
		# ICD9
		icd9 = defaultdict(list)
		getICD9Codes(config["DataDir"],id,icd9)

		# DRG-Codes
		drg = defaultdict(list)
		getDRGCodes(config["DataDir"],id,drg,desc)

		# Elixhauser
		elix = defaultdict(list)
		getElixhauser(icd9,drg,elix,icd9Parser)
	
		chartDiagnosis = []
		getChartDiagnosis(config["DataDir"],id,items,diag_desc,chartDiagnosis,logger)
		
		# Write
		writeDiagnosis(id,newId,diagFile,icd9,elix,chartDiagnosis,dischargeTimes,dictionary)
		writeDRG(id,newId,drgFile,drg,dischargeTimes,dictionary)
	
	# Generate Dictionary
	writeDictionary(outDict,dictionary,desc)
	
	# Generate Signals File
	writeSignalsFile(signalsFile,signalId)
	
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 diagnosis file for loading")
parser.add_argument("--config",help="config file")
parser.add_argument("--signalId", help ="first id of generated signal",default=30)

args = parser.parse_args() 

# Read Config
config = read_config_file(args.config)

# Generate files
generate_diag_files(config,args.signalId)

