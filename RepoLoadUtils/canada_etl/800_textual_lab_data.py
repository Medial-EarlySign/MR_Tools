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

nm_to_sig = read_file('canada_sig_name_to_sig_name.csv')
nm_to_sig = nm_to_sig[nm_to_sig.source == 'Lab_Data_text']

df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Lab_Data.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)

df = df[df.VAL_TYP_CD == 'text'].copy()
df = pd.merge(df, nm_to_sig, left_on = 'MED_TEST_NM', right_on='canada_sig_name', how='left')
df.fillna({'UOM': 'NA', 'sig':'Unknown'}, inplace=True)

output_records = []
def print_data(x):
	output_records.append({"pid": x['PAT_ID'], "sig": x['sig'], "orig_sig": x['MED_TEST_NM'], "date": x['EVENT_DAY'], "val": x['RES_VAL']})
df[df.sig.apply(lambda x: x not in ['Unknown'])].apply(print_data, axis = 1)

out_df = pd.DataFrame(output_records)
eprint('out_df', out_df.shape)
write_for_sure(out_df.sort_values(['pid', 'date']), args.output_folder + '/textual_lab_data', columns=['pid', 'sig', 'date', 'val', 'orig_sig'], index=False, header=False, sep = '\t') 
