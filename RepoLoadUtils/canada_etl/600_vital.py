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
nm_to_sig = nm_to_sig[nm_to_sig.source == 'Vital']
canada_to_medial_factor = read_file('canada_to_medial_factor.tsv', sep='\t')

df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Vital.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)
	
def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False
df = df[df.MED_VITAL_RSLT.apply(lambda x: is_number(x))]
df = pd.merge(df, nm_to_sig, left_on = 'MED_VITAL_TYP_NM', right_on='canada_sig_name', how='left')
df = pd.merge(df, canada_to_medial_factor, on = 'sig', how='left')
df.fillna({'canada_to_medial_factor':1.0, 'UOM': 'NA', 'sig':'Unknown'}, inplace=True)

output_records = []
def print_data(x):
	output_records.append({"pid": x['PAT_ID'], "sig": x['sig'], "orig_sig": x['MED_VITAL_TYP_NM'], "date": x['EVENT_DAY'], "val": float(x['MED_VITAL_RSLT']), 
		"uom": x['UOM'], "orig_val": float(x['MED_VITAL_RSLT'])})
df[df.sig.apply(lambda x: x not in ['Unknown','BP'])].apply(print_data, axis = 1)

out_df = pd.DataFrame(output_records)
write_for_sure(out_df.sort_values(['pid', 'date']), args.output_folder + '/numeric_vital_data', columns=['pid', 'sig', 'date', 'val', 'orig_sig', 'uom', 'orig_val'], index=False, header=False, sep = '\t') 

eprint("BP_SYS", df[df.MED_VITAL_TYP_NM == 'BP_SYS'].shape )
eprint("BP_DIA", df[df.MED_VITAL_TYP_NM == 'BP_DIA'].shape )
bp = pd.merge(df[df.MED_VITAL_TYP_NM == 'BP_SYS'], df[df.MED_VITAL_TYP_NM == 'BP_DIA'], on = ['PAT_ID', 'EVENT_DAY', 'sig'], suffixes = ['_SYS', '_DIA'])
eprint("BP", bp.shape )

bp_records = []
def print_data(x):
	bp_records.append({"pid": x['PAT_ID'], "sig": x['sig'], "orig_sig": x['MED_VITAL_TYP_NM_SYS'] + "_" + x['MED_VITAL_TYP_NM_DIA'], "date": x['EVENT_DAY'], 
	"val1": int(x['MED_VITAL_RSLT_DIA']), "val2": int(x['MED_VITAL_RSLT_SYS']), "uom": x['UOM_SYS']})
bp.apply(print_data, axis = 1)

out_bp = pd.DataFrame(bp_records)
write_for_sure(out_bp.sort_values(['pid', 'date']), args.output_folder + '/bp_data', columns=['pid', 'sig', 'date', 'val1', 'val2', 'orig_sig', 'uom'], index=False, header=False, sep = '\t') 
