from __future__ import print_function
from collections import defaultdict
from os.path import join
import glob
import argparse
from common import *

parser = argparse.ArgumentParser()
parser.add_argument('--in_extracted_RDW_file', default='/server/Data/THIN1601/AHD_extract_for_AHDcode_1001400217.txt')
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'), required=True)
parser.add_argument('--out_file', required=True)
parser.add_argument('--err_file', required=True)
args = parser.parse_args()

id2nr = read_id2nr(args.in_ID2NR_file)

def parse_AHD_1001400217_line(l):
    return map(clean_and_strip, [l[0:5],l[5:9],l[9:17],l[27:28],l[152:165]])

eprint("reading from", args.in_extracted_RDW_file, "and writing to", args.out_file, args.err_file)
   
out_file = file(args.out_file, 'w')
err_file = file(args.err_file, 'w')

stats = {"unknown_id": 0,\
	"empty_num_result": defaultdict(int), 
	"invalid_num_result": defaultdict(int),
	"processed": defaultdict(int),
	"bad_ahdflag": 0, "read": 0, "wrote_numeric": 0}

full_ahd_name = "42Z7.00_RBC_red_blood_cell_size-1001400217"
for l in file(args.in_extracted_RDW_file):
	stats["read"] += 1
	pracid, patid, eventdate, ahdflag, rbc_size_val = parse_AHD_1001400217_line(l)
	if stats["read"] < 5:
		eprint(pracid, patid, eventdate, ahdflag, rbc_size_val)
	combid = pracid + patid
	if combid not in id2nr:
		#eprint("unknown combid [%s]" % combid)
		stats["unknown_id"] += 1
		continue
	if ahdflag != 'Y':
		stats["bad_ahdflag"] += 1
		continue 
	if rbc_size_val is None or rbc_size_val == '':
		stats["empty_num_result"][full_ahd_name] += 1
		continue
	if not is_number(rbc_size_val) :
		stats["invalid_num_result"][full_ahd_name] += 1
		continue
	stats["processed"][full_ahd_name] += 1
	stats["wrote_numeric"] += 1
	l = [id2nr[combid], eventdate, rbc_size_val, "NA", full_ahd_name]
	print("\t".join(map(str,l)), file=out_file)
write_stats(stats, "all", err_file)    

