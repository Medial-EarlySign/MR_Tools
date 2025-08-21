from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import glob
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--input_folder', default='/server/Data/canada_122017/IQIVA/')
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

nm_to_sig = read_file('canada_sig_name_to_sig_name.csv')
nm_to_sig = nm_to_sig[nm_to_sig.source == 'Lab_Data']
canada_to_medial_factor = read_file('canada_to_medial_factor.tsv', sep='\t')
resolutions = read_file('Instructions.txt', sep='\t')
sig_to_res = {}
def fill_resolutions(x):
	resolution = x['Resolution']
	if resolution in [1, 10]:
		resolution = "{:.0f}"
	elif resolution == 0.1:
		resolution = "{:.1f}"
	elif resolution == 0.01:
		resolution = "{:.2f}"
	else:
		raise ValueError("unknown resolution: " + str(resolution))
	sig_to_res[x['Name']] = resolution
resolutions.apply(fill_resolutions, axis = 1)
df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Lab_Data.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)

numeric_tr = df[df.VAL_TYP_CD == 'number'].copy()
numeric_tr.loc[:, 'RES_VAL'] = numeric_tr.RES_VAL.astype(float)
numeric_tr.loc[:, 'UOM'] = numeric_tr.UOM.apply(lambda x: 'NA' if pd.isnull(x) else x)

numeric_tr = pd.merge(numeric_tr, nm_to_sig, left_on = 'MED_TEST_NM', right_on='canada_sig_name', how='left')
numeric_tr = pd.merge(numeric_tr, canada_to_medial_factor, on = 'sig', how='left')
numeric_tr.fillna({'canada_to_medial_factor':1.0}, inplace=True)
eprint("numeric lab data", numeric_tr.shape)

#--------------- manual fixes for some specific test and units
numeric_tr.loc[(numeric_tr.UOM == 'NA') & (numeric_tr.MED_TEST_NM == 'PROTEIN'), 'sig'] = 'Unknown' # mixed with blood protein... 
idx = (numeric_tr.UOM == 'NA') & (numeric_tr.sig == 'HbA1C')
numeric_tr.loc[idx, 'RES_VAL'] = numeric_tr[idx].RES_VAL * 100

#--------------- aggregative stats
def flatten_columns(df):
	df.columns = ['_'.join(col).strip('_') for col in df.columns.values]
	return df
by_sig = flatten_columns(numeric_tr.groupby('sig').agg({'PAT_ID': 'count', 'RES_VAL': ['mean', 'std']}).reset_index())
by_test_nm = flatten_columns(numeric_tr.groupby(['sig','MED_TEST_NM']).agg({'PAT_ID': 'count', 'RES_VAL': ['mean', 'std']}).reset_index())
by_unit = flatten_columns(numeric_tr.groupby(['sig', 'MED_TEST_NM', 'UOM']).agg({'PAT_ID': 'count', 'RES_VAL': ['mean', 'std']}).reset_index())
j = pd.merge(by_sig, by_test_nm, on = 'sig', suffixes = ['', '_test_nm'])
j = pd.merge(j, by_unit, on = ['sig', 'MED_TEST_NM'], suffixes = ['', '_unit'])
j.loc[:, 'uom_pct_of_sig'] = 1.0 * j.PAT_ID_count_unit / j.PAT_ID_count
j.loc[:, 'std_distance'] = (j.RES_VAL_mean_unit - j.RES_VAL_mean).abs() / j.RES_VAL_std_unit
write_for_sure(j.sort_values('PAT_ID_count_test_nm', ascending = False), args.output_folder + '/stats/numeric_lab_data_signals_tests_units.csv', index=False)

#---------------- all records after conversion to medial format and units
numeric_tr = pd.merge(numeric_tr, j[['MED_TEST_NM', 'UOM', 'uom_pct_of_sig', 'PAT_ID_count_unit']], on = ['MED_TEST_NM', 'UOM'])
def fix_res(x):
	my_res = sig_to_res[x['sig']]
	return float(my_res.format(x['RES_VAL']))
numeric_tr.loc[:, 'ORIG_VAL'] = numeric_tr.RES_VAL
numeric_tr.loc[:, 'RES_VAL'] = numeric_tr.RES_VAL * numeric_tr.canada_to_medial_factor
numeric_tr.loc[:, 'RES_VAL'] = numeric_tr.apply(fix_res, axis = 1)
output_records = []
def print_numeric_lab_data(x):
	output_records.append({"pid": x['PAT_ID'], "sig": x['sig'], "med_test_nm": x['MED_TEST_NM'], "date": x['EVENT_DAY'], "val": x['RES_VAL'], "uom": x['UOM'], "orig_val": x['ORIG_VAL']})

numeric_tr[(numeric_tr.uom_pct_of_sig > 0.05) & (numeric_tr.PAT_ID_count_unit > 500) & (numeric_tr.sig != 'Unknown')].apply(print_numeric_lab_data, axis = 1)
out_df = pd.DataFrame(output_records)
write_for_sure(out_df.sort_values(['pid', 'date']), args.output_folder + '/numeric_lab_data', columns=['pid', 'sig', 'date', 'val', 'med_test_nm', 'uom', 'orig_val'], index=False, header=False, sep = '\t') 

