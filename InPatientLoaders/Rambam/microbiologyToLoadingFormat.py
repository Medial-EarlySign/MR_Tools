#!/usr/bin/python
"""microbiologyToLoadingFormat.py: parse translate the rambam raw data to loading format using dictionaries"""
from lxml import etree as ET

import sys
import glob
import sets
import math
import re
import os
import pwd
import argparse

paralelIndex=int(sys.argv[1])
paralelTotal=int(sys.argv[2])
work_folder=sys.argv[3]

specDict={}
inFile=open('dirSpec.txt','r')
textIn=inFile.readlines()

splitLine=[]
for line in textIn:
	line=line.rstrip().split('\t') 
	
	#f=lambda x: x.rstrip().encode('utf-8')
	#line=map(f,line)
	for k in range(1,len(line)-1):
		line[k]=line[k].decode('utf-8').encode('utf-8').rstrip()
	if len(line)<2: continue# get rid of last line
	specDict[line[0]]=line[1]

idDict={}
inFile=open(work_folder + '/id2nr','r')
textIn=inFile.readlines()

splitLine=[]
for line in textIn:
	line=line.rstrip().split('\t') 
	if len(line)<2: continue# get rid of last line
	idDict[line[1]]=line[0]


flist=glob.glob('/nas1/Data/RAMBAM/da_medial_patients/*.xml')
flistLen=len(flist)
first=math.floor(flistLen*paralelIndex/paralelTotal)
last=math.floor(flistLen*(paralelIndex+1)/paralelTotal-1)

flist=flist[int(first):int(last)]
count=0
for ff in flist:
	sys.stderr.write(ff+'\t'+str(count)+'\n')
	count+=1
	thisFile=open(ff)
	tree = ET.parse(thisFile)

	root=tree.getroot()


	thisID=root.attrib.get("ID")
	
	for child in root:
		type=child.get('Type')
		time=child.get('Time')
		thisEv={}
		if type!="ev_lab_results_microbiology":
			continue
		for gc in child:
				thisEv[gc.get("Name")]=gc.get("Hier").encode('utf-8').rstrip()
				#thisEv[gc.get("Name")]=gc.text.rstrip()
				if gc.get("Name") in ["collectiondate","resultdate"]:
					thisEv[gc.get("Name")]=gc.text.encode('utf-8').rstrip()
		thisDate=thisEv["collectiondate"]
		#extract the level 2 name of organism
		thisOrganism=re.search('2:(.*)3:',thisEv["microorganism_code"])
		if thisOrganism!=None:
			thisOrganism=thisOrganism.group(1).lstrip().rstrip('~')
		else: thisOrganism='NoOrganism'
		#extract the spec code
		thisSpec=re.search('1:(.*)2:',thisEv["specimenmaterialcode"])
		if thisSpec != None:
			thisSpec=specDict[thisSpec.group(1).lstrip().rstrip('~')]
		else: thisSpec='NoSpec'
		#extract the antibiotic name and atc
		thisAbName=re.search('1:(.*)2:',thisEv["antibioticcode"])
		if thisAbName!=None:
			thisAbName=thisAbName.group(1).lstrip().rstrip('~')
		else: thisAbName='NoAntiBiotics'
		thisATC=re.search('2:(.*)3:',thisEv["antibioticcode"])
		if thisATC!=None:
			thisATC=thisATC.group(1).lstrip().rstrip('~')
		else: thisATC='NA'
		#extract susceptability
		thisSusc=re.search('1:(.*)',thisEv["susceptibilityinterpretation"])
		if thisSusc!=None:
			thisSusc=thisSusc.group(1).lstrip().rstrip('~')
		else: thisSusc='NA'
		# check for new exam ( and not continuation of previous one)
		
		print  idDict[thisID],'\tMICROBIOLOGY\t',thisDate,'\t',thisEv["resultdate"],'\tMB_DESC:Culture:'+thisSpec+'|'+thisOrganism+'\tMB_DESC:Test:'+thisAbName+'|'+thisATC+'|'+thisSusc
		
		
#patientId Signame Time1 Time2 Value Unit
