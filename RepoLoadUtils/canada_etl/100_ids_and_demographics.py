from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--input_folder', default='/server/Data/canada_122017/IQIVA/')
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--max_end_date', type=int, required=True)
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

import glob
df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Reference_-_Patient.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

output_records = []
missing_yob, missing_least_trans_dt = 0, 0
def print_demographics(x):
	global missing_yob, missing_least_trans_dt
	if pd.isnull(x["YOB"]):
		missing_yob += 1
		return
	if pd.isnull(x["LEAST_TRANS_DT"]):
		missing_least_trans_dt += 1
		return
	end_date=min(int(x["MOST_TRANS_DT"]), args.max_end_date)
	output_records.append({"pid": x['PAT_ID'], "sig": "BYEAR", "val": int(x["YOB"])})
	output_records.append({"pid": x['PAT_ID'], "sig": "BDATE", "val": int(x["YOB"]) * 10000 + 0101})
	output_records.append({"pid": x['PAT_ID'], "sig": "STARTDATE", "val": int(x["LEAST_TRANS_DT"])})
	output_records.append({"pid": x['PAT_ID'], "sig": "ENDDATE", "val": end_date})
	output_records.append({"pid": x['PAT_ID'], "sig": "GENDER", "val": 1 if x['GENDER_NM'] == 'Male' else 2})
df[['PAT_ID', 'YOB', 'LEAST_TRANS_DT', 'MOST_TRANS_DT', 'GENDER_NM']].drop_duplicates().apply(print_demographics, axis = 1)

eprint("missing_yob", missing_yob)
eprint("missing_least_trans_dt", missing_least_trans_dt)

output_records = pd.DataFrame(output_records).drop_duplicates().sort_values('pid')
write_for_sure(output_records, args.output_folder + '/demographics_data', index=False, header=False, sep = '\t') 

