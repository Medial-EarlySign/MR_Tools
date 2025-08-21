from __future__ import print_function
from collections import defaultdict
import sys
import argparse
import pandas as pd
from get_moments import get_moments, moments_to_str

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_completions_file', required=True)
args = parser.parse_args()

def clean_and_strip(x):
    return x.strip()

df = pd.read_csv(args.in_completions_file, names = ['pid', 'signal', 'date', 'val'], sep = '\t')
for sig in df.signal.unique():
    print(sig)
    vals = df[df.signal == sig].val
    mom_str = moments_to_str(get_moments(vals))
    print(sig, mom_str)
        