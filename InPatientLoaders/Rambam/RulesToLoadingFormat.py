#!/usr/bin/python
"""rambamParse.py: parse rmbam patient file."""
##import xml.etree.ElementTree as ET
from lxml import etree as ET

import sys
import glob
import sets
import math
paralelIndex=int(sys.argv[1])
paralelTotal=int(sys.argv[2])
rulesFileName=sys.argv[3]

inFile=open(rulesFileName,'r')
textIn=inFile.readlines()
textIn.pop(0)
# this part was written to get uniq 
#splitLine=sets.Set()
#for line in textIn:
#	splitLine.add(line.decode('utf-8').encode('utf-8').rstrip())
#for line in splitLine:
#	print line
#quit()

splitLine=[]
for line in textIn:
	line=line.rstrip().strip('"').replace('\"','').split('\t') #replace removes quotes
	
	#f=lambda x: x.rstrip().encode('utf-8')
	#line=map(f,line)
	for k in range(1,len(line)-1):
		line[k]=line[k].decode('utf-8').encode('utf-8').rstrip()
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
		if type!="ev_measurements_numeric":
			continue
		for gc in child:
				thisEv[gc.get("Name")]=gc.text.encode('utf-8').rstrip()
				#thisEv[gc.get("Name")]=gc.text.rstrip()
		
		thisKey=thisEv['measurementcode']+'@'+thisEv['resultunits'].replace('\"','').upper()
		if not thisKey in resolution:
			continue
		thisValue=thisEv['result']
		time1=thisEv['measurementdate']
		time2=thisEv['measurementdate']
		newName=standardName[thisKey]
		print thisID,'\t',newName,'\t',time1,'\t',time2,'\t',thisValue,'\t',thisEv['resultunits'].strip('"').upper()
#patientId Signame Time1 Time2 Value Unit
