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

path = str.split(sys.argv[1],"/")
file = path.pop().replace(".csv","")
dir = "/".join(path)
inId = int(sys.argv[2])
print ("%d at %s:\n"%(inId,file))
lines,header = readers.read_lines(dir,file,inId) 
for line in lines:
	id = int(line[header["SUBJECT_ID"]])
	if (id != inId):
		raise ValueError("Id Mismatch: Required %d Got %d"%(inId,id))
	print(line)

