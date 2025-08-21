#!/usr/bin/python

from __future__ import print_function
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--condor_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/condor_plot_signals.txt')
parser.add_argument('--all_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/all.signals')
parser.add_argument('--codes_to_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/codes_to_signals')
parser.add_argument('--completions_file', default='ahd/Completions_20170315/thin_completed.csv')

args = parser.parse_args()

header = """universe = vanilla
rank = memory
request_memory = 10000
Requirements = Machine == "node-02.medials.local" || Machine == "node-01.medials.local"
should_transfer_files = NO
log = plot_signals.log
request_cpus = 6
executable = /server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/plot_signal.py """

print('reading', args.all_signals_file)
print('reading', args.codes_to_signals_file)
print('completions file:', args.completions_file)
print('will write', args.condor_file)

all_signals = pd.read_csv(args.all_signals_file, names = ['sig'])
all_signals = all_signals.sort_values('sig')
codes_to_signals = pd.read_csv(args.codes_to_signals_file, names = ['code', 'sig'], sep = '\t')
j = pd.merge(all_signals, codes_to_signals, on = 'sig', how = 'left')
j.loc[:, 'fname'] = j.apply(lambda x: x['sig'] if pd.isnull(x['code']) else x['code'], axis = 1)
with open(args.condor_file, 'w') as condor_file:
    print(header, file = condor_file)
    def gen_submit(x):
        cmd = 'arguments = " --sig ' + x['fname'] + ',' + x['sig'] + ' --in_signal_files=ahd/Fixed/' + x['fname']
        if len(args.completions_file) > 0:
            cmd += "," + args.completions_file
        cmd += ' --out_file_prefix ahd/plots/' + x['sig'] + ' " '
        print(cmd, file = condor_file)
        print("error = log/" + x['sig'] + ".err" , file = condor_file)
        print("output = log/" + x['sig'] + ".out" , file = condor_file)
        print("queue" , file = condor_file)
    j.apply(gen_submit, axis = 1)

