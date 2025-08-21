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

def get_combs():
	# Read required ids
	ids = []
	with open("/nas1/Work/Users/yaron/InPatients/Mimic3/allIds.newId","r") as file:
		for line in file:
			[id,newId] = str.split(line.rstrip("\r\n"),"\t")
			ids.append(int(id))

	readers = mimic3_readers()

	n = 0 
	dir = "/home/yaron/Mimic3/"

	values = {name : defaultdict(int) for name in names}
	nEmpty = defaultdict(int)
	combs = defaultdict(int)
	for id in ids:
		lines,header = readers.read_lines(dir,"OUTPUTEVENTS",id)
		for line in lines:
				
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
					
###########################

## Main
mode = sys.argv[1]
if (mode == "get_combs"):
	get_combs()
