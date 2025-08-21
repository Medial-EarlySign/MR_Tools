#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import pandas as pd, numpy as np, os
import glob, time
import pwd
from datetime import datetime
from shutil import copyfile, copy
from  medial_tools.medial_tools import eprint, read_file, write_for_sure , run_cmd_and_print_outputs
import sys
condor_pragma_omp_lib = os.environ['MR_ROOT'] + "/Libs/Internal/python_condor_pragma_omp/"
sys.path.append(condor_pragma_omp_lib)
from condor_pragma_omp import before_condor_loop, start_condor_loop, end_condor_loop, after_condor_loop

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/ido/rambam_load/')
parser.add_argument('--in_condor_runner_template', default=condor_pragma_omp_lib + 'condor_runner_template.txt')
parser.add_argument('--do_condor_flag', type=int, default=1)
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

if not args.work_folder.endswith('/'):
	args.work_folder = args.work_folder + "/"
run_id = "run_" + time.strftime("%Y_%m_%d_%H%M%S")
condor_folder = args.work_folder + "condor/"

condor_filename, condor_file = before_condor_loop(args.do_condor_flag, condor_folder, run_id, args.in_condor_runner_template)

for n in range(20):
	i = str(n)
	cmd_filename, cmd_file = start_condor_loop(args.do_condor_flag, condor_folder, i, run_id)
	cmd = " python microbiologyToLoadingFormat.py {i} 20 {work_folder} > {work_folder}/temp/tempMB{i}.txt ".format(i=i, work_folder=args.work_folder)
	print(cmd, file=cmd_file)
	cmd = " python RulesToLoadingFormat.py {i} 20 {correctedRules} > {work_folder}/temp/tempME{i}.txt ".format(i=i, work_folder=args.work_folder, correctedRules="correctedRules.txt")
	print(cmd, file=cmd_file)
	cmd = " python RulesToLoadingFormatLabs.py {i} 20 {correctedRules} > {work_folder}/temp/tempL{i}.txt ".format(i=i, work_folder=args.work_folder, correctedRules="correctedRules.txt")
	print(cmd, file=cmd_file)
	end_condor_loop(args.do_condor_flag, condor_folder, i, run_id, cmd_filename, cmd_file, condor_filename, condor_file)

after_condor_loop(args.do_condor_flag, condor_folder, run_id, condor_filename, condor_file)

run_cmd_and_print_outputs("cat {work_folder}/temp/tempMB*|sort -n|sed -e 's/Nsseia/Neisseria/g' > {work_folder}/repo_load_files/rambam_microbiology".format(work_folder=args.work_folder))
run_cmd_and_print_outputs("cat {work_folder}/temp/tempME* {work_folder}/temp/tempL* | python separateSignals.py {work_folder}".format(work_folder=args.work_folder))
run_cmd_and_print_outputs("""cat {correctedRules}|iconv -t utf8 |awk -F '\t' '{{print $10,"\t",$6,"\t",$13,"\t",$15}}'|sed -e 's/ //g'|grep -v IGNORE|sed -e 's/"//g'|sed 1d>{work_folder}/Units""".format(work_folder=args.work_folder, correctedRules="correctedRules.txt"))
run_cmd_and_print_outputs("""cat {correctedRules}|iconv -t utf8 |awk -F '\t' '{{print $10,"\t",$14}}'|sed -e 's/ //g'|grep -v IGNORE|sed 1d>{work_folder}/Resolutions""".format(work_folder=args.work_folder, correctedRules="correctedRules.txt"))

for file in glob.glob(args.work_folder + "/converted/*"):
	f = os.path.basename(file)
	cmd = "python ../mimic3/Scripts/process_signal.py --input {work_folder}/converted/{f} --output {work_folder}/processed/{f}.Fixed --log {work_folder}/processed/{f}.log --units {work_folder}/Units --resolution {work_folder}/Resolutions --graph {work_folder}/processed/{f}.html --nTimes 2 --utf8".format(f=f, work_folder=args.work_folder)
	run_cmd_and_print_outputs(cmd)
run_cmd_and_print_outputs ("cat {work_folder}/processed/*.Fixed|sort -n >{work_folder}/repo_load_files/lab_signals".format(work_folder=args.work_folder))

