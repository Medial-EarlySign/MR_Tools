#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import sys
from collections import defaultdict
from subprocess import call
import os

stages = ("demographics","transfers","diagnosis","output","microbiology","procedures","drugs","process_drugs","input","process_input","lab_and_vital_signs", \
		  "process_lab_and_vitals","convert_config","load","post_process","transpose")
stageList = ",".join(stages)
root = os.environ['MR_ROOT']

def doIt(command,flag):
	print("%s"%" ".join(command))
	if (not flag):
		call(command)

# Parse cfg files
def getValue(cfgFile,targetKey):
	with open(cfgFile,"r") as file:
		for line in file:
			if (line[0] == "#" or line.isspace()):
				continue
			[key,value] = str.split(line.rstrip("\r\n"),"\t")
			if (key == targetKey):
				return value
	return ""

# Drugs post processing
def doDrugsPostProcess(path,dir,cfgPath,dummyFlag):

	cfgFile = dir + "/drugs.cfg"
	outDir = getValue(cfgFile,"OutDir")
	
	command = [path + "/process_drugs.py","--input",outDir + "/Drugs","--output",outDir + "/Drugs.Final","--log",outDir + "/drugs.log2","--units", cfgPath + "/Drugs.Units"]
	doIt(command,dummyFlag)

# Input post processing
def doInputPostProcess(path,dir,dummyFlag):

	cfgFile = dir + "/input.cfg"
	outDir = getValue(cfgFile,"OutDir")

	command = [path + "/process_input.py","--in",outDir + "/Input","--out",outDir + "/Input.Final","--log",outDir + "/input.log2"]
	doIt(command,dummyFlag)

# Parse signals list
def getSignalLists(signalFile,instFile1,instFile2,textSignals,numericSignals):

	# Read Instructions
	signalTypes = {}
	for fileName in (instFile1,instFile2):
		with open(fileName,"r") as file:
			for line in file:
				fields = str.split(line.rstrip("\r\n"),"\t")
				name = fields[-1].replace("BG_","").replace("LAB_","").replace("CHART_","")
				type = fields[-2]
				if (name in signalTypes.keys() and type != signalTypes[name]):
					raise ValueError("Type inconsistency for %s\n"%name)
				signalTypes[name] = type
	
	# Read Signals
	with open(signalFile,"r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			if (fields[0] == "SIGNAL"):
				name = fields[1]
				if (signalTypes[name] == "TEXT"):
					textSignals.append(name)
				else:
					numericSignals.append(name)
		
# Lab + Vitals postprocessing
def doLabAndVitalsPostProcess(path,dir,args,dummyFlag):

	cfgFile = dir + "/lab_and_vital_signs.cfg"
	outDir = getValue(cfgFile,"OutDir")

	# Extract textual and numeric signals
	textSignals = []
	numericSignals = []
	
	suffix = getValue(cfgFile,"Suffix")
	if (suffix == ""):
		signalsFile = outDir + "/signals.LabAndVitalSigns"
	else:
		signalsFile = outDir + "/signals." + suffix

	instFile1 = getValue(cfgFile,"LabInstructions")
	instFile2 = getValue(cfgFile,"ChartInstructions")

	getSignalLists(signalsFile,instFile1,instFile2,textSignals,numericSignals)
	
	# Processing
	for signal in numericSignals:
		command = [path + "/process_signal.py","--input",outDir + "/" + signal,"--output",outDir + "/" + signal + ".Fixed","--log",outDir + "/" + signal + ".log","--units",args.unitsFile, \
				   "--resolution",args.resFile,"--graph",outDir + "/" + signal + ".html"]
		doIt(command,dummyFlag)

	menuFile = outDir + "/Menu.html"
	with open(menuFile,"w") as html:
		html.write("<html>\n")
		for signal in numericSignals:
			html.write("<a href = \"%s.html\">%s<br></a>\n"%(signal,signal))
		html.write("</html>\n")

	for signal in textSignals:
		command = [path + "/process_textual_signal.py","--input",outDir + "/" + signal,"--output",outDir + "/" + signal + ".Fixed","--log",outDir + "/" + signal + ".log"]	
		doIt(command,dummyFlag)

	# Final processing
	for signal in numericSignals:
		command = [path + "/handle_lab_and_chart.py","--input",outDir + "/" + signal + ".Fixed", "--output",outDir + "/" + signal + ".Final","--log",outDir + "/" + signal + ".log2"]
		doIt(command,dummyFlag)

	if (not dummyFlag):
		for signal in textSignals:
			inFile = open(outDir + "/" + signal + ".Fixed","r")
			outFile = open(outDir + "/" + signal + ".Final","w")
			for line in inFile:
				outFile.write(line.replace("LAB_","").replace("CHART_","").replace("BG_",""))
			inFile.close()
			outFile.close()

# Convert config file
def generate_convert_config_file(dir,prefix,repDir,safeMode,dummyFlag):

	# Get outdir from demographics config file (to be changed)
	cfgFile = dir + "/demographics.cfg"
	outDir = getValue(cfgFile,"OutDir")

	if (not dummyFlag):
		fileName = dir + "/" + prefix + ".convert_config"
		with open(fileName,"w") as file:
			file.write("MODE\t3\n")
			file.write("SAFE_MODE\t1\n")
			file.write("TIMEUNIT\t6\n")
			file.write("DIR\t%s\n"%outDir)
			file.write("OUTDIR\t%s\n"%repDir)
			file.write("CONFIG\tmimic3.repository\n")
			file.write("RELATIVE\t1\n")
			file.write("SAFE_MODE\t%d\n"%safeMode)
			
			# Signals
			signalsFile = prefix + ".signals"
			outFileName = outDir + "/" + signalsFile
			dataFiles = ["Demographics","Transfers","Diagnosis","DrgCodes","Output","Microbiology","Procedures","Drugs.Final","Input.Final"]
			sig_suffices = ("demographics","transfers","diagnosis","output","micro","procedures","drugs","input","LabAndVitalSigns")
			with open(outFileName,"w") as outFile:
				outFile.write("####################################\n")
				outFile.write("# All Mimic-3 signals\n")
				outFile.write("####################################\n\n")
				for suffix in sig_suffices:
					fileName = outDir + "/signals." + suffix
					outFile.write("# Signals from %s\n"%suffix)
					with open(fileName,"r") as inFile:
						for line in inFile:
							if (line[0] == "#" or line.isspace()):
								continue
							outFile.write(line)
							if (suffix == "LabAndVitalSigns"):
								fields = str.split(line.rstrip("\r\n"),"\t")
								dataFiles.append(fields[1]+".Final")
								
			outFile.close()
			file.write("SIGNAL\t%s\n"%signalsFile)

			# Dictionaries
			dict_suffices = ("demographics","transfers","diagnosis","micro","procedures","drugs","input","LabAndVitalSigns")
			for suffix in dict_suffices:
				file.write("DICTIONARY\tdict.%s\n"%suffix)
				
			# Data Files
			for name in dataFiles:
				file.write("DATA\t%s\n"%name)

# Load repository
def load_repository(dir,prefix,dummyFlag):

	fileName = dir + "/" + prefix + ".convert_config"
	command = [root + "/Tools/Flow/Linux/Release/Flow","--rep_create","--convert_conf",fileName]	
	doIt(command,dummyFlag)

# Transform repository
def transpose_repository(dir,prefix,dummyFlag):
	# Extract repository config file from convert-config file
	fileName = dir + "/" + prefix + ".convert_config"

	with open(fileName,"r") as file:
		for line in file:
			[key,value] = str.split(line.rstrip("\r\n"),"\t")
			if (key == "OUTDIR"):
				outDir = value 
			elif (key == "CONFIG"):
				confFile = value
	file.close()
	
	command = [root + "/Tools/Flow/Linux/Release/Flow","--rep_create_pids","--rep",outDir + "/" + confFile]	
	doIt(command,dummyFlag)

# Add extra dictionaries
def post_process(dictsDir,dir,prefix,cfgPath,dummyFlag):
	
	# Extract repository config file from convert-config file
	fileName = dir + "/" + prefix + ".convert_config"

	with open(fileName,"r") as file:
		for line in file:
			[key,value] = str.split(line.rstrip("\r\n"),"\t")
			if (key == "OUTDIR"):
				outDir = value 
			elif (key == "CONFIG"):
				confFile = value
			elif (key == "DIR"):
				inDir = value
	file.close()
	
	# Get dictionaries already in config file
	fileName = outDir + "/" + confFile 

	allDicts = {}
	with open(fileName,"r") as file:
		for line in file:
			[key,value] = str.split(line.rstrip("\r\n"),"\t")
			if (key == "DICTIONARY"):
				allDicts[value] = 1
	file.close()	
	
	# Get extra dictionaries
	dicts = os.listdir(dictsDir)
	
	# Copy
	for dict in dicts:
		inFile = open(dictsDir + "/" + dict,"r")
		outFile = open(outDir + "/" + dict,"w")
		for line in inFile:
			outFile.write(line)
		inFile.close()
		outFile.close()
			
	# Add to configFile (if not existing already)
	repFileName = outDir + "/" + confFile 
	with open(repFileName,"a") as file:
		for dict in dicts:
			if (dict not in allDicts.keys()):
				file.write("DICTIONARY\t%s\n"%dict)
				allDicts[dict] = 1

	# Remove spaces from all dictionaries
	for dict in allDicts.keys():
		lines = []
		inFile = open(outDir + "/" + dict,"r")
		for line in inFile:
			line = line.rstrip("\r\n")
			if (line[:3] == "DEF" or line[:3] == "SET"):
				fields = str.split(line,"\t")
				fields[2] = fields[2].replace(" ","_")
				line = "\t".join(fields)
			lines.append(line)
		inFile.close()
		
		outFile = open(outDir + "/" + dict,"w")
		for line in lines:
			outFile.write("%s\n"%line)
		outFile.close()
			
	# Generate Prescribed Drugs Units file
	inFile = open(cfgPath + "/Drugs.Units","r") 
	units = {}
	for line in inFile:
		fields = str.split(line.rstrip("\r\n"),"\t")
		name = "%s\t%s"%(fields[0],fields[1])
		if (name not in units.keys() and float(fields[3])==1.0):
			units[name] = fields[2]
	
	outFile = open(outDir + "/PrescribedDrugsUnits","w")
	for name in units.keys():
		outFile.write("%s\t%s\n"%(name,units[name]))
		
	# Generate Administered Drugs Units file
	inFile = open(inDir + "/input.log2","r") 
	units = {}
	for line in inFile:
		fields = str.split(line.rstrip("\r\n"),"\t")
		if (fields[0] == "Units counter"):
			units[fields[2]] = fields[3]
			
	outFile = open(outDir + "/AdministeredDrugsUnits","w")
	for name in units.keys():
		outFile.write("%s\t%s\n"%(name,units[name]))
		
# ======= MAIN ======
parser = ap.ArgumentParser(description = "MIMIC-3 ETL")
parser.add_argument("--configDir",help="dir for configuration files")
parser.add_argument("--repDir",help="dir for repository files")
parser.add_argument("--start",help ="start stage [%s]"%stageList,default = "demographics")
parser.add_argument("--end",help="end stage [%s]"%stageList, default = "transpose")
parser.add_argument("--dummy",help="print without executing",action='store_true')
parser.add_argument("--unitsFile",help="units file for lab and vital signs",default=root+"/Tools/InPatientLoaders/mimic3/Configs/Signals.Units")
parser.add_argument("--resFile",help="resolutions file for lab and vital signs",default=root+"/Tools/InPatientLoaders/mimic3/Configs/Signals.Resolution")
parser.add_argument("--prefix",help="output files prefix", default = "mimic3")
parser.add_argument("--dictsDir",help="directory of extra dictionaries", default=root+"/Tools/InPatientLoaders/mimic3/Configs/ExtraDicts")
parser.add_argument("--safe_mode",help="value of SAFE_MODE flag in convert-config", default=1)
args = parser.parse_args() 

stageIdx = {stages[i]:i for i in range(len(stages))}
dummyFlag = args.dummy
safeMode = int(args.safe_mode)
dir = args.configDir

start = stageIdx[args.start]
end = stageIdx[args.end]
	
path = root + "/Tools/InPatientLoaders/mimic3/Scripts"
cfgPath = root + "/Tools/InPatientLoaders/mimic3/Configs"
for stage in stages:
	idx = stageIdx[stage]
	if (idx > end):
		quit(0)
	if (idx >= start):
		if (stage == "process_drugs"):
			doDrugsPostProcess(path,dir,cfgPath,dummyFlag)
		elif (stage == "process_input"):
			doInputPostProcess(path,dir,dummyFlag)
		elif (stage == "process_lab_and_vitals"):
			doLabAndVitalsPostProcess(path,dir,args,dummyFlag)
		elif (stage == "convert_config"):
			generate_convert_config_file(dir,args.prefix,args.repDir,safeMode,dummyFlag)
		elif (stage == "load"):
			load_repository(dir,args.prefix,dummyFlag)
		elif (stage == "post_process"):
			post_process(args.dictsDir,dir,args.prefix,cfgPath,dummyFlag)
		elif (stage == "transpose"):
			transpose_repository(dir,args.prefix,dummyFlag)
		else:
			command = [path + "/get_"+stage+".py","--config",dir + "/" + stage + ".cfg"]
			doIt(command,dummyFlag)
		


