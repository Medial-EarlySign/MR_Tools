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
parser.add_argument('--in_common_values_file', type=argparse.FileType('r'), required=True)
parser.add_argument('--out_per_ahdcode_folder', required=True)
parser.add_argument('--prac_ids', required=True)
args = parser.parse_args()

def clean_and_strip(x):
    return x.strip()

ahdcode_to_file = {}

eprint('reading common_values file:', args.in_common_values_file.name)
#for l in args.in_common_values_file:
    #ahdcode, count, count_non_zero = l.split()
    #count, count_non_zero = int(count), int(count_non_zero)
    #ahdcode_to_file[ahdcode] = open(args.out_per_ahdcode_folder + "/" +\
    #ahdcode, 'a')
args.in_common_values_file.close()

eprint('found', len(ahdcode_to_file), 'ahdcodes')

stats = {"processed": 0, "in_common_values": 0}

in_file_names = glob.glob(join(args.in_resolved_AHD_folder, args.prac_ids))
eprint("about to process", len(in_file_names), "files")
for in_filename in in_file_names:
    pracid = in_filename[-5:]
    eprint("reading from", in_filename)

    fp = open(in_filename, 'r')
    l = fp.readline()
    while( l is not None and len(l) > 0):
        patid, ahdcode, eventdate, the_value, unit = map(clean_and_strip, l.split('\t'))
        the_value = float(the_value)
        stats["processed"] += 1
        if ahdcode in ahdcode_to_file:
            stats["in_common_values"] += 1
            ahdcode_to_file[ahdcode] = open(args.out_per_ahdcode_folder + "/" +\
    ahdcode, 'a')
            print("\t".join([patid, eventdate, str(the_value), unit]), file=ahdcode_to_file[ahdcode])
            ahdcode_to_file[ahdcode].close()
        l = fp.readline()
    fp.close()
        
    eprint("processed", stats["processed"], "records")
        
for k, v in stats.iteritems():
    if type(v) is defaultdict:
        top_5 = sorted(v.items(), key=lambda x: x[1], reverse=True)[:5]
        eprint(k, len(v), "entries, top 5 are:", top_5)
    else:
        eprint(k, v)
        
    
    
    
