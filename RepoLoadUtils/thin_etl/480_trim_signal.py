#!/usr/bin/python

from __future__ import print_function
import argparse
import sys
import string
import pandas as pd
import numpy as np
import os
import scipy.stats
import statsmodels.stats.proportion as proportion
import random

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_signal_file', default='ahd/Fixed/CRP', type=argparse.FileType('r'))
parser.add_argument('--in_trimming_instructions_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/trimming_instructions.txt')
parser.add_argument('--out_signal_file', default='ahd/Trimmed/CRP', type=argparse.FileType('w'))
args = parser.parse_args()


instructions = {}
eprint("reading", args.in_trimming_instructions_file)
df = 	pd.read_csv(args.in_trimming_instructions_file, sep = '\t')
def fill_instructions(x):
	instructions[str(x['Name'])] = x.copy()
df.apply(fill_instructions, axis = 1)
eprint("reading", args.in_signal_file, "writing", args.out_signal_file)
for line in args.in_signal_file:
	a = map(lambda x: x.strip(), line.split('\t'))
	val = float(a[3])
	sig = str(a[1])
	if sig not in instructions:
		ins = instructions["Default"]
	else:
		ins = instructions[sig]
	if val > ins['MaxRemove'] or val < ins['MinRemove']:
		continue
	orig_val = ""
	if val > ins['MaxTrim']:
		orig_val = str(val)
		val = ins['MaxTrim']
	if val < ins['MinTrim']:
		orig_val = str(val)
		val = ins['MinTrim']
	a[3] = val
	a.append(orig_val)
	f = "\t".join(map(str, a))
	print(f, file = args.out_signal_file)

