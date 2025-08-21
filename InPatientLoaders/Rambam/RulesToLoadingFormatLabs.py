#!/usr/bin/python
"""rambamParse.py: parse rmbam patient file."""
##import xml.etree.ElementTree as ET
from lxml import etree as ET

import sys
import glob
import math
paralelIndex=int(sys.argv[1])
paralelTotal=int(sys.argv[2])
rulesFileName=sys.argv[3]

inFile=open(rulesFileName,'r')
textIn=inFile.readlines()
textIn.pop(0) # get rid of titles
splitLine=[]
for line in textIn:
	
	line=line.rstrip().split('\t')
	f=lambda x:x.decode('utf-8').encode('utf-8').rstrip()
	line=map(f,line)
	if len(line)<2: continue# get rid of last line
	if line[9]=='IGNORE': continue# get rid of IGNORE lines
	splitLine.append(line)


#splitLine.sort()

resolution={}
standardName={}
factor={}
for line in splitLine:
	key=line[2]
	resolution[key]=line[10]
	standardName[key]=line[9]
	factor[key]=line[11]

flist=glob.glob('/nas1/Data/RAMBAM/da_medial_patients/*.xml')
flistLen=len(flist)
first=math.floor(flistLen*paralelIndex/paralelTotal)
last=math.floor(flistLen*(paralelIndex+1)/paralelTotal-1)

flist=flist[int(first):int(last)]

labcodes={} 
count=0
for ff in flist:
	sys.stderr.write(ff+'\t'+str(count)+'\n')
	count+=1
	thisFile=open(ff)
	patientNames=['Patient ID','hmo','nationality','birthdate','deceaseddate''gendercode']
	tree = ET.parse(thisFile)

	root=tree.getroot()

	#for name in patientNames:
	#	print root.name+"\t"
	#print""
	#print root.tag


	#print "ID\ttime\tevent type\t",
#	for name in names:
#		print name+'\t',
#	print ""
	thisID=root.attrib.get("ID")
	for child in root:
		type=child.get('Type')
		time=child.get('Time')
		thisEv={}
		if type!="ev_lab_results_numeric":
			continue
		for gc in child:
				thisEv[gc.get("Name")]=gc.text.encode('utf-8').rstrip()
		
		thisKey=thisEv['testcode']+'@'+thisEv['valueunitcode'].upper().replace('\\','/')
		if not thisKey in resolution:
			continue
		thisValue=thisEv['valueconversion']
		time1=thisEv['collectiondate']
		time2=thisEv['resultdate']
		newName=standardName[thisKey]
		print thisID,'\t',newName,'\t',time1,'\t',time2,'\t',thisValue,'\t',thisEv['valueunitcode'].upper().replace('\\','/')
#patientId Signame Time1 Time2 Value Unit
