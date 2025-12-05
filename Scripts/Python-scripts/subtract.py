#!/usr/bin/env python

import argparse as ap
import re
import sys

parser = ap.ArgumentParser(description = "Subtract two files")
parser.add_argument("-f1","--file1",help="first file (STDIN if omitted)",default="STDIN")
parser.add_argument("-ids1","--indices1",nargs='+',help="first file indices (0 if omitted)",default=[0])
parser.add_argument("-f2","--file2",help="second file (STDIN if omitted)",default="STDIN")
parser.add_argument("-ids2","--indices2",nargs='+',help="second file indices (0 if omitted)",default=[0])
parser.add_argument("-s","--separator",help="field separator (\s+ if omitted)",default="\s+")

args = parser.parse_args() 
#order = int(args.order)

assert(args.file1 != "STDIN" or args.file2 != "STDIN")

# Loop on File2 and index
if (args.file2 == "STDIN"):
	file2=sys.stdin
else:
	file2 = open(args.file2,"r")

taker = {}
for line in file2:
	fields = re.split(args.separator,line.rstrip("\r\n"))
	key = [fields[int(i)] for i in args.indices2]
	taker[tuple(key)] = 1
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
	key = tuple([fields[int(i)] for i in args.indices1])
	if (key not in taker):
			print (stripped)
