#!/usr/bin/python

from __future__ import print_function
import sys
import argparse
import pandas as pd

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_signal_file', default='lab/crp_new')
parser.add_argument('--in_best_res_file', default='best_res.csv')
parser.add_argument('--out_fixed_res_file', default='fixed_res/crp_new')
args = parser.parse_args()

eprint("reading", args.in_signal_file, args.in_best_res_file, "will write to", args.out_fixed_res_file)
best_res = pd.read_csv(args.in_best_res_file, dtype = {"sig": str})
best_res_dict = {}
def put_in_dict(x):
	
	if x['res'] == 1:
		resolution = "{:.0f}"
	elif x['res'] == 0.1:
		resolution = "{:.1f}"
	elif x['res'] == 0.01:
		resolution = "{:.2f}"
	else:
		raise ValueError("sig: " + x['sig'] + " has unknown resolution: " + str(x['res']))
	best_res_dict[x['sig']] = resolution
	
best_res.apply(put_in_dict, axis = 1)
raw = pd.read_csv(args.in_signal_file, sep = ' ', names = ['pid', 'sig', 'date', 'orig_val', 'extra'], dtype = {"sig": str})
raw.loc[:, 'val'] = raw.apply(lambda x: 0 if x["orig_val"] == 0 else float(best_res_dict[x["sig"]].format(x["orig_val"])), axis = 1)
raw.to_csv(args.out_fixed_res_file, index=False, sep = ' ', header=False, columns=['pid', 'sig', 'date', 'val', 'orig_val'])