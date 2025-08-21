from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import glob

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('--in_resolved_AHD_folder', required=True)
parser.add_argument('--out_filename', required=True)
parser.add_argument('--prac_ids', required=True)
args = parser.parse_args()

def clean_and_strip(x):
    return x.strip()

stats = {"processed": 0}

in_file_names = glob.glob(join(args.in_resolved_AHD_folder, args.prac_ids))
eprint("about to process", len(in_file_names), "files")

counts = defaultdict(int)
counts_non_zero = defaultdict(int)

for in_filename in in_file_names:
    pracid = in_filename[-5:]
    
    eprint("reading from", in_filename)
    for l in file(in_filename):
        patid, ahdcode, eventdate, the_value, unit = map(clean_and_strip, l.split('\t'))
        the_value = float(the_value)
        counts[ahdcode]+= 1
        if the_value != 0.0:
            counts_non_zero[ahdcode]+= 1
        stats["processed"]+=1
        
    eprint("processed", stats["processed"], "records")
        
out_file = file(args.out_filename, 'w')
eprint("writing to", args.out_filename)
#print("\t".join(['ahdcode', 'count', 'count_non_zero']), file=out_file)
for k, v in counts.iteritems():
    print("\t".join([k, str(v), str(counts_non_zero[k])]), file=out_file)
        
    
    
    
