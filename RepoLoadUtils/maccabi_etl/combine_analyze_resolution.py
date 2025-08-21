#!/usr/bin/python

from __future__ import print_function
import sys
import argparse
import pandas as pd
import glob

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_res_folder', default='res')
parser.add_argument('--out_combined_res_file', default='all_res.csv')
parser.add_argument('--out_best_res_file', default='best_res.csv')
args = parser.parse_args()

in_file_names = glob.glob(args.in_res_folder + '/*')

df = pd.DataFrame()
for f in in_file_names:
	eprint('reading', f)
	t = pd.read_csv(f, names = ['sig', 'res', 'num'], sep = ',')
	if t.res.count() < 3:
		t = pd.read_csv(f, names = ['sig', 'res', 'num'], sep = '\t')
	df = pd.concat([df, t], axis = 0)

eprint ('df', df.shape, df.head())

df = df[df.res < 10000]
s = df.groupby(['sig', 'res']).agg({'num': 'sum'}).reset_index()
eprint('writing', args.out_combined_res_file)
s.to_csv(args.out_combined_res_file, index=False)

best = s.sort_values(['sig', 'num']).groupby('sig').last().reset_index()
eprint('writing', args.out_best_res_file)
best.to_csv(args.out_best_res_file, index=False)