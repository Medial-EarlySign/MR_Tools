from __future__ import print_function
from collections import defaultdict
import sys
import argparse
import glob
from common import *

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    
parser = argparse.ArgumentParser()
parser.add_argument('--in_PVI_files_prefix', required=True)
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'), default='/server/Work/Users/Ido/THIN_ETL/ID2NR')
parser.add_argument('--in_PVI_def_file', type=argparse.FileType('r'), default='/server/Work/Users/Ido/THIN_ETL/pvi/distinct_pvi_flags_def')
parser.add_argument('--out_files_prefix', required=True)
args = parser.parse_args()

id2nr = read_id2nr(args.in_ID2NR_file)

err_file_name = args.out_files_prefix + "pvi_stat"
err_file = file(err_file_name, 'w')
out_file_name = args.out_files_prefix + "PVI"
out_file = file(out_file_name, 'w')
eprint("writing to", err_file_name, out_file_name)

in_file_names = glob.glob(args.in_PVI_files_prefix)
eprint("about to process", len(in_file_names), "files")
for in_file_name in in_file_names:
    pracid = in_file_name[-5:]
    eprint("reading from", in_file_name)
    stats = {"unknown_id": 0, "read": 0, "wrote": 0}    
    data = defaultdict(list)
    for l in file(in_file_name):
        stats["read"] += 1
        patid, flags, eventdate = l[0:4],l[4:16],l[16:24]
        combid = pracid + patid
        if combid not in id2nr:
            stats["unknown_id"] += 1
            continue
        print("\t".join(map(str, [id2nr[combid], "PVI", eventdate, "PVI_" + flags])), file=out_file)
            
write_stats(stats, pracid, err_file)
    
