from __future__ import print_function
from collections import defaultdict
from os.path import join
import glob
import argparse
from common import *

parser = argparse.ArgumentParser()
parser.add_argument('--in_AHDCodes_file', default='/server/Data/THIN1601/THINAncil1601/text/AHDCodes1601.txt',type=argparse.FileType('r'))
parser.add_argument('--in_AHDReadcodes_file', default='/server/Data/THIN1601/THINAncil1601/text/Readcodes1601.txt', type=argparse.FileType('r'))
parser.add_argument('--in_AHDlookups_file', default='/server/Data/THIN1601/THINAncil1601/text/AHDlookups1601.txt', type=argparse.FileType('r'))
parser.add_argument('--in_AHD_folder', default='/server/Data/THIN1601/THINDB1601/')
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'), required=True)
parser.add_argument('--out_folder', required=True)
parser.add_argument('--out_prefix', required=True)
parser.add_argument('--prac_ids', required=True)
args = parser.parse_args()

ahd_codes = read_ahd_codes(args.in_AHDCodes_file)

ahd_read_codes = read_ahd_read_codes(args.in_AHDReadcodes_file)

ahd_lookups = {'':'NA', '<None>':'<None>'}
for l in args.in_AHDlookups_file:
    dataname, datadesc, lookup, lookupdesc = \
    map(clean_and_strip, [l[0:8],l[8:38],l[38:44],l[44:144]])
    #print("\t".join([dataname, datadesc, lookup, lookupdesc]))
    ahd_lookups[lookup]=lookupdesc
eprint("found", len(ahd_lookups), "AHD lookups")

id2nr = read_id2nr(args.in_ID2NR_file)

out_raw_ahd_file_name = args.out_folder + "/NonNumeric/" + args.out_prefix + "_AHDCODE"
out_raw_ahd_file = file(out_raw_ahd_file_name, 'w')

in_file_names = glob.glob(join(args.in_AHD_folder, args.prac_ids))
eprint("about to process", len(in_file_names), "files")
for in_file_name in in_file_names:
    pracid = in_file_name[-5:]
    out_file_name = args.out_folder + "/Resolved/ahd.resolved." + pracid
    err_file_name = args.out_folder + "/Stats/ahd.resolve_err." + pracid
    eprint("reading from", in_file_name, "and writing to", out_file_name, err_file_name, out_raw_ahd_file_name)
    
    out_file = file(out_file_name, 'w')
    err_file = file(err_file_name, 'w')
    
    stats = {"unknown_id": 0,\
        "unknown_unit": defaultdict(int), "empty_num_result": defaultdict(int), 
        "invalid_num_result": defaultdict(int),
        "processed": defaultdict(int),
        "unknown_medcode": defaultdict(int), "bad_ahdflag": 0, "read": 0, "wrote_numeric": 0, "wrote_non_numeric": 0}
    out_data = []
    for l in file(in_file_name):
        stats["read"] += 1
        patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
        combid = pracid + patid
        if combid not in id2nr:
            #eprint("unknown combid [%s]" % combid)
            stats["unknown_id"] += 1
            continue
        if ahdflag != 'Y':
            stats["bad_ahdflag"] += 1
            continue 
        if medcode not in ahd_read_codes:
            stats["unknown_medcode"][medcode] += 1
            continue
        def get_full_ahd_name(medcode, ahdcode):
            full_ahd_name = ahd_read_codes[medcode] + '-' + medcode + '_' + ahd_codes[ahdcode]["desc"] + '-' + ahdcode
            full_ahd_name = full_ahd_name.replace('/', '_Over_').replace(':', '-').replace(' ', '_').replace('>', 'GreaterThan').replace('<', 'LessThan')
            return full_ahd_name
        if ahdcode in ahd_codes and ahd_codes[ahdcode]["data2"] == "NUM_RESULT" and ahd_codes[ahdcode]["datafile"] == "TEST" :
            full_ahd_name = get_full_ahd_name(medcode, ahdcode)
            if data2 is None or data2 == '':
                stats["empty_num_result"][full_ahd_name] += 1
                continue
            if not is_number(data2) :
                stats["invalid_num_result"][full_ahd_name] += 1
                continue
            if data3 not in ahd_lookups:
                stats["unknown_unit"][(full_ahd_name, data3)] += 1
                continue
            stats["processed"][full_ahd_name] += 1        
            units = ahd_lookups[data3]
            stats["wrote_numeric"] += 1
            l = [id2nr[combid], full_ahd_name, eventdate, data2, units]
            print("\t".join(map(str,l)), file=out_file)
        elif ahdcode in ['1001400217', '1001400156'] : #RBC red blood cell size and Immunoglobulin are specified as START_RNGE, END_RNGE
            full_ahd_name = get_full_ahd_name(medcode, ahdcode)
            if not is_number(data5) or not is_number(data6):
                stats["invalid_num_result"][full_ahd_name] += 1
                continue            
            stats["processed"][full_ahd_name] += 1
            stats["wrote_numeric"] += 2
            l = [id2nr[combid], "start_"+full_ahd_name, eventdate, data5, "NA"]
            print("\t".join(map(str,l)), file=out_file)
            l = [id2nr[combid], "end_"+full_ahd_name, eventdate, data6, "NA"]
            print("\t".join(map(str,l)), file=out_file)
        else:
            stats["wrote_non_numeric"] += 1
            out_data.append([id2nr[combid], "MEDCODE", eventdate, medcode])
    out_data.sort()
    for l in out_data:
        print("\t".join(map(str,l)), file=out_raw_ahd_file) 
    err_file = file(err_file_name, 'w')
    write_stats(stats, pracid, err_file)    

