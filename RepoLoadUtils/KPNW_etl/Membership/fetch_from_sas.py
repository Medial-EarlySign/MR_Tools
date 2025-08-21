#!/usr/bin/python
import pandas as pd
import os

data_folder = '/nas1/Data/NWP'
pat_demo_file = 'medial_flu_pat_membership.sas7bdat'

delta_folders = sorted(list(filter(lambda nm: nm.startswith('Delta') ,os.listdir(data_folder))))
delta_folders.insert(0, '')
full_files = list(map(lambda x: os.path.join(data_folder, x, pat_demo_file), delta_folders ))

output_path = '/nas1/Temp/NWP'
				  
for i, d_file in zip(range(1, len(full_files) + 1), full_files):
	print('Reading file ' + d_file + ' (' + str(i) + ')')
	member_one_df = pd.read_sas(d_file, encoding='latin-1')
	#print(member_one_df.head())
	member_one_df = member_one_df[['PAT_ID_GEN', 'COVERAGE_START_DT', 'COVERAGE_END_DT', 'CURRENT_MEMBER_FLAG']]
	member_one_df['COVERAGE_START_DT'] = pd.to_timedelta(member_one_df['COVERAGE_START_DT'], unit='S') + pd.Timestamp('1960-1-1')
	member_one_df['COVERAGE_END_DT'] = pd.to_timedelta(member_one_df['COVERAGE_END_DT'], unit='S') + pd.Timestamp('1960-1-1')
	member_one_df.to_csv(os.path.join(output_path, 'FILE_%d'%(i)), sep='\t', index=False, header=False, mode='w', line_terminator='\n')

