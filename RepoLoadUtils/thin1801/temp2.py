import sys
import os
import re
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name, special_codes, is_nan


def get_out_file_name(row):
    out_file = row['description_x'] + '-' + row['medcode'] + '_' + row['description_y'] + '-' + str(row['ahdcode'])
    out_file = out_file.replace('/', '_Over_').replace(':', '-').replace(' ', '_').replace('>', 'GreaterThan').replace(
        '<', 'LessThan').replace('"', '').replace('?', '-').replace('*', 'wc')
    return out_file


def save_ahd_non_numeric_tests(vals_df, path_to_save):
    tests_list = vals_df[['medcode', 'description_x', 'ahdcode', 'description_y']].drop_duplicates()
    cols = ['medialid', 'eventdate', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'full_ahd_name']
    for _, codes in tests_list.iterrows():
        out_file = get_out_file_name(codes)
        test_dt = vals_df[(vals_df['medcode'] == codes['medcode']) & (vals_df['ahdcode'] == codes['ahdcode'])]
        test_dt['full_ahd_name'] = out_file
        #write_tsv(test_dt[cols], path_to_save, out_file)
    return vals_df.shape[0]

cfg = Configuration()
code_folder = fixOS(cfg.code_folder)
data_path = fixOS(cfg.raw_source_path)
raw_path = fixOS(cfg.doc_source_path)
out_folder = fixOS(cfg.work_path)
# full_file = os.path.join(code_folder, 'thin_signal_mapping.csv')
# thin_map = pd.read_csv(full_file, sep='\t')
# thin_map.drop_duplicates(subset='signal', inplace=True)
# thin_map.set_index('signal', inplace=True)
#
# readcodes = read_fwf('Readcodes', raw_path)
# cancer_codes = pd.read_csv(os.path.join(out_folder, 'CancerCodes.txt'), names=['rc', 'desc', 'organ'])
#
# mrg = cancer_codes.merge(readcodes, how='left', left_on='rc', right_on='medcode')
# mrg[['rc', 'description', 'organ']].to_csv(os.path.join(out_folder, 'CancerCodes1.txt'), index=False)

# numeric_sigs = []
# cat_sigs = []
# sig_file = os.path.join(out_folder, 'rep_configs', 'thin.signals')
# thin_map = pd.read_csv(full_file, sep='\t')
# thin_map.drop_duplicates(subset='signal', inplace=True)
# thin_map.set_index('signal', inplace=True)
# with open(sig_file) as f:
#     lines = f.readlines()
#
# new_lines = []
# for l in lines:
#     if l.strip().startswith('#') or len(l.strip()) == 0:
#         new_lines.append(l)
#     else:
#         parsed = l.strip().split('\t')
#         s = parsed[1]
#         if s not in thin_map.index:
#             new_lines.append(l)
#             print(s + ' not found in thin map')
#             continue
#         if len(parsed) < 4:
#             print('ERORR in line ' + l)
#             continue
#         if len(parsed) == 4:
#             parsed.append('general comment')
#         if len(parsed) > 4:
#             if parsed[4] == '':
#                 parsed[4] = 'general comment'
#         if len(parsed) == 5:
#             if thin_map.loc[s]['type'] == 'numeric':
#                 parsed.append('0')
#             else:
#                 parsed.append('1')
#         if len(parsed) >= 6:
#             if thin_map.loc[s]['type'] == 'numeric':
#                 parsed[5] == '0'
#             else:
#                 parsed[5] == '1'
#         new_lines.append('\t'.join(parsed)+'\n')
# with open(os.path.join(out_folder, 'rep_configs', 'thin.signals_with_cat'), 'w') as f:
#     for item in new_lines:
#         f.write("%s" % item)

final_path = os.path.join(out_folder, 'FinalSignals')
new_path = os.path.join(out_folder, 'temp')
# # file = 'Cancer_Location'
# # cols = ['medialid', 'sig', 'eventdate', 'val']
# # al_file = read_tsv(file, final_path, names=cols, header=None)
# # print(' sorting ' + file)
# # al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
# # print(' saving ' + file)
# # write_tsv(al_file[cols], new_path, file)
# files = os.listdir(final_path)
# files = ['RC_Procedures', 'RC_Demographic', 'RC_Diagnosis', 'RC_History', 'RC_Injuries', 'RC_Radiology', 'RC_Admin',
#          'RC_a', 'RC_b', 'RC_c', 'RC_d', 'RC_e', 'RC_f', 'RC_g', 'RC_h', 'RC_i', 'RC_j',
#          'RC_Diagnostic_Procedures_a', 'RC_Diagnostic_Procedures_b', 'RC_Diagnostic_Procedures_c',
#          'RC_Diagnostic_Procedures_d', 'RC_Diagnostic_Procedures_e', 'RC_Diagnostic_Procedures_f',
#          'RC_Diagnostic_Procedures_g', 'RC_Diagnostic_Procedures_h', 'RC_Diagnostic_Procedures_i',
#          'RC_Diagnostic_Procedures_j']
files = ['RC_d', 'RC_e', 'RC_f', 'RC_g', 'RC_h', 'RC_i', 'RC_j',
         'RC_Diagnostic_Procedures_a', 'RC_Diagnostic_Procedures_b', 'RC_Diagnostic_Procedures_c',
         'RC_Diagnostic_Procedures_d', 'RC_Diagnostic_Procedures_e', 'RC_Diagnostic_Procedures_f',
         'RC_Diagnostic_Procedures_g', 'RC_Diagnostic_Procedures_h', 'RC_Diagnostic_Procedures_i',
         'RC_Diagnostic_Procedures_j']

# #
# #files = [x for x in files if any(xs in x for xs in lst)]
#files = ['a_detailed_drugs', 'b_detailed_drugs', 'c_detailed_drugs',  'd_detailed_drugs', 'e_detailed_drugs',
#         'f_detailed_drugs', 'g_detailed_drugs',  'h_detailed_drugs', 'b_detailed_drugs','i_detailed_drugs', 'j_detailed_drugs']
#files = ['b_detailed_drugs']
# for file in files:
#      cols = ['medialid', 'sig', 'eventdate', 'val']
#      print(' reading ' + file)
#      al_file = read_tsv(file, final_path, names=cols, header=None)
#      print(' sorting ' + file)
#      al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
#      #print(' replacing ' + file)
#      #al_file.loc[al_file['val3'].isnull(), 'val3'] = 'unknown'
#      print(' saving ' + file)
#      write_tsv(al_file[cols], new_path, file)


prev_id2inr = fixOS(cfg.prev_id2ind)
curr_id2inr = 'X:\\Thin_2018_Loading\\ID2NR'
old_train = os.path.join(out_folder, 'FinalSignals', 'TRAIN17')
print(old_train)
tr_df = pd.read_csv(old_train, sep='\t', usecols=[0,2], names=['pid', 'val'], dtype={'pid': int, 'val': int})
old_ids = tr_df['pid'].unique()

#old_id2nr = pd.read_csv(prev_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
#old_ids = old_id2nr['medialid'].unique()
#del old_id2nr

cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
cur_ids = cur_id2nr['medialid'].unique()
del cur_id2nr

not_in_cur = list(set(old_ids) - set(cur_ids))
only_in_new = list(set(cur_ids) - set(old_ids))
in_both = list(set(cur_ids) & set(old_ids))


per70 = int(len(only_in_new)*0.7)
per20 = int(len(only_in_new)*0.2)

list1 = np.random.choice(only_in_new, per70, replace=False)
df1 = pd.DataFrame(list1)
df1['val'] = 1

remain = list(set(only_in_new) - set(list1))
list2 = np.random.choice(remain, per20, replace=False)
df2 = pd.DataFrame(list2)
df2['val'] = 2

remain2 = list(set(remain) - set(list2))
df3 = pd.DataFrame(remain2)
df3['val'] = 3

new_df = pd.concat([df1, df2, df3])
new_df.rename({0: 'pid'}, inplace=True, axis=1)


tr_df = tr_df[tr_df['pid'].isin(in_both)]

tr_df = pd.concat([tr_df, new_df])
tr_df['signal'] = 'TRAIN'
tr_df.sort_values(by='pid', inplace=True)
write_tsv(tr_df[['pid', 'signal', 'val']], os.path.join(out_folder, 'FinalSignals'), 'TRAIN')



