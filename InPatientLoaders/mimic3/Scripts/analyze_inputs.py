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

def handleId(info,combs):
	orders = defaultdict(list)
	for line in info:
		orders[line[1]].append(line[0])
		
	for order in orders.keys():
		comb = {e : 1 for e in orders[order]}
		combs[",".join(sorted(comb.keys()))] += 1
		
def check_orders():
	# Read Instructions
	desc = {}
	with open("cv_input.more_than_100.desc","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			desc[fields[0]] = fields[1]
			
	# Read Data
	with open("/home/yaron/Mimic3/INPUTEVENTS_CV.csv","r") as file:
		reader = csv.reader(file)
		header = 1
		info = []
		prevId = -1
		idCount = 0 
		combs = defaultdict(int)
		for line in reader:
			if (header == 1):
				header = 0
			else:
				id = int(line[1])
				if (prevId != -1 and prevId != id):
					handleId(info,combs)
					info = []
					idCount += 1
					if (idCount%200 == 1):
						eprint("Handled %d stays (currently at %d)"%(idCount,id))
				prevId = id
				info.append((line[5],line[12]))
		handleId(info,combs)

		# Print
		for comb in combs:
			print("%s\t%d"%(comb,combs[comb]))

def get_combs(prefix = "cv"):

	if (prefix == "cv"):
		itemIdx = 5
		amountIdx = 6
		rateIdx = 8
		extraIdx = [18]
	else:
		itemIdx = 6
		amountIdx = 7
		rateIdx = 9
		extraIdx = [15,16]		

	# Read Instructions
	desc = {}
	fileName = prefix + "_input.more_than_100.desc"
	with open(fileName,"r") as file:
		for line in file:
			[itemId,description] = str.split(line.rstrip("\r\n").upper(),"\t")
			desc[itemId] = description.upper()
			
	# Read Data
	counter = defaultdict(int)
	nLines = 0
	fileName = "/home/yaron/Mimic3/INPUTEVENTS_" + prefix.upper() + ".csv"
	with open(fileName,"r") as file:
		reader = csv.reader(file)
		header = 1
		for line in reader:
			if (header == 1):
				header = 0
			else:
				item = line[itemIdx]
				if (line[amountIdx] != "" and not line[amountIdx].isspace()):
					amount = 1
				else:
					amount = 0
				amUnit = line[amountIdx+1]
				if (line[rateIdx] != "" and not line[rateIdx].isspace()):
					rate = 1
				else:
					rate = 0
				rtUnit = line[rateIdx+1]
				extraInfo = ",".join([line[idx] for idx in extraIdx])
				comb = "%s\t%d\t%s\t%s\t%s\t%s"%(item,amount,amUnit,rate,rtUnit,extraInfo)
				counter[comb] += 1
				
				nLines += 1
				if (nLines%250000 == 0):
					eprint(nLines)
				
	for comb in counter.keys():
		fields = str.split(comb,"\t")
		if (fields[0] in desc.keys()):
			print("%s\t%d\t%s"%(comb,counter[comb],desc[fields[0]]))
				
#"ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","CHARTTIME","ITEMID","AMOUNT","AMOUNTUOM","RATE","RATEUOM","STORETIME","CGID","ORDERID","LINKORDERID","STOPPED","NEWBOTTLE","ORIGINALAMOUNT","ORIGINALAMOUNTUOM","ORIGINALROUTE","ORIGINALRATE","ORIGINALRATEUOM","ORIGINALSITE"

def check(entry,syns,candidates,atcs):

	if (entry in syns.keys()):
		entry = syns[entry]
		
	foundGen = defaultdict(int)
	for rec in candidates:
		for field in rec:
			if (field == entry):
				foundGen[rec[-1]] += 1
	
	if (len(foundGen.keys())>0):
		found = sorted(foundGen.keys(),key = lambda x : foundGen[x], reverse=True)
		for cand in found:
			if (cand == entry):
				return cand
		
		if (len(found)==1 or foundGen[found[1]] < 0.1*foundGen[found[0]]):
			return found[0]
		else:
			eprint("Cannot decide on %s from %s"%(entry,",".join(found)))
			return ""
	else:
		if (entry in atcs.keys()):
			eprint("Add to Dict : %s\t%s"%(entry,atcs[entry]))
			return entry
		else :
			return ""
			
def handle_piggyback(list,info,syns,candidates,atcs):
	list = [n.rstrip(" ") for n in list]
	for name in list:
		conc = -1
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tPiggyback\tFluid"%name)
			else:
				for substances in info[name]:
					print("%s\tPiggyback\tDRUG\t%s\t%f"%(name,substances[0],substances[1]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found != ""):
				print("%s\tPiggyback\tDRUG\t%s\t%f"%(name,found,conc))
			else:
				eprint("Cannot find instructions for %s"%name)
	
def handle_push(list,info,syns,candidates,atcs):
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.replace("GTT","").rstrip(" ")
		if (name[-2:] == "-K"):
			name = name[:-2]
		if (name[:3] == "OR "):
			name = name[3:]
		if (name[:5] == "PACU "):
			name = name[5:]
		if (name[-6:] == " BOLUS"):
			name = name[:-6]
			
		if (name[-5:] == " DRIP"):
			name = name[:-5]
			type = "IV DRIP"
		else:
			type = "PUSH"
		
		conc = -1
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tPush\tFluid"%origin)
			else:		
				for substances in info[name]:
					if (type == "PUSH"):
						print("%s\tPush\tDRUG\t%s\t%f\t%s"%(origin,substances[0],substances[1],substances[2]))
					else:
						print("%s\tPush\tDRUG\t%s"%(origin,substances[0]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found != ""):
				if (type == "PUSH"):
					print("%s\tPush\tDRUG\t%s\t%f"%(origin,found,conc))
				else:
					print("%s\tPush\tDRUG\t%s"%(origin,found))
			else:
				eprint("Cannot find instructions for %s"%origin)		
			
def handle_infusions(list,info,syns,candidates,atcs):
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.replace("MCG/KG/MIN","").replace("CC/CC","").replace("CC/HR","").replace("INFUSION","").replace("GTT","").replace("(MG/H)","").rstrip(" ")
		
		if (name[-5:] == " DRIP"):
			name = name[:-5]
			type = "IV DRIP"
		else:
			type = "INFUSION"
		
		conc = -1
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tInfusion\tFluid"%origin)
			else:		
				for substances in info[name]:
					if (type == "INFUSION"):
						print("%s\tInfusion\tDRUG\t%s\t%f\t%s"%(origin,substances[0],substances[1],substances[2]))
					else:
						print("%s\tInfusion\tDRUG\t%s"%(origin,substances[0]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found != ""):
				if (type == "INFUSION"):
					print("%s\tInfusion\tDRUG\t%s\t%f"%(origin,found,conc))
				else:
					print("%s\tInfusion\tDRUG\t%s"%(origin,found))
			else:
				
				eprint("Cannot find instructions for %s"%origin)

def handle_gu(list,info,syns,candidates,atcs):
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.rstrip(" ").replace("_GU","")
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tGU\tFluid"%origin)
			else:			
				for substances in info[name]:		
					print("%s\tGU\tDRUG\t%s\t%f\t%s"%(origin,substances[0],substances[1],substances[2]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found != ""):
				print("%s\tGU\tDRUG\t%s\t%f"%(origin,found,-1))
			else:		
				eprint("Cannot find instructions for %s"%origin)

def handle_nasogastric(list,syns):
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.replace("NG","").replace("POWDER","PWDR").replace("PO","").replace("LIQUID","").rstrip(" ")
		if (name in syns.keys()):
			name = syns[name]
			
		if (name == "FREE WATER BOLUS"):
			print("%s\tNasogastric\tFluid"%origin)
		else:
			print("%s\tNasogastric\tNUTRITION\t%s"%(origin,name))
			
def handle_gastric_or_tube(list,syns):
	
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.replace("PG","").rstrip(" ")
		if (name in syns.keys()):
			name = syns[name]
		print("%s\tGastric/Tube\tNUTRITION\t%s"%(origin,name))
	
def handle_by_mouth(list,syns):
	list = [n.rstrip(" ") for n in list]
	for origin in list:
		name = origin.replace("NG","").replace("POWDER","PWDR").replace("PO","").rstrip(" ")
		if (name in syns.keys()):
			name = syns[name]
		print("%s\tBy Mouth\tNUTRITION\t%s"%(origin,name))

def handle_oral(list):

	list = [n.rstrip(" ") for n in list]
	for origin in list:
		if (origin == "PO INTAKE"):
			print("%s\tOral\tFluid"%origin)
		else:
			raise ValueError("Cannot handle Oral %s"%origin)
		
def handle_iv_drips(list,syns,candidates,atcs):

	list = [n.rstrip(" ") for n in list]			
			
	for orig in list:
		if (orig[-2:] == "-K"):
			entry = orig[:-2]
		else:
			entry = orig	
	
		found = check(entry,syns,candidates,atcs)
		if (found == ""):
			words = str.split(orig," ")
			for word in words:
				found = check(word,syns,candidates,atcs)
				if (found != ""):
					break
		if (found != ""):
			print("%s\tIV DRIP\tDRUG\t%s\t"%(orig,found))
		else:
			eprint("Cannot find %s anywhere"%orig)


def generate_instructions():

	# Read rerouting
	allowed = {"By Mouth":1, "Gastric/Feeding Tube":1, "Intravenous Infusion":1, "Intravenous Push":1, "Nasogastric":1}
	rerouter = {}
	with open("rerouter","r") as file:
		for line in file:
			[name,route] = str.split(line.rstrip("\r\n"),"\t")
			rerouter[name] = route
			if (route not in allowed.keys()):
				raise ValueError("Cannot reroute to \'%s\'"%route)
			
	# Read instructions for fluids
	info = {}
	with open("fluidsInstructions","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			entry = fields.pop(0)
			info[entry] = []
			for field in fields:
				subFields = str.split(field,":")
				if (len(subFields) > 1):
					if (len(subFields)==2):
						subFields.append("MG/ML")
					info[entry].append((subFields[0],float(subFields[1]),subFields[2]))
			
	# Read info
	names = defaultdict(dict)
	with open("BasicInfoForInputCV","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			route = fields[5]
			name = fields[7]
			
			if (route == "Drip"):
				route = "IV Drip"
			elif (route == "Intravenous"):
				route = "Intravenous Infusion"
			elif (route == "Oral or Nasogastric"):
				route = "Nasogastric"
			elif (route == "" or route.isspace()):
				clean = name.rstrip(" ")
				if (clean not in rerouter.keys()):
					raise ValueError("Cannot find rerouting for \'%s\'"%name)
				route = rerouter[clean]
			names[route][name] = 1
	
	# Read synonims
	syns = {}
	with open("drug_synonims","r") as file:
		for line in file:
			[orig,syn] = str.split(line.rstrip("\r\n"),"\t")
			syns[orig.upper()] = syn.upper()
	
	# Read generic names from prescriptions
	candidates = []
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/Prescriptions/comb2atc.ver6","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			candidates.append([fields[0],fields[1],fields[2],fields[6]])

	# read atcs
	atcs = {}
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/Prescriptions/full_atc","r") as file:
		for line in file:
			[atc,name] = str.split(line.rstrip("\r\n"),"\t")
			atcs[name] = atc			
			
	handle_iv_drips(names["IV Drip"].keys(),syns,candidates,atcs)
	handle_by_mouth(names["By Mouth"].keys(),syns)
	handle_gastric_or_tube(names["Gastric/Feeding Tube"].keys(),syns)
	handle_nasogastric(names["Nasogastric"].keys(),syns)
	handle_gu(names["GU"].keys(),info,syns,candidates,atcs)
	handle_infusions(names["Intravenous Infusion"].keys(),info,syns,candidates,atcs)
	handle_push(names["Intravenous Push"].keys(),info,syns,candidates,atcs)
	handle_piggyback(names["IV Piggyback"].keys(),info,syns,candidates,atcs)
	handle_oral(names["Oral"].keys())
	

############################################################
def handle_mv_drips(list,info,syns,candidates,atcs):

	for orig in list:
		name=orig.replace("-K","").replace("(CRRT)","").rstrip(" ")
		
		# Special care
		if (orig == "CALCIUM GLUCONATE (CRRT)"):
			# Given in grams
			print("%s\tIV DRIP\tDRUG\t%s\t%f\tMG/MG"%(orig,"CALCIUM",40.0/430))
			print("%s\tIV DRIP\tDRUG\t%s\t%f\tMG/MG"%(orig,"GLUCONATE",390.0/430))
			continue
		elif (orig == "KCL (CRRT)"):
			# Given in meq
			print("%s\tIV DRIP\tDRUG\t%s\t%f\tMG/MEQ"%(orig,"POTASSIUM",39.0))
			print("%s\tIV DRIP\tDRUG\t%s\t%f\tMG/MEQ"%(orig,"CHLORIDE",35.0))
			continue
		
		# Check at info
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tIV DRIP\tFluid"%orig)
			elif (len(info[name]) == 1 and (info[name][0][1] == 1 or info[name][0][1] == -1)):
				print("%s\tIV DRIP\tDRUG\t%s"%(orig,info[name][0][0]))
			else:		
				for substances in info[name]:
					print("%s\tIV DRIP\tDRUG\t%s\t%f\t%s"%(orig,substances[0],substances[1],substances[2]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found == ""):
				words = str.split(orig," ")
				for word in words:
					found = check(word,syns,candidates,atcs)
					if (found != ""):
						break
			if (found != ""):
				print("%s\tIV DRIP\tDRUG\t%s"%(orig,found))
			else:
				eprint("Cannot find %s anywhere"%orig)
		
def handle_mv_fluids(list,info,syns,candidates,atcs):		

	for origin in list:
		if (origin != "SODIUM BICARBONATE 8.4% (AMP)"):
			matchObj = re.match(r'(.*)\s*\(.*\)',origin, re.M|re.I)
			if (matchObj):
				name = matchObj.group(1).rstrip(" ")
			else:
				name = origin
		else:
			name = origin
			
		matchObj = re.match(r'(OR|PACU) (.*) INTAKE',origin, re.M|re.I)
		if (matchObj):
			name = matchObj.group(2)
			
		if (name in syns.keys()):
			name = syns[name]
			
		conc = -1
		if (name in info.keys()):
			if (len(info[name]) == 0):
				print("%s\tInfusion\tFluid"%origin)
			else:		
				for substances in info[name]:
					print("%s\tInfusion\tDRUG\t%s\t%f\t%s"%(origin,substances[0],substances[1],substances[2]))
		else:
			found = check(name,syns,candidates,atcs)
			if (found != ""):
				print("%s\tInfusion\tDRUG\t%s\t%f"%(origin,found,conc))
			else:
				eprint("Cannot find instructions for %s"%origin)
		
def handle_mv_nutrition(list,syns):
	
	for origin in list:
		matchObj = re.match(r'(.*)\s*\((.*)\)',origin, re.M|re.I)
		if (matchObj):
			if (matchObj.group(2) == "FULL"):
				name = matchObj.group(1)
			else:
				name = matchObj.group(2) + " STR " + matchObj.group(1)
		else:
			name = origin	
		name = name.rstrip(" ")
		if (name in syns.keys()):
			name = syns[name]
		print("%s\tEnteral\tNUTRITION\t%s"%(origin,name))
		
def handle_mv_intake(list,info,syns,candidates,atcs):
	
	for origin in list:
		print("%s\tGastric/Tube\tFluid"%origin)
		
def handle_mv_non_iv_drugs(list,info,syns,candidates,atcs):
	
	for origin in list:
		matchObj = re.match(r'(.*)\s*\(.*\)',origin, re.M|re.I)
		if (matchObj):
			name = matchObj.group(1).rstrip(" ")
		else:
			name = origin
			
		if (re.match(r'^INSULIN -',origin, re.M|re.I)):
			name = "INSULIN"
			
		if (name in syns.keys()):
			name = syns[name]
			
		found = check(name,syns,candidates,atcs)
		if (found != ""):
			print("%s\tNON_IV\tDRUG\t%s"%(origin,found))
		else:
			eprint("Cannot find instructions for %s"%origin)
		
def generate_mv_instructions():

	# Read instructions for fluids
	info = {}
	with open("fluidsInstructions","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			entry = fields.pop(0)
			info[entry] = []
			for field in fields:
				subFields = str.split(field,":")
				if (len(subFields) > 1):
					if (len(subFields)==2):
						subFields.append("MG/ML")
					info[entry].append((subFields[0],float(subFields[1]),subFields[2]))
			
	# Read info
	names = defaultdict(dict)
	with open("BasicInfoForInputMV","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			type = fields[5]
			name = fields[7]
			names[type][name] = 1
	
	# Read synonims
	syns = {}
	with open("drug_synonims","r") as file:
		for line in file:
			[orig,syn] = str.split(line.rstrip("\r\n"),"\t")
			syns[orig.upper()] = syn.upper()
	
	# Read generic names from prescriptions
	candidates = []
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/Prescriptions/comb2atc.ver6","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			candidates.append([fields[0],fields[1],fields[2],fields[6]])

	# read atcs
	atcs = {}
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/Prescriptions/full_atc","r") as file:
		for line in file:
			[atc,name] = str.split(line.rstrip("\r\n"),"\t")
			atcs[name] = atc			
	
	handle_mv_drips(names["01-Drips,02-Fluids (Crystalloids)"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["02-Fluids (Crystalloids),Additive (Crystalloid)"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["03-IV Fluid Bolus,"].keys(),info,syns,candidates,atcs)	
	handle_mv_fluids(names["04-Fluids (Colloids),"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["05-Med Bolus,"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["07-Blood Products,"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["08-Antibiotics (IV),02-Fluids (Crystalloids)"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["10-Prophylaxis (IV),02-Fluids (Crystalloids)"].keys(),info,syns,candidates,atcs)	
	handle_mv_fluids(names["12-Parenteral Nutrition,Additives (PN)"].keys(),info,syns,candidates,atcs)
	handle_mv_fluids(names["16-Pre Admission,"].keys(),info,syns,candidates,atcs)
	handle_mv_nutrition(names["13-Enteral Nutrition,Additives (EN)"].keys(),syns)
	handle_mv_intake(names["14-Oral/Gastric Intake,"].keys(),info,syns,candidates,atcs)
	handle_mv_non_iv_drugs(names["06-Insulin (Non IV),"].keys(),info,syns,candidates,atcs)
	handle_mv_non_iv_drugs(names["09-Antibiotics (Non IV),"].keys(),info,syns,candidates,atcs)
	handle_mv_non_iv_drugs(names["11-Prophylaxis (Non IV),"].keys(),info,syns,candidates,atcs)

# ======= MAIN ======
## Main
mode = sys.argv[1]

if (mode == "check_orders"):
	check_orders()
elif (mode == "get_combs"):
	if (len(sys.argv)==2):
		get_combs()
	else:
		get_combs(sys.argv[2])
elif (mode == "instructions"):
	generate_instructions()
elif (mode == "mv_instructions"):
	generate_mv_instructions()

