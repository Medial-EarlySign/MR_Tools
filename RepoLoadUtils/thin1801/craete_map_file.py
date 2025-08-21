import sys
import os
import re
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name, special_codes


def get_sig_name(ahd_name, ahd_column_description, ahdcnt):
    ahdname = ahd_name.strip()
    if ahdcnt > 1:
        coldesc = ahd_column_description.replace('QUALIFIER', '').replace('(Y/N)', '')
        if coldesc != '':
            ahdname = ahdname + '_' + coldesc

    ahdname = ahdname.replace(' ', '_').replace('/', '_over_').replace('%', '').replace('&', 'and').replace('(', '_').replace(')', '')
    ahdname = ahdname.replace(',', '_')
    ahdname = ahdname.replace('_-_', '_')
    ahdname = ahdname.replace('__', '_')
    return ahdname


cfg = Configuration()
code_folder = fixOS(cfg.code_folder)
data_path = fixOS(cfg.raw_source_path)
raw_path = fixOS(cfg.doc_source_path)
out_folder = fixOS(cfg.work_path)
reg_folder = fixOS(cfg.reg_list_path)

file_to_sig = read_tsv('numeric_mapping.txt', code_folder, names=['InFile',	'signal'])
file_to_sig = file_to_sig[(file_to_sig['signal'] != 'TBD') & (file_to_sig['signal'].notnull())]

file_to_sig['LIST'] = file_to_sig['InFile'].str.split('-')
#file_to_sig['ahdcode'] = file_to_sig.apply(lambda row: row['LIST'][-1], axis=1)
file_to_sig['readcode'] = file_to_sig.apply(lambda row: row['LIST'][-2][0:7], axis=1)
file_to_sig['readcode1'] = file_to_sig.apply(lambda row: row['LIST'][-3][0:7], axis=1)
file_to_sig['readcode'] = file_to_sig['readcode'].where(~file_to_sig['readcode'].str.startswith('_'), file_to_sig['readcode1'])
file_to_sig['readcode'] = file_to_sig['readcode'].where(~file_to_sig['readcode'].str.startswith('i'),
                                                        file_to_sig['readcode1'])

file_to_sig.drop_duplicates(subset=['signal', 'readcode'], inplace=True)

file_to_sig['source_file'] = 'ahd'
file_to_sig['value_field'] = 'data2'
file_to_sig['unitcode_field'] = 'data3'
file_to_sig['type'] = 'numeric'

cols = ['signal', 'source_file','ahdcode', 'readcode', 'value_field', 'unitcode_field', 'type']
file_to_sig_map = read_tsv('ahd_non_numeric_mapping.txt', code_folder,
                           names=['data_file', 'ahdcode', 'ahd_name', 'value_field', 'column_description', 'type'])
file_to_sig_map['ahdcode'] = file_to_sig_map['ahdcode'].astype(str)
file_to_sig_map = file_to_sig_map[file_to_sig_map['column_description'] != 'READ_CODE']
countdf = file_to_sig_map[['ahdcode', 'value_field']]. groupby('ahdcode').count()
countdf.rename(columns={'value_field': 'count'}, inplace=True)
file_to_sig_map = file_to_sig_map.merge(countdf, how='left', right_index=True, left_on='ahdcode')
file_to_sig_map['signal'] = file_to_sig_map.apply(lambda x: get_sig_name(x['ahd_name'], x['column_description'], x['count']), axis=1)
file_to_sig_map['source_file'] = 'ahd'
file_to_sig_map['type'] = 'string'

alcohol_qnt = read_tsv('alcohol_type_quan_list.txt', reg_folder,
                       names=['readcode', 'value1', 'value2', 'desc', 'freq_medical', 'freq_ahd'], header=0)
smoke_qnt = read_tsv('smoking_type_quan_list.txt', reg_folder,
                     names=['readcode', 'value1', 'value2', 'desc', 'freq_medical', 'freq_ahd'], header=0)
alcohol_qnt['signal'] = 'Alcohol_quantity'
smoke_qnt['signal'] = 'Smoking_quantity'
smk_alc_qnt_ahd = pd.concat([alcohol_qnt, smoke_qnt])
smk_alc_qnt_ahd['type'] = 'numeric'
smk_alc_qnt_medical = smk_alc_qnt_ahd.copy()
smk_alc_qnt_ahd = smk_alc_qnt_ahd[(smk_alc_qnt_ahd['freq_ahd'].notnull()) & (smk_alc_qnt_ahd['freq_ahd'] > 100)]
smk_alc_qnt_medical = smk_alc_qnt_medical[(smk_alc_qnt_medical['freq_ahd'].notnull()) & (smk_alc_qnt_medical['freq_medical'] > 100)]
smk_alc_qnt_ahd['source_file'] = 'ahd'
smk_alc_qnt_medical['source_file'] = 'medical'

#smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 3, 'value_field'] = 'data2'
#smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 3, 'unitcode_field'] = 'data1'
#smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 3, 'value2'] = np.nan
#smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 3, 'value1'] = np.nan


smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 3, 'value1'] = 100
smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 100, 'value2'] = -9

smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 4, 'value2'] = 0
smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 4, 'value1'] = 3

smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 5, 'value2'] = 0
smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 5, 'value1'] = 4

smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 6, 'value2'] = -9
smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 6, 'value1'] = 1

smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 7, 'value2'] = -9
smk_alc_qnt_ahd.ix[smk_alc_qnt_ahd['value1'] == 7, 'value1'] = 5

#smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 3, 'value_field'] = 'data2'
#smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 3, 'unitcode_field'] = 'data1'
#smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 3, 'value2'] = np.nan
#smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 3, 'value1'] = np.nan


smk_alc_qnt_medical = smk_alc_qnt_medical[smk_alc_qnt_medical['value1'] != 3]
smk_alc_qnt_medical = smk_alc_qnt_medical[smk_alc_qnt_medical['value1'] != 6]

smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 4, 'value2'] = 0
smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 4, 'value1'] = 3

smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 5, 'value2'] = 0
smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 5, 'value1'] = 4

smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 7, 'value2'] = -9
smk_alc_qnt_medical.ix[smk_alc_qnt_medical['value1'] == 7, 'value1'] = 5


cols_sa = ['signal', 'source_file', 'type', 'readcode', 'value1', 'value2']
cols_s = ['signal', 'source_file', 'type', 'ahdcode', 'value_field']
cols_n = ['signal', 'source_file', 'type', 'readcode', 'value_field', 'unitcode_field']
cols = ['signal', 'source_file', 'type', 'ahdcode', 'readcode', 'value_field', 'unitcode_field', 'value1', 'value2', 'regex']
final = pd.concat([file_to_sig[cols_n],file_to_sig_map[cols_s], smk_alc_qnt_ahd[cols_sa], smk_alc_qnt_medical[cols_sa]])
final_x = pd.concat([smk_alc_qnt_ahd[cols_sa], smk_alc_qnt_medical[cols_sa]])
final_x['ahdcode'] = np.nan
final_x['regex'] = np.nan
final_x['value_field'] = np.nan
final_x['unitcode_field'] = np.nan

more_coodes = [{'signal': 'BP', 'ahdcode': 1005010500, 'type': 'numeric', 'value_field': ['data1', 'data2'], 'source_file': 'ahd'},
               {'signal': 'Weight', 'ahdcode': 1005010200, 'type': 'numeric', 'value_field': 'data1', 'source_file': 'ahd'},
               {'signal': 'BMI', 'ahdcode': 1005010200, 'type': 'numeric', 'value_field': 'data3', 'source_file': 'ahd'},
               {'signal': 'Height', 'ahdcode': 1005010100, 'type': 'numeric', 'value_field': 'data1', 'source_file': 'ahd'},
               {'signal': 'SMOKING', 'ahdcode': 1003040000, 'type': 'numeric', 'value_field': 'data1', 'source_file': 'ahd'},
               {'signal': 'STOPPED_SMOKING', 'ahdcode': 1003040000, 'type': 'numeric', 'value_field': 'data6', 'source_file': 'ahd'},
               {'signal': 'ALCOHOL', 'ahdcode': 1003050000, 'type': 'numeric', 'value_field': 'data1', 'source_file': 'ahd'},
               {'signal': 'PULSE', 'ahdcode': 1009300000, 'type': 'numeric', 'value_field': 'data1', 'source_file': 'ahd'}]
final = final.append(more_coodes)

rc_codes = [
    {'signal': 'RC_Demographic', 'regex': '^[0]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_History', 'regex': '^[12R]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Diagnostic_Procedures', 'regex': '^[34]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Radiology', 'regex': '^[5]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Procedures', 'regex': '^[678Z]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Admin', 'regex': '^[9]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Diagnosis', 'regex': '^[ABCDEFGHJKLMNPQ]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Injuries', 'regex': '^[STU]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC', 'regex': '^[0-9A-HJ-NP-U]', 'type': 'readcode', 'source_file': 'ahd'},
    {'signal': 'RC_Demographic', 'regex': '^[0]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_History', 'regex': '^[12R]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_Diagnostic_Procedures', 'regex': '^[34]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_Radiology', 'regex': '^[5]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_Procedures', 'regex': '^[678Z]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_Admin', 'regex': '^[9]', 'type': 'readcode','source_file': 'medical'},
    {'signal': 'RC_Diagnosis', 'regex': '^[ABCDEFGHJKLMNPQ]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC_Injuries', 'regex': '^[STU]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'RC', 'regex': '^[0-9A-HJ-NP-U]', 'type': 'readcode', 'source_file': 'medical'},
    {'signal': 'Drug', 'type': 'readcode',  'source_file': 'therapy'}
]

final = final.append(rc_codes)

demo_codes = [{'signal': 'GENDER', 'source_file': 'patient', 'value_field': 'sex'},
              {'signal': 'BYEAR', 'source_file': 'patient', 'value_field': 'yob'},
              {'signal': 'STARTDATE', 'source_file': 'patient', 'value_field': 'regdate'},
              {'signal': 'ENDDATE', 'source_file': 'patient', 'value_field': 'xferdate'},
              {'signal': 'DEATH', 'source_file': 'patient', 'value_field': 'deathdate'}]
final = final.append(demo_codes)

final.sort_values(by='signal', inplace=True)
#final[cols].to_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t', index=False, header=True, mode='w', line_terminator='\n')
final_x.sort_values(by='signal', inplace=True)
final_x[cols].to_csv(os.path.join(code_folder, 'thin_signal_mapping_qunt.csv'), sep='\t', index=False, header=True, mode='w', line_terminator='\n')

#write_tsv(final[cols], out_folder, 'thin_signal_mapping.csv', headers=True)
#print(file_to_sig_map)




