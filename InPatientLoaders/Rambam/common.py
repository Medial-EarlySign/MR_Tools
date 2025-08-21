#!/usr/bin/python
from __future__ import print_function
from  medial_tools.medial_tools import eprint, read_file, write_for_sure

def write_as_dict(df, header, filename, prefix='DEF'):
	df.loc[:, 'prefix'] = prefix
	df = df.groupby(['numeric_code', 'desc']).head(1).sort_values(['numeric_code', 'pri'])
	s = df.to_csv(sep = '\t', index = False, header = False,
		columns = ['prefix', 'numeric_code', 'desc'])
	with open(filename, 'w') as f:
		print(header, file=f)
		print(s, file=f)
		eprint("writing {0} into {1}".format(df.shape, filename))

def rambam_str_to_dict(x):
	return {int(s.split(':')[0]) : str(s[3:]).replace(" ","_") for s in str(x).split('~')}
