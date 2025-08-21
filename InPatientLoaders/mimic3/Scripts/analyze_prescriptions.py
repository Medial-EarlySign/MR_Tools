#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import re
import sys
from collections import defaultdict
from indexer import *
import random


def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

def analyze_combs(mode):
	# Read
	combs = []
	
	if (mode == "cluster" or mode == "find_multiple" or mode == "unite"):
		combsFile = "combs"
	elif (mode == "base_cluster" or mode == "find_base_multiple" or mode == "find_base_unite"):
		combsFile = "base_combs"
	
	with open(combsFile,"r") as file:
		for line in file:
			combs.append(line.rstrip("\r\n"))
	nFields = len(str.split(combs[0],"\t")) - 1
	
	# cluster
	clusters = [{} for i in range(nFields)]
	iCluster = 0
	allClusters = []
	
	for comb in combs:
		combClusters = {}
		fields = [f.replace("*NF*","").rstrip(" ").lstrip(" ") for f in str.split(comb,"\t")]
		
		# Start with drug name
		if (fields[0] != "" and (not fields[0].isspace()) and fields[0] in clusters[0].keys()):
			combClusters[clusters[0][fields[0]]] = 1
		
		# Otherwise ...
		if (len(combClusters.keys()) == 0):
			for i in range(1,nFields):
				if (fields[i] != "" and (not fields[i].isspace()) and fields[i] in clusters[i].keys()):
					combClusters[clusters[i][fields[i]]] = 1

		if (len(combClusters.keys()) == 0):
#			eprint("new cluster for %s"%comb)
			combClusters[iCluster] = 1
			iCluster += 1
		
		basicCluster = combClusters.keys()[0]
		allClusters.append(combClusters.keys())
		for i in range(nFields):
			if (fields[i] != "" and (not fields[i].isspace()) and fields[i] not in clusters[i].keys()):
				clusters[i][fields[i]] = basicCluster
			
	cluster2combs = defaultdict(list)		
	for i in range(len(combs)):
		if (mode == "cluster" or mode == "base_cluster"):
			print("%s\t%s"%(",".join("%d"%k for k in allClusters[i]),combs[i]))
		for cluster in allClusters[i]:
			cluster2combs[cluster].append(i)
	
	
	if (mode == "cluster" or mode == "base_cluster"):
		return
	
	# Find clusters with multiple generic names
	if (mode == "find_multiple"):
		minNumForUnion = 10
		generic2cluster = defaultdict(list)
		for cluster in cluster2combs.keys():
			generics=defaultdict(int)
			for i in cluster2combs[cluster]:
				fields = [f.replace("*NF*","").rstrip(" ").lstrip(" ") for f in str.split(combs[i],"\t")]
				if (fields[2] != "" and (not fields[2].isspace())):
					generics[fields[2]] += int(fields[-1])
			for generic in generics.keys():
				generic2cluster[generic].append(cluster)
			if (len(generics.keys())>1):
				goodGenerics = {}
				for generic in generics.keys():
					if (generics[generic] > minNumForUnion):
						goodGenerics[generic] = generics[generic]
				if (len(goodGenerics.keys())>0):
					generics = goodGenerics
				if (len(generics.keys())>1):	
					print("Multiple generic names for cluster %s : %s"%(cluster," // ".join(generics.keys())))
	else:
		# Split cluster by removal file
		with open("multipleGeneric.afterManualRemoval") as file:
			for line in file:
				[cluster,generic] = str.split(line.rstrip("\r\n"),"\t")
				cluster = int(cluster)
				
				new_cluster2combs = []
				for i in cluster2combs[cluster]:
					fields = [f.replace("*NF*","").rstrip(" ").lstrip(" ") for f in str.split(combs[i],"\t")]
					if (fields[2] == generic):
						eprint("Splitting %s from cluster %d"%(combs[i],cluster))
						cluster2combs[iCluster].append(i)
						allClusters[i] = [iCluster]
					else:
						new_cluster2combs.append(i)
				cluster2combs[cluster] = new_cluster2combs
				iCluster += 1

	# Get (again) all clusters per generic name
	if (mode == "unite"):
		minNumForUnion = 10
		generic2cluster = defaultdict(list)
		for cluster in cluster2combs.keys():
			generics=defaultdict(int)
			for i in cluster2combs[cluster]:
				fields = [f.replace("*NF*","").rstrip(" ").lstrip(" ") for f in str.split(combs[i],"\t")]
				if (fields[2] != "" and (not fields[2].isspace())):
					generics[fields[2]] += int(fields[-1])

			if (len(generics.keys())>1):
				goodGenerics = {}
				for generic in generics.keys():
					if (generics[generic] > minNumForUnion):
						goodGenerics[generic] = generics[generic]
				if (len(goodGenerics.keys())>0):
					generics = goodGenerics				
			for generic in generics.keys():
				generic2cluster[generic].append(cluster)
				
		clustersMap = {}
		for generic in generic2cluster.keys():
			if (len(generic2cluster[generic])>1):
				eprint("Uniting %s for generic = %s"%(",".join("%d"%k for k in generic2cluster[generic]),generic))
				for i in range(1,len(generic2cluster[generic])):
					clustersMap[generic2cluster[generic][i]] = generic2cluster[generic][0]
		
		finalClusterMap = {}
		for cluster in range(iCluster):
			finalCluster = cluster
			while (finalCluster in clustersMap.keys()):
				finalCluster = clustersMap[finalCluster]
			finalClusterMap[cluster] = finalCluster
		
		mixedClusters = {}
		for i in range(len(combs)):
			clusters = { finalClusterMap[c]:1 for c in allClusters[i]}
			myClusters = clusters.keys()
			if (len(myClusters)>1):
				s = ",".join("%d"%k for k in myClusters)
				if (s not in mixedClusters.keys()):
					mixedClusters[s] = iCluster
					iCluster += 1
				myClusters = [mixedClusters[s]]
			print("%d\t%s"%(myClusters[0],combs[i]))
			
def get_combs(type = "MAIN"):
# Read required ids
	ids = []
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/allIds.newId","r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append(int(id))

	readers = mimic3_readers()

	n = 0 
	dir = "/home/yaron/Mimic3/"
	names = ["DRUG","DRUG_NAME_POE","DRUG_NAME_GENERIC","FORMULARY_DRUG_CD","GSN","NDC"]

	values = {name : defaultdict(int) for name in names}
	nEmpty = defaultdict(int)
	combs = defaultdict(int)
	for id in ids:
		lines,header = readers.read_lines(dir,"PRESCRIPTIONS",id)
		for line in lines:
			lineType = line[header["DRUG_TYPE"]]
			if ((type == "MAIN"  and lineType != "MAIN" and lineType != "ADDITIVE") or (type != "MAIN" and lineType != type)):
				continue
				
			n += 1
			for name in names:
				value = line[header[name]]
				if (value == "" or value.isspace()):
					nEmpty[name]+=1
				else:
					values[name][value] +=1
			comb = "\t".join(line[header[name]].upper() for name in names)
			combs[comb] += 1
					
	for comb in combs.keys():
		print("%s\t%d"%(comb,combs[comb]))
					
def get_atc(mode):
	# Read Clusters
	combs = defaultdict(list)
	with open("clusters2","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			cluster = fields.pop(0)
			combs[cluster].append(fields)
			
	# Read ATC file
	atc = {}
	extra_atc = {}
	
	if (mode == "atc"):
		fileName = "full_atc"
	else:
		fileName = "extended_atc"
	
	with open(fileName,"r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			atc[fields[1].upper()] = fields[0]
			matchObj = re.match(r'(.*)\s+\((.*)\)',fields[1].upper(), re.M|re.I)
			if (matchObj):
				extra_atc[matchObj.group(1)] = fields[0]
				extra_atc[matchObj.group(2)] = fields[0]
	
	# Look in drug-names
	nFound = 0
	nMult = 0
	for cluster in combs.keys():
		names = {}
		size =  0
		found_atc = ""
		found_desc = ""
		for comb in sorted(combs[cluster],key= lambda x : int(x[-1]), reverse=True):
			size += int(comb[-1])
			for field in range(3):
				name = comb[field].replace("*IM*"," ").replace("*SC*"," ").replace("*IV*"," ").replace("*PO*"," ").replace("*NF*"," ").replace(",","")
				name = name.replace("(","").replace(")","").replace("-"," ").rstrip(" ").lstrip(" ")
				if (name != "" and not name.isspace()):
					# Check name in original atc list
					if (name in atc.keys()):
						if (found_atc == ""):
							found_desc = "%s (%d)"%(name,int(comb[-1]))
							found_atc = atc[name]
						elif (atc[name] != found_atc):
							eprint("1. Extra atc for cluster %s : %s from \'%s\' ; Base = %s ; # = %s"%(cluster,name,comb,found_desc,comb[-1]))

					
					# Check subset of name in original atc list
					if (found_atc == ""):
						words = str.split(name," ")
						nwords = len(words)
						for start in range(nwords):
							for end in range(start,nwords):
								candidate = " ".join(words[i] for i in range(start,end+1))
								if (candidate in atc.keys()):
									if (found_atc == ""):
										found_desc = "%s (%d)"%(candidate,int(comb[-1]))
										found_atc = atc[candidate]
									elif (atc[candidate] != found_atc):
										eprint("2. Extra atc for cluster %s : %s from \'%s\' ; Base = %s ; # = %s"%(cluster,candidate,comb,found_desc,comb[-1]))

					# Check name in extra atc list
					if (found_atc == ""):
						if (name in extra_atc.keys()):
							if (found_atc == ""):
								found_desc = "%s (%d)"%(name,int(comb[-1]))
								found_atc = extra_atc[name]
							elif (extra_atc[name] != found_atc):
								eprint("3. Extra atc for cluster %s : %s from \'%s\' ; Base = %s ; # = %s "%(cluster,name,comb,found_desc,comb[-1]))

					
					# Check subset of name in extra atc list
					if (found_atc == ""):
						words = str.split(name," ")
						nwords = len(words)
						for start in range(nwords):
							for end in range(start,nwords):
								candidate = " ".join(words[i] for i in range(start,end+1))
								if (candidate in extra_atc.keys()):
									if (found_atc == ""):
										found_desc = "%s (%d)"%(candidate,int(comb[-1]))
										found_atc = extra_atc[candidate]
									elif (extra_atc[candidate] != found_atc):
										eprint("4. Extra atc for cluster %s : %s from \'%s\' ; Base = %s ; # = %s"%(cluster,candidate,comb,found_desc,comb[-1]))										
										
		print("%d\t%s\t%s\t%s"%(size,cluster,found_desc,found_atc))

def transform_generic(comb2atc,transformFile):
	# Read transform file
	transform = {}
	with open (transformFile,"r") as gen:
		for line in gen:
			fields = str.split(line.rstrip("\r\n"),"\t")
			if (len(fields)==4):
				if (fields[1] in transform.keys() and transform[fields[1]] != fields[3]):
					raise ValueError("Inconsistent transformation for %s"%fields[1])
				transform[fields[1]]= fields[3]

	# Transform
	with open(comb2atc,"r") as infile:
		for line in infile:
			fields = str.split(line.rstrip("\r\n"),"\t")
			if (fields[6] in transform.keys()):
				fields[6] = transform[fields[6]]
			fields[6] = fields[6].rstrip(" ")
			print("%s"%("\t".join(fields)))

def show_generic(comb2atc = "comb2atc"):
	# Read clusters
	combs = defaultdict(list)
	counters = {}
	clusters = {}
	all_clusters = {}
	with open("clusters2","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			cls = fields.pop(0)
			count = fields.pop()
			comb = "\t".join(fields)
			clusters[comb] = cls
			counters[comb] = int(count)
			all_clusters[cls] = 1
			
	# Read comb2atc
	cluster2generic = {cl : defaultdict(int) for cl in all_clusters.keys()}
	with open(comb2atc,"r") as comb:
		for line in comb:
			fields = str.split(line.rstrip("\r\n"),"\t")
			if (len(fields)==8):
				fields.pop()
			generic = fields.pop()
			comb = "\t".join(fields)
			cluster2generic[clusters[comb]][generic] += counters[comb]
			
	for cluster in cluster2generic.keys():
		generic = sorted(cluster2generic[cluster].keys(),key= lambda g : cluster2generic[cluster][g], reverse=True)
		for g in generic:
			print("%s\t%s\t%d"%(cluster,g,cluster2generic[cluster][g]))
		print()
		
def get_comb2atc():
	# Read clusters
	combs = defaultdict(list)
	counters = {}
	with open("clusters2","r") as clusters:
		for line in clusters:
			fields = str.split(line.rstrip("\r\n"),"\t")
			cluster = fields.pop(0)
			count = fields.pop()
			comb = "\t".join(fields)
			combs[cluster].append(comb)
			counters[comb] = int(count)
			
	# Read cluster2atc
	atc = {}
	with open("atcStatus","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			atc[fields[1]] = fields[-1]
	
	# Get drug name to generic
	name2generics = {}
	for cluster in combs.keys():
		for comb in combs[cluster]:
			fields = str.split(comb,"\t")
			if (fields[0] != "" and not fields[0].isspace() and fields[2] != "" and not fields[2].isspace()):
				if (fields[0] not in name2generics.keys()):
					name2generics[fields[0]] = defaultdict(int)
				generic = fields[2].replace("-","").replace("(*IND*)","").replace("<IND>","").replace("(IND)","")
				name2generics[fields[0]][generic] += counters[comb]
	
	name2generic = {}
	for name in name2generics.keys():
		generics = sorted(name2generics[name].keys(),key=lambda x : name2generics[name][x], reverse=True)
		generic = generics[0]
		if (len(generics)>1):
			for i in range(1,len(generics)):
				if (generics[i] == name and name2generics[name][generics[i]] > 5):
					eprint("Replacing most common generic \'%s\' for %s (%d) with %s (%d)"%(generic,name,name2generics[name][generic],generics[i],name2generics[name][generics[i]]))
					generic = generics[i]
					break
		name2generic[name] = generic
					
	# Write comb to generic to atc
	for cluster in combs.keys():
		for comb in combs[cluster]:
			fields = str.split(comb,"\t")
			if (fields[0]!="" and not fields[0].isspace()):
				if (fields[0] in name2generic.keys()):
					generic = name2generic[fields[0]]
				else :
					generic = fields[0].replace("-","").replace("(*IND*)","").replace("<IND>","").replace("(IND)","").replace("*IND*","")
				if (atc[cluster] != ""):
					print("%s\t%s\t%s"%(comb,generic,atc[cluster]))
				else :
					print("%s\t%s"%(comb,generic))
			else:
				eprint("Problems finding generic for %s"%comb)
	
def get_add_comb2atc():
	# Read combs
	combs = []
	counters = []
	with open("add_combs","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			counters.append(fields.pop())
			combs.append(fields)
			
	# Read ATC file
	atc = {}
	extra_atc = {}
	fileName = "extended_atc"

	with open(fileName,"r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			atc[fields[1].upper()] = fields[0]
			matchObj = re.match(r'(.*)\s+\((.*)\)',fields[1].upper(), re.M|re.I)
			if (matchObj):
				extra_atc[matchObj.group(1)] = fields[0]
				extra_atc[matchObj.group(2)] = fields[0]

	# Get drug name to generic
	name2generics = {}
	for i in range(len(combs)):
		fields = combs[i]
		counter = counters[i]
		if (fields[0] != "" and not fields[0].isspace() and fields[2] != "" and not fields[2].isspace()):
			if (fields[0] not in name2generics.keys()):
				name2generics[fields[0]] = defaultdict(int)
			name2generics[fields[0]][fields[2]] += counter
	
	name2generic = {}
	for name in name2generics.keys():
		generics = sorted(name2generics[name].keys(),key=lambda x : name2generics[name][x], reverse=True)
		generic = generics[0]
		if (len(generics)>1):
			for i in range(1,len(generics)):
				if (generics[i] == name and name2generics[name][generics[i]] > 5):
					eprint("Replacing most common generic \'%s\' for %s (%d) with %s (%d)"%(generic,name,name2generics[name][generic],generics[i],name2generics[name][generics[i]]))
					generic = generics[i]
					break
		name2generic[name] = generic				
				
	# Look in drug-names
	for comb in combs:
		name = comb[0].replace("*IM*"," ").replace("*SC*"," ").replace("*IV*"," ").replace("*PO*"," ").replace("*NF*"," ").replace(",","")
		name = name.replace("(","").replace(")","").replace("-"," ").rstrip(" ").lstrip(" ")
		found_atc = ""
		if (name != "" and not name.isspace()):
			if (name in name2generic.keys()):
				generic = name2generic[name]
			else:
				generic = name
				
			# Check name in original atc list
			if (name in atc.keys()):
				found_atc = atc[name]
					
			# Check subset of name in original atc list
			if (found_atc == ""):
				words = str.split(name," ")
				nwords = len(words)
				for start in range(nwords):
					for end in range(start,nwords):
						candidate = " ".join(words[i] for i in range(start,end+1))
						if (candidate in atc.keys()):
							found_atc = atc[candidate]
							break

			# Check name in extra atc list
			if (found_atc == ""):
				if (name in extra_atc.keys()):
					found_atc = extra_atc[name]

			# Check subset of name in extra atc list
			if (found_atc == ""):
				words = str.split(name," ")
				nwords = len(words)
				for start in range(nwords):
					for end in range(start,nwords):
						candidate = " ".join(words[i] for i in range(start,end+1))
						if (candidate in extra_atc.keys()):
							found_atc = extra_atc[candidate]
							break

			if (found_atc != ""):
				print("%s\t%s\t%s"%("\t".join(comb),generic,found_atc))
			else:
				print("%s\t%s"%("\t".join(comb),generic))
				print("%s\t%s"%("\t".join(comb),generic))
				
def get_comb2code():
	# Read combs
	combs = []
	counter = []
	with open("base_combs","r") as clusters:
		for line in clusters:
			fields = str.split(line.rstrip("\r\n"),"\t")
			counter.append(fields.pop())
			combs.append(fields)
			
	# Read name2code
	mapper = {}
	with open("base_cluster_names","r") as file:
		for line in file:
			fields = str.split(line.rstrip("\r\n"),"\t")
			mapper[fields[0]] = fields[1]
	
	# Write comb2code
	for i in range(len(combs)):
		comb = combs[i]
		if (comb[0] in mapper.keys()):
			code = mapper[comb[0]]
		elif (comb[0] != "" and not comb[0].isspace()):
			code = comb[0]
		else:
			code = "NA"
#		print("%s\t%s\t%s"%("\t".join(comb),code,counter[i]))
		print("%s\t%s"%("\t".join(comb),code))
###########################

## Main
mode = sys.argv[1]
if (mode == "get_combs"):
	get_combs()
elif (mode == "get_base_combs"):
	get_combs("BASE")
elif (mode == "get_add_combs"):
	get_combs("ADDITIVE")
elif (mode == "atc" or mode == "extended_atc"):
	get_atc(mode)
elif (mode == "cluster" or mode == "find_multiple" or mode == "unite"):
	analyze_combs(mode)
elif (mode == "comb2atc"):
	get_comb2atc()
elif (mode == "comb2code"):
	get_comb2code()
elif (mode == "add_comb2atc"):
	get_add_comb2atc()
elif (mode == "show_generic"):
	if (len(sys.argv)==3):
		show_generic(sys.argv[2])
	else:
		show_generic()
elif (mode == "transform"):
	if (len(sys.argv)==4):
		transform_generic(sys.argv[2],sys.argv[3])
	else:
		transform_generic("comb2atc","generic_counts")

