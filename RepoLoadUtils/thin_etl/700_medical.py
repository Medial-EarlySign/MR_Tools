from __future__ import print_function
import glob
import argparse
from common import * 

parser = argparse.ArgumentParser()
parser.add_argument('--in_medical_files', required=True)
parser.add_argument('--in_ID2NR_file', required=True, type=argparse.FileType('r'))
parser.add_argument('--out_signals_prefix', required=True)
args = parser.parse_args()

id2nr = read_id2nr(args.in_ID2NR_file)

in_file_names = glob.glob(args.in_medical_files)
eprint("about to process", len(in_file_names), "files")

medcode_file_name = args.out_signals_prefix + "MEDCODE"
nhsspec_file_name = args.out_signals_prefix + "NHSSPEC"
eprint("writing to %s, %s" % (medcode_file_name, nhsspec_file_name))

medcode_file = file(medcode_file_name, 'w')
nhsspec_file = file(nhsspec_file_name, 'w')

# main loop
for in_filename in in_file_names:
    pracid = in_filename[-5:]
    eprint("reading from %s, pracid = %s" % (in_filename, pracid))
    
    stats = {"unknown_id": 0, "invalid_medflag":0, "read": 0, "wrote": 0}
    
    out_data = [[], []]
    
    for l in file(in_filename):
        stats["read"] += 1
        patid, eventdate, enddate, datatype, medcode, medflag, staffid, source,\
        episode, nhsspec, locate, textid, category, priority, medinfo, inprac,\
        private, medid, consultid, sysdate, modified =\
        parse_medical_line(l)
        
        combid = pracid + patid
        if combid not in id2nr:
            stats["unknown_id"] += 1
            continue
        if medflag not in ['R', 'S']:
            stats["invalid_medflag"] += 1
            continue
        out_data[0].append([id2nr[combid], "MEDCODE", eventdate, medcode])
        if len(nhsspec) > 0 and nhsspec != "000":
            out_data[1].append([id2nr[combid], "NHSSPEC", eventdate, nhsspec])

    for i, f in enumerate([medcode_file, nhsspec_file]):
        out_data[i].sort()
        for l in out_data[i]:
            print("\t".join(map(str,l)), file=f)