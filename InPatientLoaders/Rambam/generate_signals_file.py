#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import StringIO
import pandas as pd, numpy as np, os
from datetime import datetime
from shutil import copyfile, copy
from  medial_tools.medial_tools import eprint, read_file, write_for_sure
from common import write_as_dict

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/Ido/rambam_load/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

rules = read_file('correctedRules.txt', sep = '\t', encoding = 'utf-8', dtype=str)
rules[rules.columns] = rules.apply(lambda x: x.str.strip())
lab_signals = rules[rules.medial_signal_name != 'IGNORE'].groupby('medial_signal_name').head(1)
lab_signals.loc[:, 'signal'] = 'SIGNAL'
lab_signals.loc[:, 'sid'] = range(1000, 1000+lab_signals.shape[0])
lab_signals.loc[:, 'stype'] = '3'
lab_signals.loc[:, 'desc'] = '3'
lab_signals.loc[:, 'is_categorical'] = '0'
code_to_signal = read_file('code_to_signal', sep = '\t', names = ['medial_signal_name', 'medial_really_real_signal_name'])
lab_signals = pd.merge(lab_signals, code_to_signal, on = 'medial_signal_name', how = 'left')
lab_signals.loc[: , 'medial_really_real_signal_name'] = lab_signals.medial_really_real_signal_name.fillna(lab_signals.medial_signal_name) 

rfname = 'rambam_template.signals'
wfname = args.work_folder + 'repo_load_files/rambam.signals'
eprint('reading', rfname)
eprint('writing', wfname)
with open(rfname, 'r') as signals_template, open(wfname, 'w') as out_signals:
	o = signals_template.read()
	print(o, file=out_signals)
	s = StringIO.StringIO()
	lab_signals.to_csv(s, columns = ['signal', 'medial_really_real_signal_name', 'sid', 'stype', 'rambam_signal_name', 'is_categorical', 'medial_unit'], encoding='utf-8',
		index=False, sep='\t', header=False)
	print(s.getvalue(), file=out_signals)

rfname = 'rambam_template.convert_config'
wfname = args.work_folder + 'repo_load_files/rambam.convert_config'
eprint('reading', rfname)
eprint('writing', wfname)
with open(rfname, 'r') as template, open(wfname, 'w') as out:
	o = template.read()
	print(o, file=out)
	print("DIR\t" + args.work_folder + "/repo_load_files/", file=out)

d, target = "code_to_signal", args.work_folder + '/repo_load_files/'
eprint("copying", d, "target", target)
copy(d, target)
