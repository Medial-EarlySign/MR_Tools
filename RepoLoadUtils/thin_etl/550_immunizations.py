from __future__ import print_function
from collections import defaultdict
import glob
import argparse
from common import *

parser = argparse.ArgumentParser()
parser.add_argument('--in_AHDCodes_file', default='/server/Data/THIN1601/THINAncil1601/text/AHDCodes1601.txt',type=argparse.FileType('r'))
parser.add_argument('--in_AHD_files_prefix', required=True)
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'), required=True)
parser.add_argument('--out_files_prefix')
args = parser.parse_args()

id2nr = read_id2nr(args.in_ID2NR_file)

ahd_codes = read_ahd_codes(args.in_AHDCodes_file)

err_file_name = args.out_files_prefix + "imms_stat"
err_file = file(err_file_name, 'w')
out_file_name = args.out_files_prefix + "IMMS"
out_file = file(out_file_name, 'w')
eprint("writing to", err_file_name, out_file_name)

in_file_names = glob.glob(args.in_AHD_files_prefix)
eprint("about to process", len(in_file_names), "files")
for in_file_name in in_file_names:
    pracid = in_file_name[-5:]
    eprint("reading from", in_file_name)
    
    stats = {"unknown_id": 0, "bad_ahdflag": 0, "read": 0, "wrote": 0}
    
    data = defaultdict(list)
    for l in file(in_file_name):
        stats["read"] += 1
        patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
        combid = pracid + patid
        if combid not in id2nr:
            stats["unknown_id"] += 1
            continue
        if ahdflag != 'Y':
            stats["bad_ahdflag"] += 1
            continue
        if ahdcode in ahd_codes and ahd_codes[ahdcode]["datafile"] == "IMMS":
            print("\t".join([id2nr[combid], "IMMS", eventdate, ahd_codes[ahdcode]["desc"]]), file=out_file)
            
write_stats(stats, pracid, err_file)
    
