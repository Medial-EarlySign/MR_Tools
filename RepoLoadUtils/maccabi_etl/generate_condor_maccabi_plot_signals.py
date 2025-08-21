#!/usr/bin/python

from __future__ import print_function
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--condor_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/maccabi_etl/condor_plot_signals.txt')
parser.add_argument('--all_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/maccabi_etl/all.signals')
parser.add_argument('--codes_to_signals_file', default='/server/Work/Users/Ido/MACCABI_ETL/load/maccabi_mar2017/codes_to_signal_names')

args = parser.parse_args()

header = """universe = vanilla
rank = memory
request_memory = 10000
Requirements = Machine == "node-02.medials.local"
should_transfer_files = NO
log = plot_signals.log
request_cpus = 6
executable = /server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/plot_signal.py """

print ("writing", args.condor_file)
all_signals = pd.read_csv(args.all_signals_file, names = ['sig'], dtype = {'sig':str})
all_signals = all_signals.sort_values('sig')
codes_to_signals = pd.read_csv(args.codes_to_signals_file, names = ['code', 'sig'], sep = '\t', dtype = {'sig':str})
j = pd.merge(all_signals, codes_to_signals, on = 'sig', how = 'left')
j.loc[:, 'fname'] = j.apply(lambda x: x['sig'] if pd.isnull(x['code']) else x['code'], axis = 1)
with open(args.condor_file, 'w') as condor_file:
	print(header, file = condor_file)
	def gen_submit(x):
		print('arguments = " --do_series_per_origin=0 --sig ' + x['fname'] + ',' + x['sig'] + ' --in_signal_files=lab_fixed_res/* --out_file_prefix plots/' + x['sig'] + ' " ', file = condor_file)
		print("error = log/" + x['sig'] + ".err" , file = condor_file)
		print("output = log/" + x['sig'] + ".out" , file = condor_file)
		print("queue" , file = condor_file)
	j.apply(gen_submit, axis = 1)

