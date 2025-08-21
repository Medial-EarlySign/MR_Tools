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

counts_per_patient = defaultdict(int)

out_file = file(args.out_filename, 'w')
eprint("writing to", args.out_filename)

for in_filename in in_file_names:
    pracid = in_filename[-5:]
    
    eprint("reading from", in_filename)
    prev_pat_id = -1
    min_date, max_date, cnt_records = '99999999', '00000000', 0
    for l in file(in_filename):
        patid, ahdcode, eventdate, the_value, unit = map(clean_and_strip, l.split('\t'))
        if patid != prev_pat_id:
            print(prev_pat_id, min_date, max_date, cnt_records, file=out_file)
            min_date, max_date, cnt_records = '99999999', '00000000', 0
            prev_pat_id = patid
        min_date = min(min_date, eventdate)
        max_date = max(max_date, eventdate)
        cnt_records+=1
        
            
    
    
