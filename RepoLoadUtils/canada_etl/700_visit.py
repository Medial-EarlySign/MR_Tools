from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import glob, string 
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--input_folder', default='/server/Data/canada_122017/IQIVA/')
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Visit.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)
	
def is_int(s):
	try:
		int(s)
		return True
	except ValueError:
		return False
		
smoking_records = []
def print_data(x):
	if x['SMOKER_STATUS'] == 'yes':
		val, qty = 2, -9
	elif x['SMOKER_STATUS'] == 'never':
		val, qty = 3, 0
	elif x['SMOKER_STATUS'] == 'quit':
		val, qty = 1, -9
	else:
		raise Exception("Unknown SMOKER_STATUS [{0}]".format(x['SMOKER_STATUS'],))
	smoking_records.append({"pid": x['PAT_ID'], "sig": "Smoking_quantity", "orig_sig": "SMOKER_STATUS", "date": x['EVENT_DAY'], "val1": val, "val2": qty})
	if not pd.isnull(x['SMOKE_QUIT_DATE']) and is_int(x['SMOKE_QUIT_DATE']) and int(x['SMOKE_QUIT_DATE']) > 19011231:
		smoking_records.append({"pid": x['PAT_ID'], "sig": "Smoking_quantity", "orig_sig": "SMOKE_QUIT_DATE", "date": int(x['SMOKE_QUIT_DATE']), "val1": 2, "val2": -9})
df[~pd.isnull(df.SMOKER_STATUS)].apply(print_data, axis = 1)

out_df = pd.DataFrame(smoking_records).drop_duplicates()
write_for_sure(out_df.sort_values(['pid', 'date']), args.output_folder + '/smoking_data', columns=['pid', 'sig', 'date', 'val1', 'val2', 'orig_sig'], index=False, header=False, sep = '\t') 
