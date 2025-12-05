#!/usr/bin/env python

import argparse as ap
import re
import sys

parser = ap.ArgumentParser(description = "Paste two files")
parser.add_argument("-f1","--file1",help="first file (STDIN if omitted)",default="STDIN")
parser.add_argument("-ids1","--indices1",nargs='+',help="first file key indices(0 if omitted)",default=[0])
parser.add_argument("-f2","--file2",help="second file (STDIN if omitted)",default="STDIN")
parser.add_argument("-ids2","--indices2",nargs='+',help="second file key indices (0 if omitted)",default=[0])
parser.add_argument("-ads2","--additional2", nargs='+', help="second file additional indices (all if ommited)",default=[])
parser.add_argument("-s","--separator",help=r"field separator (\s+ if omitted)",default=r"\s+")
parser.add_argument("-os","--out_separator",help="output field separator (space if omitted)",default=" ")
parser.add_argument("-o","--order",help="the order determining file ([1]/2)",default=1)
parser.add_argument("-e","--external",help="print lines in file1 with no match in file2",action="store_true")

args = parser.parse_args() 
order = int(args.order)

assert(args.file1 != "STDIN" or args.file2 != "STDIN")
assert(order == 1 or order == 2) 
inds2 = [int(i) for i in args.indices2]
inds1 = [int(i) for i in args.indices1]

# Loop on File2 and index
if (args.file2 == "STDIN"):
	file2=sys.stdin
else:
	file2 = open(args.file2,"r")

idx = 0
taker = {}

for line in file2:
	fields = re.split(args.separator,line.rstrip("\r\n"))
	key = [fields[i] for i in inds2]
	
	if (len(args.additional2) > 0):
		add = args.out_separator.join([fields[int(i)] for i in args.additional2])
	else:
		add = args.out_separator.join([fields[i] for i in range(len(fields)) if i not in inds2])
	
	taker[tuple(key)] = {'idx':idx , 'info':add}
	idx += 1
file2.close()

# Loop on File1 and print
if (args.file1 == "STDIN"):
	file1=sys.stdin
else:
	file1 = open(args.file1,"r")
	
outLines = []

for line in file1:
	stripped = line.rstrip("\r\n")
	fields = re.split(args.separator,stripped)
	key = tuple([fields[i] for i in inds1])
	if (key in taker or args.external):
		if (key in taker):
			stripped = args.out_separator.join([stripped,taker[key]['info']])
			
		if (order == 1):
			print (stripped)
		else:
			outLines.append((taker[key]['idx'],stripped))
			
# Print in order
if (order == 2):
	for record in sorted(outLines,key=lambda outLines: outLines[0]):
		print(record[1])
			

