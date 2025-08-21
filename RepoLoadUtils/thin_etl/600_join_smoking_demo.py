from __future__ import print_function
import argparse
import glob
from common import *

parser = argparse.ArgumentParser()
parser.add_argument('--in_AHDReadcodes_file', default='/server/Data/THIN1601/THINAncil1601/text/Readcodes1601.txt', type=argparse.FileType('r'))
parser.add_argument('--in_demo_file', default='/server/Work/Users/Ido/THIN_ETL/thin_demographic', type=argparse.FileType('r'))
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'), required=True)
parser.add_argument('--in_AHD_files_prefix', required=True)
parser.add_argument('--out_files_prefix', required=True)
args = parser.parse_args()

err_file_name = args.out_files_prefix + "_STAT_SMOKING_JOIN"
err_file = file(err_file_name, 'w')
out_file_name = args.out_files_prefix + "_SMOKING_JOIN"
out_file = file(out_file_name, 'w')
eprint("writing to", err_file_name, out_file_name)


ahd_read_codes = read_ahd_read_codes(args.in_AHDReadcodes_file)
id2nr = read_id2nr(args.in_ID2NR_file)

def read_demo_line(prev_demo_patid):
    demo_l = args.in_demo_file.readline().strip()
    if len(demo_l) == 0:
        raise
    demo_patid, demo_signal, demo_val = demo_l.split()
    demo_patid = int(demo_patid)
    if prev_demo_patid > demo_patid:
        eprint("ERROR! previous demo_patid %d > current demo_patid %d" % 
        (prev_demo_patid, demo_patid))
        raise
    return demo_patid, demo_signal, demo_val
    
demo_patid = -1

in_file_names = glob.glob(args.in_AHD_files_prefix)
eprint("about to process", len(in_file_names), "files")
for in_file_name in in_file_names:
    pracid = in_file_name[-5:]
    eprint("reading from", in_file_name)

    stats = {"unknown_id": 0,\
        "bad_ahdflag": 0, "demo_read": 0, "demo_skipped": 0, "demo_miss": 0, "ahd_read": 0, "wrote": 0}

    print("\t".join("numerator yob sex evntdate data1 data2 data5 data6 medcode desc".split()), file=out_file)
    for l in file(in_file_name):            
        patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
        combid = pracid + patid
        if combid not in id2nr:
            stats["unknown_id"] += 1
            continue
        if ahdflag != 'Y':
            stats["bad_ahdflag"] += 1
            continue
        if ahdcode != "1003040000":
            continue
        
        stats["ahd_read"] += 1
            
        patid = id2nr[combid]
        while demo_patid < patid:
            # new smoking patient, reset values and look for patient id in demo
            stats["demo_skipped"] += 1
            demo_yob, demo_enddate, demo_gender = None, None, None 
            demo_patid, demo_signal, demo_val = read_demo_line(demo_patid)
                
        while demo_patid == patid:
            # try to extract the demographics we need
            if demo_signal == 'BYEAR':
                demo_yob = int(demo_val)
            if demo_signal == 'GENDER':
                demo_gender = int(demo_val)
            if demo_signal == 'ENDDATE':
                demo_enddate = int(demo_val[:4])
            if all(x is not None for x in [demo_yob, demo_enddate, demo_gender]):
                break
            stats["demo_read"] += 1            
            demo_patid, demo_signal, demo_val = read_demo_line(demo_patid)
            
        if all(x is not None for x in [demo_yob, demo_enddate, demo_gender]) and demo_patid == patid:
            # if we have the demo we need            
            print("\t".join(map(str,[patid, str(demo_yob) + "0000", demo_gender, eventdate, data1, data2, data5, data6, medcode, ahd_read_codes[medcode]])), file=out_file)
        else:
            stats["demo_miss"] += 1
    write_stats(stats, pracid, err_file)
    
