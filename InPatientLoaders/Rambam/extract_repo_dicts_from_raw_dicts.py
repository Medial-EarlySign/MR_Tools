#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import pandas as pd, numpy as np, os
import glob
from datetime import datetime
from shutil import copyfile, copy
from  medial_tools.medial_tools import eprint, read_file, write_for_sure
from common import write_as_dict, rambam_str_to_dict

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/Ido/rambam_load/')
parser.add_argument('--code_folder', default='/server/UsersData/{user}/MR/Tools/InPatientLoaders/Rambam/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

directory =  args.work_folder + 'repo_load_files/dicts/'
if not os.path.exists(directory):
	os.mkdir(directory);

# hmo and nationality

orig_dict_name = 'nationality'
section = 'INSURANCE'
new_dict_name = 'insurance'
def handle_demo_dict(orig_dict_name, section, new_dict_name):
	n = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.' + orig_dict_name, sep = '\t', names = ['a', 'b'], dtype=str)
	n[n.columns] = n.apply(lambda x: x.str.strip())
	n = n[n.a != 'Null']
	n['numeric_code'] = n.a
	n1 = n[['numeric_code', 'b']]
	n1.columns = ['numeric_code', 'desc']
	n1['pri'] = 1
	n2 = n[['numeric_code', 'a']]
	n2.columns = ['numeric_code', 'desc']
	n2['pri'] = 2
	write_as_dict(pd.concat([n1, n2]), "SECTION\t" + section, args.work_folder + '/repo_load_files/dicts/dict.' + new_dict_name)
handle_demo_dict('nationality', 'ETHNICITY', 'ethnicity')
handle_demo_dict('hmo', 'INSURANCE', 'insurance')

# procedure
############

sc = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.servicecode', sep = '\t', names = ['a', 'b'], dtype=str)
pc = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.performedprocedurecode', sep = '\t', names = ['a', 'b'], dtype=str)
sc[sc.columns] = sc.apply(lambda x: x.str.strip())
pc[pc.columns] = pc.apply(lambda x: x.str.strip())

spc = pd.concat([sc, pc]).sort_values('b',ascending=True).groupby('a').head(1)
spc.loc[:, 'numeric_code'] = range(1000, 1000 + spc.shape[0])
outme = pd.DataFrame({'numeric_code': spc.numeric_code, 'desc': 'PROC_ID:' + spc.a, 'pri':1})
outme = pd.concat([outme, pd.DataFrame({'numeric_code': spc.numeric_code, 'desc': spc.b, 'pri':2})])
write_as_dict(outme, "SECTION\tPROCEDURE", args.work_folder + '/repo_load_files/dicts/dict.procedurecode')

# diagnosis
############

dc = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.conditioncode', sep = '\t', names = ['code', 'desc'], dtype=str)
dc.loc[:, 'numeric_code'] = range(1000, 1000 + dc.shape[0])

def extract_short_desc(x):
	if "~" not in x:
		return None
	d = rambam_str_to_dict(x)
	ret =  "DIAG_ID:" + d[0] 
	if d[2] != d[0]:
		ret += "_ICD10:" + d[2]
	elif d[4] != d[0]:
		ret += "_ICD10:" + d[4]
	ret += "_" + "DESC:" + d[1]
	return ret

dc.loc[:, 'short_desc'] = dc.desc.apply(extract_short_desc)
outme = pd.DataFrame({'numeric_code': dc.numeric_code, 'desc':'DIAG_ID:' + dc.code, 'pri': 0})
outme = pd.concat([outme, pd.DataFrame({'numeric_code': dc.numeric_code, 'desc':dc.short_desc, 'pri': 1})])

write_as_dict(outme, "SECTION\tDIAGNOSIS", args.work_folder + '/repo_load_files/dicts/dict.diagnosiscode')


# build ICD10 hierarchy 

seen_codes = set([])
defs = []
hier = []
i = 10000
def build_hier(x):
	global i
	if "~" not in x['desc']:
		return None
	d = rambam_str_to_dict(x['desc'])
	prev_code = 'DIAG_ID:' + x['code'] # code x['short_desc']
	seen_codes.add(x['short_desc'])
	for lev in [2,4,6,8,9]:
		if lev < 4:
			code = 'DIAG_ID:' + str(d[lev]) + '_DESC:' + str(d[lev+1])
		elif lev < 8:
			code = 'ICD10:' + str(d[lev]) + '_DESC:' + str(d[lev+1])
		else:
			code = 'DESC:' + str(d[lev])
		if code != prev_code:
			hier.append({'numeric_code': code, 'desc': prev_code, 'pri': 0})
		if code not in seen_codes:
			seen_codes.add(code)
			defs.append({'numeric_code': i, 'desc': code, 'pri': 0})
			i+=1
		prev_code = code
	return
dc.apply(build_hier, axis = 1)		 

defs = pd.DataFrame(defs)
hier = pd.DataFrame(hier)
write_as_dict(defs, "SECTION\tDIAGNOSIS", args.work_folder + '/repo_load_files/dicts/dict.icd10_defs')
#write_for_sure(hier, args.work_folder + '/repo_load_files/dicts/dict.icd10_sets')
write_as_dict(hier, "SECTION\tDIAGNOSIS", args.work_folder + '/repo_load_files/dicts/dict.icd10_sets', prefix='SET')


# department
############

dep = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.departmentcode', sep = '\t', names = ['code', 'desc'], dtype=str)
dep.loc[:, 'numeric_code'] = range(1000, 1000 + dep.shape[0])
outme = pd.DataFrame({'numeric_code': dep.numeric_code, 'desc':'DEP_ID:' + dep.code, 'pri': 0})
outme = pd.concat([outme, pd.DataFrame({'numeric_code': dep.numeric_code, 'desc':'DESC:' + dep.desc, 'pri': 1})])

write_as_dict(outme, "SECTION\tSTAY", args.work_folder + '/repo_load_files/dicts/dict.departmentcode')

# microbiology
############

mb = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/microbiology.dict', sep = '\t', names = ['desc'], dtype=str)
mb.loc[:, 'numeric_code'] = range(1000, 1000 + mb.shape[0])
outme = pd.DataFrame({'numeric_code': mb.numeric_code, 'desc':mb.desc, 'pri': 0})

write_as_dict(outme, "SECTION\tMICROBIOLOGY", args.work_folder + '/repo_load_files/dicts/dict.microbiology')

# copy small hand-crafted dicts
############
for d in glob.glob(args.code_folder + "/dict.*"):
	eprint("copying", d)
	copy(d, args.work_folder + '/repo_load_files/dicts/')
