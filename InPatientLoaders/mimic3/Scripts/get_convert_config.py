#!/usr/bin/python

from __future__ import print_function
import argparse as ap
import sys

# Read a list of names
def read_list(name,list):
	with open(name,"r") as file:
		for line in file:
			list.append(line.rstrip("\r\n"))

# Generate file
def generate_convert_config(numeric_data_files,non_numeric_data_files,dict_files,signals_files,config,signals,in_dir,out_dir):
	
	# Generate signals file
	signals_fp = open(signals,"w")	
	for inFile in signals_files:
		with open(inFile,"r") as file:
			for line in file:
				signals_fp.write(line)
	signals_fp.close()

	# Generate convert-config
	config_fp = open(config,"w")
	config_fp.write("#\n# Mimic-3 convert config\n#\n")
	config_fp.write("DESCRIPTION\tMimic-3 new version\n")
	config_fp.write("RELATIVE\t1\n")
	config_fp.write("SAFE_MODE\t1\n")
	
	for dict in dict_files:
		config_fp.write("DICTIONARY\t%s\n"%dict)
	
	config_fp.write("\nMODE\t3\n")
	config_fp.write("PREFIX\tMimic3\n")
	config_fp.write("CONFIG\tMimic3.repository\n")
	config_fp.write("SIGNAL\t%s\n\n"%signals)
	
	for data_file in numeric_data_files:
		config_fp.write("DATA\t%s\n"%data_file)	
	for data_file in non_numeric_data_files:
		config_fp.write("DATA_S\t%s\n"%data_file)
		
	config_fp.write("\nDIR\t%s\n"%in_dir)
	config_fp.write("OUTDIR\t%s\n"%out_dir)
	
# ======= MAIN ======
parser = ap.ArgumentParser(description = "prepare MIMIC-3 transfers file for loading")
parser.add_argument("--numeric_signals",help="numeric signals")
parser.add_argument("--text_signals",help="non numeric signals")
parser.add_argument("--dicts",help="dict files list")
parser.add_argument("--signals",help="signals file list")
parser.add_argument("--config",help="output config file")
parser.add_argument("--out_signals",help="output signals file")
parser.add_argument("--in_dir",help="input files directory")
parser.add_argument("--out_dir",help="output files directory")
args = parser.parse_args() 

# Read
numeric_data_files = []
read_list(args.numeric_signals,numeric_data_files)

non_numeric_data_files = []
read_list(args.text_signals,non_numeric_data_files)

dict_files = []
read_list(args.dicts,dict_files)

signals_files = []
read_list(args.signals,signals_files)

# Do your stuff
generate_convert_config(numeric_data_files,non_numeric_data_files,dict_files,signals_files,args.config,args.out_signals,args.in_dir,args.out_dir)

