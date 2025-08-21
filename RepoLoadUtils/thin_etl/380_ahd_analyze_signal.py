from __future__ import print_function
from collections import defaultdict
import sys
import argparse
import os
import glob
from get_moments import get_moments, moments_to_str

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--window_size', default=10, type=int)
parser.add_argument('--signal_files', required=True)
parser.add_argument('--out_files_prefix', required=True)
args = parser.parse_args()

def clean_and_strip(x):
    return x.strip()

def get_res(x):
    res = 100000.0
    while int(x/res) != x/res and res > 0.0000001:
        res = res/10
    return res

in_file_names = glob.glob(args.signal_files)
eprint("about to process", len(in_file_names), "files")
out_file_res = open(args.out_files_prefix + ".analyse_res", 'w')
out_file_stats = open(args.out_files_prefix + ".analyse_units", 'w')
eprint("writing to ", args.out_files_prefix + ".analyse_res", 
       args.out_files_prefix + ".analyse_units")

for in_file_name in in_file_names:
    signal = os.path.basename(in_file_name)
    eprint("processing", signal)
    values, counts, counts_non_zero, resolution = defaultdict(list), \
        defaultdict(int), defaultdict(int), defaultdict(int)
    examples_per_res = defaultdict(list)
    for l in open(in_file_name, 'r'):
        try:
            patid, eventdate, val, unit, source = l.strip().split('\t')
        except ValueError:
            eprint(l)
            raise
        val = float(val)
        if unit == "U/L": 
            unit = "IU/L" 
        counts[(unit, source)] += 1
        if val != 0.0:
            counts_non_zero[(unit, source)] += 1
            values[(unit, source)].append(val)
            my_res = get_res(val)
            resolution[my_res] += 1
            if len(examples_per_res[my_res]) < 5:
                examples_per_res[my_res].append(val)
    for k in sorted(resolution.keys()):
        print("\t".join(map(str, [signal, k, resolution[k]] + examples_per_res[k])), file=out_file_res)
        
    def analyze(vals, unit, source, count, count_non_zero, max_count):
        ''' print quartile, and all local maxes = values with frequencies higher than the frequency of their 10 neighbors from each side'''
        hist = defaultdict(int)
        for i in vals:
            hist[i] += 1
        keys = sorted(hist.keys())
        window_size = args.window_size
        local_maxes = [0] * len(keys)
        
        for i in range(len(keys)-window_size):
            local_maxes[i] = max([hist[keys[j]] for j in range(i,i+window_size)])
        found = []
        for i in range(window_size, len(keys)-window_size):
            if hist[keys[i]] > local_maxes[i-window_size] and hist[keys[i]] > local_maxes[i+1]:
                found.append((hist[keys[i]], keys[i]))
        found.sort(reverse=True)
        mom_str = moments_to_str(get_moments(vals))
        sta = [signal, source, unit, max_count, count, count_non_zero, len(keys), mom_str]
        sta += found[:3]
        print("\t".join(map(str, sta)), file=out_file_stats)
    
    max_count = max(counts.values()) if len(counts) > 0 else -1
    for k in counts.keys():
        if counts[k] < 200:
            continue
        unit, source = k[1], k[0]
        analyze(values[k], unit, source, counts[k], counts_non_zero[k],max_count)
        