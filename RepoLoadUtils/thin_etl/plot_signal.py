#!/usr/bin/python

from __future__ import print_function
from collections import defaultdict
import argparse
import sys
import matplotlib.pyplot as plt
import glob
import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import plot

parser = argparse.ArgumentParser()
parser.add_argument('--in_signal_files', default='/server/Work/Users/Ido/THIN_ETL/ahd/Fixed/CRP*')
parser.add_argument('--sig', default='CRP')
parser.add_argument('--min_pct_to_display', type=int, default=1)
parser.add_argument('--min_val', default=5)
parser.add_argument('--do_series_per_origin', default=1)
parser.add_argument('--out_file_prefix', required=True)

args = parser.parse_args()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
				
in_file_names = []
sigs = args.sig.split(",")
for g in args.in_signal_files.split(","):
	in_file_names.extend(glob.glob(g))
eprint("looking for", sigs, "in", in_file_names)
hist = defaultdict(int)
lines_scanned, lines_found = 0, 0
sep = '\t'
for fname in in_file_names:
	eprint("reading", fname)
	with open(fname, 'r') as f:
		for l in f:
			lines_scanned += 1
			if (lines_scanned % 1000000 == 0):
				eprint("scanned", lines_scanned, "lines, found", lines_found)
			s = l.strip().split(sep)
			if len(s) == 1:
				sep = ' '
				s = l.strip().split(sep)
			if s[1] in sigs:
				lines_found += 1
				hist[(s[3], 'all', 'all')] += 1
				if args.do_series_per_origin == 1 and len(s) >=5:
					hist[(s[3], s[4], 'all')] += 1
				if args.do_series_per_origin == 1 and len(s) >=6:
					hist[(s[3], s[4], s[5])] += 1
					hist[(s[3], 'all', s[5])] += 1
df = pd.DataFrame({"X": [c[0] for c in hist.keys()], "Y": hist.values(), "Origin": ["_".join(map(str, [c[1],c[2]])) for c in hist.keys()]})
df = df[df.Y >= args.min_val]
df = df.sort_values(['Origin', 'X'])
csv_file = args.out_file_prefix + ".csv"
eprint('writing', len(hist), 'lines to', csv_file)
df.to_csv(csv_file, index=False)

html_file = args.out_file_prefix + ".html"
eprint('writing', html_file)

data = []
size_all = df[df.Origin == 'all_all'].Y.sum()
eprint("size_all", size_all)
def append_series(o):
	my_series = df[df.Origin == o]
	trace0 = go.Scatter(x = my_series.X, y = my_series.Y, mode = 'markers', name = o)
	data.append(trace0)
g = df.groupby('Origin').agg({'Y': 'sum'}).reset_index()
eprint("all", g)
g[g.Y > size_all * args.min_pct_to_display / 100].Origin.apply(append_series)
eprint("filtered out", g[g.Y <= size_all * args.min_pct_to_display / 100])
plot(data, filename=html_file, auto_open=False)

