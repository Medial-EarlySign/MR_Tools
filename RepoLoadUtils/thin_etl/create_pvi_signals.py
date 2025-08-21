from Configuration import Configuration
import os, re, subprocess, traceback, random
from datetime import datetime
from common import *
import pandas as pd
import numpy as np
import sys




def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = filter(lambda x: len(x.strip()) > 0 ,lines)
    fp.close()
    return lines


	
def load_pvi_signals():

	cfg = Configuration()
	out_folder = fixOS(cfg.output_path)
	work_path = fixOS(cfg.work_path)

	#load id2nr
	print ("read id2nr .....")
	lines = getLines(work_path, 'ID2NR')
	id2nr = read_id2nr(lines)



	if not(os.path.exists( os.path.join(out_folder, 'pvi' ))):
		os.makedirs(os.path.join(out_folder, 'pvi'))
		
	err_file_name = os.path.join(out_folder, 'pvi' ,"pvi_stat")
	err_file = file(err_file_name, 'w')
	out_file_name = os.path.join(out_folder, 'pvi' ,"PVI")
	#out_file = io.open(out_file_name, 'w', newline = '')
	out_file = open(out_file_name, 'w')
	eprint("writing to", err_file_name, out_file_name)

	flag_names = ["pvi_urbanrural",  \
				  "pvi_eth_percw",  \
				  "pvi_eth_percm",  \
				  "pvi_eth_percas",  \
				  "pvi_eth_percb",  \
				  "pvi_eth_perco",  \
				  "pvi_prop_llti",  \
				  "pvi_no2",  \
				  "pvi_pm10",  \
				  "pvi_so2",  \
				  "pvi_nox",  \
				  "pvi_townsend"]


	data_path = fixOS(cfg.raw_source_path)

	in_file_names = list(filter(lambda f: f.startswith('pvi.') ,os.listdir(data_path)))
	eprint("about to process", len(in_file_names), "files")
	outlines = []

	from collections import defaultdict
	data = defaultdict(list)

	count=0
	for in_file_name in in_file_names:
		count+=1
		pracid = in_file_name[-5:]
		print (pracid, count, len(in_file_names) )
		#if count>=5: break
		eprint("reading from", in_file_name)
		stats = {"unknown_id": 0, "read": 0, "wrote": 0}    
		data = defaultdict(list)
		fp = open(os.path.join(data_path ,in_file_name), 'r')
		fp_lines = fp.readlines()
		fp.close()
		for l in fp_lines:
			stats["read"] += 1
			patid, flags, eventdate = l[0:4],l[4:16],l[16:24]
			
			
			combid = pracid + patid
			if combid not in id2nr:
				stats["unknown_id"] += 1
				continue
			
			for k in range(len(flags)):
				val = flags[k]
				if val =='X': val = -9
				outlines.append([id2nr[combid], flag_names[k], eventdate, val])

		write_stats(stats, pracid, err_file)
	print ("before sort")
	outlines.sort()
	print ("after sort")
	final_outlines = []
	prev_id =-1
	prev_flag_name = '-1'
	prev_flag=-1
	for line in outlines:
		id = line[0]
		flag_name = line[1]
		date = line[2]
		flag = line[3]
		
	
		if not(prev_id ==id and prev_flag_name ==flag_name and prev_flag==flag):
			final_outlines.append("\t".join(map(str, line)) + '\n')
		
		
		prev_id =id
		prev_flag_name =flag_name
		prev_flag=flag
		
	out_file.writelines(list(map(lambda ln : unicode(ln),final_outlines)))
	out_file.close()



if __name__ == "__main__":
    load_pvi_signals()

	
		