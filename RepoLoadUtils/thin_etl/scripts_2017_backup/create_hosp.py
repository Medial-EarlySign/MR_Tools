#!/bin/python
import sys, os, io
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from Configuration import Configuration
from signal_full_api import *
from flow_api import getLines
from common import *
from create_dictionaries import *

"""
cfg = Configuration()
out_folder = fixOS(cfg.work_path)
raw_path = fixOS(cfg.doc_source_path)
data_path = fixOS(cfg.raw_source_path)
lines = getLines(out_folder, 'ID2NR_fixed')
id2nr = read_id2nr(lines)

if not(os.path.exists( os.path.join(out_folder, 'medical' ))):
    os.makedirs(os.path.join(out_folder, 'medical'))

in_file_names = list(filter(lambda f: f.startswith('medical.') ,os.listdir(data_path)))
eprint("about to process", len(in_file_names), "files")


nhsspec_file_name = os.path.join(out_folder, 'medical',  "NHSSPEC")

nhsspec_file = io.open(nhsspec_file_name, 'w', newline = '')
load_stats_fp = open(os.path.join(out_folder, 'medical', 'nsp_prac.stats'), 'w')

flags_inpatien = set(map(lambda c:c ,'gaZVSGHAD'))
flags_outpatient = set(map(lambda c:c ,'CERIKPY1')) 
flags_day_case = set(map(lambda c:c ,'BWbkp'))
cat_to_name = dict()
cat_to_name['INPATIENT'] = flags_inpatien
cat_to_name['OUTPATIENT'] = flags_outpatient
cat_to_name['DAY_CASE'] = flags_day_case
flags_all = set()
for tmp, flags in cat_to_name.items():
    flags_all.update(flags)
# main loopll med       
for in_filename in in_file_names:
    pracid = in_filename[-5:]
    eprint("reading from %s, pracid = %s" % (in_filename, pracid))
    stats = {"unknown_id": 0, "invalid_medflag":0, "read": 0, "wrote": 0}
    out_data = []
    fp = open(os.path.join(data_path, in_filename) ,'r')
    fp_lines = fp.readlines()
    fp.close()
    for l in fp_lines:
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
        
        if len(nhsspec) > 0 and nhsspec != "000" and source in flags_all:
            fl = None
            for cat, flags in cat_to_name.items():
                if source in flags:
                    fl = cat
                    break
            if fl is None:
                raise NameError('coudn''t find category')
            out_data.append([id2nr[combid], "NHSSPEC", eventdate, nhsspec, fl])

    write_stats(stats, pracid, load_stats_fp)
    out_data.sort()
    for l in out_data:
        nhsspec_file.write(unicode("\t".join(map(str,l))+ '\n'))
print('Done creating initiale files')
nhsspec_file.close()
"""
#load_hospitalizations()
create_hospitalization_dict()