from __future__ import print_function
from  medial_tools.medial_tools import eprint, read_file, write_for_sure
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/UsersData/ido/MR/Tools/Registries/Lists/')
parser.add_argument('--thin_folder', default='/server/Data/THIN1601/THINAncil1601/text/')

args = parser.parse_args()

reg = read_file(args.work_folder + 'thin_cancer_medcodes_20161103_full_tree.txt', sep = '\t')
freq = read_file(args.thin_folder + 'MedicalReadcodeFrequencyEver1601.txt', sep='\t', names = ['col'])
ahd_freq = read_file(args.thin_folder + 'AHDReadcodeFrequencyEver1601.txt', sep='\t', names = ['col'])

freq.loc[:, 'read_code'] = freq.col.apply(lambda x: x[:7])
freq.loc[:, 'desc'] = freq.col.apply(lambda x: x[7:67])
freq.loc[:, 'medical_freq'] = freq.col.apply(lambda x: x[67:])

freq.drop('col', axis = 1, inplace = True)

ahd_freq.loc[:, 'read_code'] = ahd_freq.col.apply(lambda x: x[:7])
ahd_freq.loc[:, 'desc'] = ahd_freq.col.apply(lambda x: x[7:67])
ahd_freq.loc[:, 'ahd_freq'] = ahd_freq.col.apply(lambda x: x[67:])
ahd_freq.drop('col', axis = 1, inplace = True)

j = pd.merge(reg, freq[['read_code', 'medical_freq']], left_on = "Read code", right_on = "read_code", how='left')
j = pd.merge(j, ahd_freq[['read_code','ahd_freq']], on = "read_code",how='left')
j = j.drop(['# records', '# patients'], axis = 1)
write_for_sure(j, args.work_folder + 'thin_cancer_medcodes_20170716_full_tree_fixed_freqs.txt', sep='\t', index = False)