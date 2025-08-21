#!/usr/bin/python

from __future__ import print_function
import sys
import argparse
import pandas as pd

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_signal_file', default='lab/lab2004.part0')
parser.add_argument('--out_analysis_file', default='res/res.lab2004.part0.csv')
args = parser.parse_args()

def clean_and_strip(x):
    return x.strip()

def get_res(x):
    if x == 0:
        return None	
    res = 100000.0
    while int(x/res) != x/res and res > 0.0000001:
        res = res/10
    return res

resolution = {}
examples_per_res = {}
eprint("reading", args.in_signal_file, "will write to", args.out_analysis_file)
raw = pd.read_csv(args.in_signal_file, sep = ' ', names = ['pid', 'sig', 'date', 'val', 'extra'])
raw.loc[:, 'res'] = raw.val.apply(get_res)
o = raw.groupby(['sig', 'res']).size().reset_index()
o.columns = ['sig', 'res', 'num']
o.to_csv(args.out_analysis_file, index=False)