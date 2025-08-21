#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import pandas as pd, numpy as np, os
from datetime import datetime
from  medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/Ido/rambam_load/')
parser.add_argument('--id2nr', default='/nas1/Work/Users/Coby/rambam/id2nr')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

FMT = '%Y%m%d%H%M'
start = datetime.strptime('190001010000', FMT)
def translate_to_minutes_since_1900(x):
	end = datetime.strptime(str(x), FMT)
	return int((end-start).total_seconds()//60)


id2nr = read_file(args.id2nr, sep = '\t', names = ['pid', 'orig_pid'], limit_records=args.limit_records)

train = pd.DataFrame({'pid': id2nr.pid})
def allocate_train(x):
	d = int(x % 100)
	if d < 70:
		return 1
	elif d < 90:
		return 2
	else:
		return 3

train.loc[:, 'TRAIN'] = train.pid.apply(allocate_train)
train.loc[:, 'sig'] = 'TRAIN'

write_for_sure(train, args.work_folder + '/repo_load_files/rambam_train', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'TRAIN'])

demo = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/rambam_demographics', sep = '\t', names = ['pid', 'sig', 'val'], limit_records=args.limit_records)

def translate_signal_names(x):
	if x == 'gendercode':
		return 'GENDER'
	elif x == 'hmo':
		return 'INSURANCE'
	elif x == 'deceaseddate':
		return 'DEATH'
	elif x == 'birthdate':
		return 'BDATE'
	elif x == 'nationality':
		return 'ETHNICITY'
	else:
		return 'UNKNOWN'

demo.loc[:, 'sig'] = demo.sig.apply(translate_signal_names)
demo = demo [ ~pd.isnull(demo.val) & (demo.sig != 'UNKNOWN') & (demo.val != 'None') ]

byear = demo[demo.sig == 'BDATE']
byear.loc[:, 'sig'] = 'BYEAR'
def get_year(x):
	return int(x[:4])
byear.loc[:, 'val'] = byear.val.apply(get_year)

nation = demo[demo.sig == 'ETHNICITY']
insu = demo[demo.sig == 'INSURANCE']

demo = pd.concat([demo, byear, nation, insu])

write_for_sure(demo.sort_values(['pid', 'sig']), 
	args.work_folder + '/repo_load_files/rambam_demographics', sep = '\t', index = False, header = False)


visits = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/rambam_visits', sep = '\t', limit_records=args.limit_records, dtype=str)

stays = visits[visits.ev_type == 'ev_transfers'][['pid', 'startdate', 'enddate','departmentcode']]
out_stays = visits[visits.ev_type == 'ev_outpatient_visits'][['pid', 'startdate','departmentcode']]
out_stays.loc[:, 'enddate'] = out_stays.startdate
stays = pd.concat([stays, out_stays])
stays.loc[:, 'departmentcode'] = "DEP_ID:" + stays.departmentcode
stays.loc[:, 'emr'] = 'EMR_ID:rambam'
stays.loc[:, 'sig'] = 'STAY'
def move_enddate_one_day_forward(x):
    if x.endswith("00:00:00"):
        x = x[:-8] + "23:59:59"
    return x
stays.loc[stays.startdate > stays.enddate, 'enddate'] = stays.enddate.apply(move_enddate_one_day_forward)

write_for_sure(stays.sort_values(['pid', 'startdate']), args.work_folder + '/repo_load_files/rambam_stays', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'startdate', 'enddate', 'departmentcode', 'emr'])

adm = visits[visits.ev_type == 'ev_admissions'][['pid', 'startdate', 'enddate', 'admissionsourcecode']]
adm.loc[:, 'admission_id'] = "1"
adm.loc[:, 'sig'] = 'ADMISSION'

write_for_sure(adm.sort_values(['pid', 'startdate']), args.work_folder + '/repo_load_files/rambam_admissions', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'startdate', 'enddate', 'admission_id'])

adm.loc[:, 'sig'] = 'ADMISSION_TYPE'
adm.loc[:, 'admissionsourcecode'] = "ADMTYPE_ID:" + adm.admissionsourcecode
write_for_sure(adm.sort_values(['pid', 'startdate']), args.work_folder + '/repo_load_files/rambam_admission_type', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'startdate', 'admissionsourcecode'])

diag = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/rambam_diagnoses', sep = '\t', limit_records=args.limit_records)
diag = diag[diag.ev_type == 'ev_diagnoses']
diag.loc[:, 'sequencenumber'] = 'DTYPE_ID:' + diag.sequencenumber.astype(str)
diag.loc[:, 'conditioncode'] = 'DIAG_ID:' + diag.conditioncode.astype(str)
diag = diag[['pid', 'ev_time', 'conditioncode', 'sequencenumber']]
diag.loc[:, 'sig'] = 'DIAGNOSIS'

write_for_sure(diag.sort_values(['pid', 'ev_time', 'sequencenumber']), args.work_folder + '/repo_load_files/rambam_diagnoses', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'ev_time', 'conditioncode', 'sequencenumber'])

all_procs = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/rambam_procedures', sep = '\t', limit_records=args.limit_records, dtype=str)
surg = all_procs[all_procs.ev_type == 'ev_surgeries'][['pid', 'executiondate', 'performedprocedurecode', 'surgerytype']]
proc = all_procs[all_procs.ev_type == 'ev_procedures'][['pid', 'startdate', 'servicecode', 'prefix']]
ins = all_procs[all_procs.ev_type == 'ev_institutes'][['pid', 'dateperformed', 'servicecode']]
ins.loc[:, 'proctype'] = 'INSTITUTE'
for df in [proc, surg, ins]:
	df.columns = ['pid', 'date', 'proccode', 'proctype']

all_procs = pd.concat([surg, proc, ins])
all_procs.loc[:, 'sig'] = 'PROCEDURE'
all_procs.loc[:, 'proctype'] = all_procs.proctype.apply(lambda x: "PTYPE_ID:" + str(x))
all_procs.loc[:, 'proccode'] = all_procs.proccode.apply(lambda x: "PROC_ID:" + str(x))
write_for_sure(all_procs.sort_values(['pid', 'date',]), args.work_folder + '/repo_load_files/rambam_procedures', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'date', 'proccode', 'proctype'])

