from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import glob, string 
from medial_tools.medial_tools import eprint, read_file, write_for_sure
import StringIO

parser = argparse.ArgumentParser()
parser.add_argument('--input_folder', default='/server/Data/canada_122017/IQIVA/')
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Prescription_Treatment.txt'):
	cur = read_file(f, sep = '|', limit_records=args.limit_records)
	cur.loc[:, 'filename'] = f
	df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)
	
eprint(df.shape[0], 'drug records before removing unknown ATC codes')
df = df[~pd.isnull(df.ATC4_CD) & ~pd.isnull(df.ATC3_CD)& ~pd.isnull(df.DIN_STD)]
eprint(df.shape[0], 'drug records after removing unknown DIN/ATC codes')

dict_records = []
dict_records.append({"def": "DEF", "order": 1, "my_serial_id": 0, "val": "Days:Unknown"})
my_serial_id = 1
for days in range(500):
	dict_records.append({"def": "DEF", "order": 1, "my_serial_id": my_serial_id, "val": "Days:{0}".format(my_serial_id,)})
	my_serial_id += 1
#------------- fill ATC dict
my_serial_id = 10000
tbl = string.maketrans(" \t", '__')
atc_code_to_serial_id = {}
for atc_level in ['ATC4', 'ATC3']:
	def print_atc_dict(x):
		global my_serial_id
		my_serial_id += 1
		atc_code = "ATC_{0}".format(x[atc_level + '_CD'][:4],)
		if atc_level == "ATC4": 
			atc_code += "_" + x[atc_level + '_CD'][4]
		atc_code_to_serial_id[atc_code] = my_serial_id
		
		dict_records.append({"def": "DEF", "order": 1, "my_serial_id": my_serial_id, "val": atc_code.ljust(12, '_')})
		dict_records.append({"def": "DEF", "order": 2, "my_serial_id": my_serial_id, "val": x[atc_level + '_DESC'].translate(tbl)})
		dict_records.append({"def": "DEF", "order": 3, "my_serial_id": my_serial_id, "val": "frequency: {0}".format(x['PAT_ID'],)})
	df.groupby(atc_level + '_CD').agg({'PAT_ID': 'nunique', atc_level + '_DESC': 'max'}).reset_index().apply(print_atc_dict, axis = 1)

for atc_level in [3, 1]:
	for atc_code in df['ATC3_CD'].apply(lambda x: "ATC_{0}".format(x[:atc_level],)).unique():
		my_serial_id += 1
		atc_code_to_serial_id[atc_code] = my_serial_id
		dict_records.append({"def": "DEF", "order": 1, "my_serial_id": my_serial_id, "val": atc_code.ljust(12, '_')})

#------------- fill DIN dict
dependency_set_records = []
din_code_to_serial_id = {}
my_serial_id = 20000
def print_din_dict(x):
	global my_serial_id
	my_serial_id += 1
	din_code = "DIN_" + str(x['DIN_STD'])
	din_code_to_serial_id[din_code] = my_serial_id
	dict_records.append({"def": "DEF", "order": 1, "my_serial_id": my_serial_id, "val": din_code})
	my_atc4 = ("ATC_{0}_{1}".format(x['ATC4_CD'][:4],x['ATC4_CD'][4]).ljust(12, '_'))
	dict_records.append({"def": "DEF", "order": 2, "my_serial_id": my_serial_id, "val": my_atc4 + ":" + str(x['RX_NM']).translate(tbl)})
	dependency_set_records.append({"set": "SET", "parent": my_atc4, "child": din_code})
df.groupby('DIN_STD').agg({'PAT_ID': 'nunique', 'ATC4_CD': 'max', 'RX_NM': 'max'}).reset_index().apply(print_din_dict, axis = 1)

dict = pd.DataFrame(dict_records).sort_values(['my_serial_id', 'order'])
s = dict.to_csv(columns=['def', 'my_serial_id', 'val'], index=False, header=False, sep = '\t')
with open(args.output_folder + '/dicts/dict.drugs_defs', 'w') as f:
	print("SECTION\tDrug", file=f)
	print(s, file=f)
	eprint("writing {0} into {1}".format(dict.shape, args.output_folder + '/dicts/dict.drugs_defs'))
#------------- fill set of dependencies
for atc_code in atc_code_to_serial_id.keys():
	parent = atc_code[:-1]
	while len(parent) > 0:
		if parent in atc_code_to_serial_id:
			dependency_set_records.append({"set": "SET", "parent": parent.ljust(12, '_'), "child": atc_code.ljust(12, '_')})
			break
		parent = parent[:-1]

set_dict = pd.DataFrame(dependency_set_records).sort_values(['parent', 'child'])
s = set_dict.to_csv(columns=['set', 'parent', 'child'], index=False, header=False, sep = '\t') 
with open(args.output_folder + '/dicts/dict.drugs_sets', 'w') as f:
	print("SECTION\tDrug", file=f)
	print(s, file=f)
	eprint("writing {0} into {1}".format(set_dict.shape, args.output_folder + '/dicts/dict.drugs_sets'))

output_records = []
def print_drug(x):
	if pd.isnull(x["TOTAL_DURATION"]):
		duration = "Days:Unknown"
	else:
		duration = "Days:{0}".format(int(x["TOTAL_DURATION"]),)
	output_records.append({"pid": x['PAT_ID'], "sig": "Drug", "date": x['EVENT_DAY'], "val1": "DIN_" + str(x['DIN_STD']), "val2": duration})
df.apply(print_drug, axis = 1)

drug_data = pd.DataFrame(output_records)
write_for_sure(drug_data.sort_values(['pid', 'date']), args.output_folder + '/drug_data', columns=['pid', 'sig', 'date', 'val1', 'val2'], index=False, header=False, sep = '\t') 
