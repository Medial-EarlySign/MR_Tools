from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import glob, string 
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

def is_int(s):
	try:
		int(s)
		return True
	except ValueError:
		return False

dict = read_file(args.output_folder + "/dicts/dict.diag_defs", sep = '\t', names=['def', 'my_serial_id', 'diag_name'], limit_records=args.limit_records)
cancers = dict[dict.diag_name.apply(lambda x: str(x).startswith('ICD-9:') and is_int(x[6:]) and 140 <= int(x[6:]) <= 239) | dict.diag_name.apply(lambda x: "Neoplasm_(Malignant)" in str(x))]
cancers = pd.merge(dict, cancers[['my_serial_id']].drop_duplicates(), on = 'my_serial_id')
cancers.loc[:, 'my_serial_id'] = cancers.my_serial_id.astype(int)

s = cancers.to_csv(columns=['def', 'my_serial_id', 'diag_name'], index=False, header=False, sep = '\t')
with open(args.output_folder + '/dicts/dict.Cancer_Location_defs', 'w') as f:
	print("SECTION\tCancer_Location", file=f)
	print(s, file=f)
	eprint("writing {0} into {1}".format(cancers.shape, args.output_folder + '/dicts/dict.Cancer_Location_defs'))

diag = read_file(args.output_folder + "diag_data", sep = '\t', names=['pid', 'sig', 'date', 'diag_name'], limit_records=args.limit_records)
cancer_diag = pd.merge(diag, cancers, on='diag_name')
cancer_diag.loc[:, 'sig'] = 'Cancer_Location'
eprint("cancer_diag", cancer_diag.shape)

write_for_sure(cancer_diag.sort_values(['pid', 'date']), args.output_folder + '/cancer_data', columns=['pid', 'sig', 'date', 'diag_name'], index=False, header=False, sep = '\t') 