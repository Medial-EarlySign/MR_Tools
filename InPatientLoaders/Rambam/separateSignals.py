#!/usr/bin/python
#convert ids according to rambamIdConversion.txt
#separate  to files according to signal names
import sys
import os, pwd

work_folder=sys.argv[1]

inFile=open(work_folder + '/id2nr','r')
textIn=inFile.readlines()
splitLine=[]
idConvert={}
for line in textIn:
	line=line.rstrip().split('\t')
	idConvert[line[1]]=line[0]
textIn=sys.stdin.readlines()
splitLine=[]
fileHandleNames={}
for line in textIn:
	
	line1=line.rstrip().split('\t')
	f=lambda x: x.rstrip()
	line1=map(f,line1)
	fname=work_folder + '/converted/'+line1[1]
	if not fname in fileHandleNames:
		fileHandleNames[fname]=open(fname,'w')
	if line1[4]=='Null':
		continue
	line1[5]=line1[5].replace('\"','').upper()
	fileHandleNames[fname].write(idConvert[line1[0]].rstrip())
	for i in range(1,len(line1)):
		fileHandleNames[fname].write('\t'+line1[i])
	fileHandleNames[fname].write('\n')
	
	
for f in fileHandleNames:
	fileHandleNames[f].close()
