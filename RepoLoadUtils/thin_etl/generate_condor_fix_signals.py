#!/usr/bin/python

from __future__ import print_function
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--condor_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/condor_fix_signals.txt')
parser.add_argument('--all_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/problematic.signals')
parser.add_argument('--codes_to_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/codes_to_signals')

args = parser.parse_args()

header = """universe = vanilla
rank = memory
request_memory = 10000
Requirements = Machine == "node-02.medials.local" || Machine == "node-01.medials.local"
should_transfer_files = NO
log = fix_signals.log
request_cpus = 6
executable = /server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/signal_fix_api.py """

print('reading', args.all_signals_file)
print('reading', args.codes_to_signals_file)
print('will write', args.condor_file)

all_signals = pd.read_csv(args.all_signals_file, names = ['sig'])
all_signals = all_signals.sort_values('sig')
codes_to_signals = pd.read_csv(args.codes_to_signals_file, names = ['code', 'sig'], sep = '\t')
j = pd.merge(all_signals, codes_to_signals, on = 'sig', how = 'left')
j.loc[:, 'fname'] = j.apply(lambda x: x['sig'] if pd.isnull(x['code']) else x['code'], axis = 1)

with open(args.condor_file, 'w') as condor_file:
	print(header, file = condor_file)
	def gen_submit(x):
		print('arguments = " ' + x['fname']  + ' " ', file = condor_file)
		print("error = log/fix_" + x['sig'] + ".err" , file = condor_file)
		print("output = log/fix_" + x['sig'] + ".out" , file = condor_file)
		print("queue" , file = condor_file)
	j.apply(gen_submit, axis = 1)

