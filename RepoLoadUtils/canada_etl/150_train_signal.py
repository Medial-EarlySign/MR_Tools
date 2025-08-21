from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd, numpy as np
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
args = parser.parse_args()

demo = read_file(args.output_folder + '/demographics_data', names=['pid', 'sig', 'val'], sep = '\t') 
pids = demo.pid.unique()
np.random.shuffle(pids)
output_records = []
i = 0
for pid in pids:
	if i < pids.size * 0.7:
		train = 1
	elif i < pids.size * 0.9:
		train = 2
	else:
		train = 3
	output_records.append({"pid": pid, "sig": "TRAIN", "val": train})
	i += 1

output_records = pd.DataFrame(output_records).drop_duplicates().sort_values('pid')
write_for_sure(output_records[['pid', 'sig', 'val']], args.output_folder + '/train_data', index=False, header=False, sep = '\t') 

