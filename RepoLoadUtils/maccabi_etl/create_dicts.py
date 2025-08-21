import os
import pandas as pd
import numpy as np
import sys
MR_ROOT = '/opt/medial/tools/bin/RepoLoadUtils'
sys.path.append(os.path.join(MR_ROOT, 'common'))

from shutil import copy
from Configuration import Configuration
from utils import write_tsv, fixOS, add_fisrt_line, is_nan, add_last_line, replace_spaces
from drugs_to_load_files import get_largo_map
from tyatuk import english_first
# -*- coding: utf-8 -*-

def code_desc_to_dict_df(df, dc_start, desc_last=False):
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))    
    cols = ['defid', 'desc', 'code']
    if desc_last:
        cols = ['defid', 'code', 'desc']
    to_stack = df[cols].set_index('defid', drop=True)
    dict_df = to_stack.stack().to_frame()
    dict_df['defid'] = dict_df.index.get_level_values(0)
    dict_df.rename({0: 'code'}, axis=1, inplace=True)
    dict_df['def'] = 'DEF'
    return dict_df


def code_desc_to_dict_df_3(df, dc_start):
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))    
    to_stack = df[['defid', 'desc', 'code', 'code1']].set_index('defid', drop=True)
    dict_df = to_stack.stack().to_frame()
    dict_df['defid'] = dict_df.index.get_level_values(0)
    dict_df.rename({0: 'code'}, axis=1, inplace=True)
    dict_df['def'] = 'DEF'
    return dict_df
'''
def create_drug_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    atc_codes = os.path.join(data_path, 'atc_codes.txt')
    atc_codes_df = pd.read_csv(atc_codes, sep='\t', encoding='utf-8')
    atc_codes_df.rename(columns={'ATC_CD':'code', 'ATC_Desc': 'desc'}, inplace=True)    
    atc_codes_df['desc'] = atc_codes_df['desc'].str.upper().str.strip()
    atc_codes_df['code'] = atc_codes_df['code'].str.upper().str.strip()
    
    all_atc_codes = os.path.join(code_path, 'ATCcodes.txt')
    all_atc_df = pd.read_csv(all_atc_codes, sep='\t', names=['code', 'all_desc'])
    #all_atc_df['code'] = all_atc_df['code'].str.upper().str.strip()
    all_atc_df['all_desc'] = all_atc_df['all_desc'].str.upper().str.strip()
    
    all_atc_df['code_underscore'] = all_atc_df['code'].str.replace(' ', '_').str.ljust(8, '_')
    all_atc_df['code'] = all_atc_df['code'].str.replace(' ', '')
    atc_codes_df = atc_codes_df.merge(all_atc_df, on='code', how='outer')
    
    atc_codes_df['desc'] = atc_codes_df['desc'].where(atc_codes_df['desc'].notnull(), atc_codes_df['all_desc'])
    atc_codes_df.drop_duplicates(subset=['code', 'desc'], inplace=True)
    
    atc_codes_df['code1'] = 'ATC_' + atc_codes_df['code_underscore']
    atc_codes_df['desc'] = atc_codes_df['code'] + ':' + replace_spaces(atc_codes_df['desc'])
    atc_codes_df['desc']  = atc_codes_df['desc'].str.replace(',', '_')
    dc_start = 1200
    
    dict_file = 'dict.atc_defs'
    signal = 'Drug'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    dict_df = code_desc_to_dict_df_3(atc_codes_df, dc_start)
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\tDrug,Drug_purchase,Drug_prescription\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    set_file = 'dict.atc_sets'
    if os.path.exists(os.path.join(dict_path, set_file)):
        os.remove(os.path.join(dict_path, set_file))
    set_dict = pd.DataFrame()
    # Set from ATC hierarchy
    atc_codes_df = atc_codes_df[atc_codes_df['code1'].notnull()]
    for _, atc1 in atc_codes_df[['code1', 'desc']].iterrows():
        val = atc1['code1']
        val_strip = val.replace('_', '')
        for inn in [s for s in atc_codes_df['code1'].values if val_strip in s.replace('_', '') and len(s.replace('_', '')) > len(val_strip)]:
            set_dict = set_dict.append({'outter': val, 'inner': inn}, ignore_index=True)
    #print(set_dict)
    set_dict['type'] = 'SET'
    write_tsv(set_dict[['type', 'outter', 'inner']], dict_path, set_file)
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    print('DONE atc_dicts')
'''

def create_drug_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    first_line = 'SECTION\tDrug,Drug_purchase,Drug_prescription,Drug_purchase_simple,Drug_prescription_simple\n'
    dict_file = 'dict.largo'
    dc_start = 500000
    largo_df = get_largo_map()
    largo_df['parma_grp'] = 'PHARMA_GRP:' + largo_df['PHARMACOLOGICAL_GROUP_CD'].astype(str)+':'+replace_spaces(largo_df['PHARMACOLOGICAL_GROUP_DESC'])
    largo_df['treat_grp'] = 'TREATMENT_GR:' + largo_df['TREATMENT_GROUP_CD'].astype(str)+':'+replace_spaces(largo_df['TREATMENT_GROUP_DESC'])
    largo_df['code'] = 'LARGO_CODE:' + largo_df['LARGO_CD'].astype(str)
    
    # Get missing LARGO codes list
    missing_df = pd.read_csv(os.path.join(out_folder, 'missing_largos.csv'), names=['code'])
    missing_df['desc'] = missing_df['code'] + ':UNKNOWN'
    
    lrgo_code_df = largo_df[['code', 'MEDICINE_NAME']].copy()
    lrgo_code_df.drop_duplicates(inplace=True)
    lrgo_code_df['desc'] = 'LARGO_DESC:' +largo_df['LARGO_CD'].astype(str)+ ':' + replace_spaces(lrgo_code_df['MEDICINE_NAME'])
    lrgo_code_df = pd.concat([lrgo_code_df, missing_df])
    largo_code_dict = code_desc_to_dict_df(lrgo_code_df, dc_start)
    
    new_start = largo_code_dict['defid'].max()+100
    largo_dict1 = pd.DataFrame(data=largo_df['dose'].unique(), columns=['code'])
    largo_dict2 = pd.DataFrame(data=largo_df['parma_grp'].unique(), columns=['code'])
    largo_dict3 = pd.DataFrame(data=largo_df['treat_grp'].unique(), columns=['code'])
    largo_dict = pd.concat([largo_dict1, largo_dict2, largo_dict3])
    largo_dict = largo_dict.assign(defid=range(new_start, new_start + largo_dict.shape[0]))
    largo_dict['def'] = 'DEF'
    largo_dict = largo_code_dict.append(largo_dict)
    largo_dict = largo_dict.append({'def': 'DEF', 'defid': largo_dict['defid'].max()+1, 'code': 'DOSE:UNKNOWN'}, ignore_index=True)
    write_tsv(largo_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    largo_sets1 = largo_df[['parma_grp', 'code']]
    largo_sets1['set'] = 'SET'
    write_tsv(largo_sets1[['set', 'parma_grp', 'code']], dict_path, dict_file, mode='a')

    largo_sets2 = largo_df[['treat_grp', 'code']]
    largo_sets2['set'] = 'SET'
    write_tsv(largo_sets2[['set', 'treat_grp', 'code']], dict_path, dict_file, mode='a')

    atc_codes_df = largo_df[['ATC_CD', 'ATC_Desc']].copy()
    atc_codes_df.drop_duplicates(subset='ATC_CD', inplace=True)
    atc_codes_df.rename(columns={'ATC_CD':'code', 'ATC_Desc': 'desc'}, inplace=True)
    atc_codes_df['desc'] = atc_codes_df['desc'].str.upper().str.strip()
    atc_codes_df['code'] = atc_codes_df['code'].str.upper().str.strip()
    

    all_atc_codes = os.path.join(code_path, 'ATCcodes.txt')
    all_atc_df = pd.read_csv(all_atc_codes, sep='\t', names=['code', 'all_desc'])
    #all_atc_df['code'] = all_atc_df['code'].str.upper().str.strip()
    all_atc_df['all_desc'] = all_atc_df['all_desc'].str.upper().str.strip()
    
    all_atc_df['code_underscore'] = all_atc_df['code'].str.replace(' ', '_').str.ljust(8, '_')
    all_atc_df['code'] = all_atc_df['code'].str.replace(' ', '')
    atc_codes_df = atc_codes_df.merge(all_atc_df, on='code', how='outer')
    
    atc_codes_df['desc'] = atc_codes_df['desc'].where(atc_codes_df['desc'].notnull(), atc_codes_df['all_desc'])
    atc_codes_df.drop_duplicates(subset=['code', 'desc'], inplace=True)
    
    atc_codes_df['code1'] = 'ATC_' + atc_codes_df['code_underscore']
    atc_codes_df['desc'] = atc_codes_df['code'] + ':' + replace_spaces(atc_codes_df['desc'])
    atc_codes_df['desc']  = atc_codes_df['desc'].str.replace(',', '_')
    dc_start = 600000
    
    dict_file = 'dict.atc_defs'
    dict_df = code_desc_to_dict_df_3(atc_codes_df, dc_start)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'ATC_UNKNOWN'}, ignore_index=True)
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')

    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    set_file = 'dict.atc_sets'
    set_dict = pd.DataFrame()
    # Set from ATC hierarchy
    atc_codes_df = atc_codes_df[atc_codes_df['code1'].notnull()]
    for _, atc1 in atc_codes_df[['code1', 'desc']].iterrows():
        val = atc1['code1']
        val_strip = val.replace('_', '')
        for inn in [s for s in atc_codes_df['code1'].values if val_strip in s.replace('_', '') and len(s.replace('_', '')) > len(val_strip)]:
            set_dict = set_dict.append({'outter': val, 'inner': inn}, ignore_index=True)
    #print(set_dict)
    set_dict['type'] = 'SET'
    write_tsv(set_dict[['type', 'outter', 'inner']], dict_path, set_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    
    # SET LARGO to ATC
    set_file = 'dict.largo_atc_sets'
    largo_atc_df = largo_df[largo_df['ATC_CD'].notnull()][['LARGO_CD', 'ATC_CD']].copy()
    largo_atc_df.drop_duplicates(inplace=True)
    largo_atc_df['LARGO_CD'] = 'LARGO_CODE:' + largo_atc_df['LARGO_CD'].astype(str)
    largo_atc_df['type'] = 'SET'
    write_tsv(largo_atc_df[['type', 'ATC_CD', 'LARGO_CD']], dict_path, set_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    
    print('DONE Largo')

def create_diagnosis_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    #maccbi_codes = pd.read_csv(os.path.join(data_path,'diagnoses_codes.txt'), sep='\t')
    #maccbi_codes = pd.concat([maccbi_codes, maccbi_codes['DIAGNOSIS_DESC'].str.split('-', expand=True)], axis=1)
    #maccbi_codes['code'] = maccbi_codes[0].str.strip()
    #maccbi_codes['desc'] = maccbi_codes[1].str.strip()
    #maccbi_codes = maccbi_codes[['code', 'desc']]
    
    in_folder = os.path.join(fixOS(cfg.data_folder), 'hospital_diagnosis_data')
    file_list = os.listdir(in_folder)
    maccbi_codes = pd.DataFrame()
    for fl in file_list:
        fullfile = os.path.join(in_folder, fl)
        print('reading from: ' + fullfile) 
        encoding='cp1255'
        if 'delta' in fl:
            encoding = None
        mim_df = pd.read_csv(fullfile, sep='\t', encoding=encoding, usecols=['DiagName', 'DiagCode'])
        mim_df['DiagName'] = mim_df['DiagName'].str.strip()
        mim_df['DiagCode'] = mim_df['DiagCode'].astype(str).str.strip()
        mim_df.drop_duplicates(inplace=True)
        maccbi_codes = maccbi_codes.append(mim_df)
        maccbi_codes.drop_duplicates(inplace=True)
    maccbi_codes.rename(columns={'DiagName': 'desc','DiagCode': 'code'}, inplace=True) 
    print('1111')
    print(maccbi_codes[maccbi_codes['code'].astype(str).str.contains('71104')])
    
    missing_codes = pd.read_csv(os.path.join(data_path,'real_missing_diag_codes.txt'), sep='\t')
    missing_codes['code'] = missing_codes['code'].str.strip()
    missing_codes['desc'] = 'ICD9_CODE:' + missing_codes['code']
    dc_start = 1200
    dict_file = 'dict.icd9dx'
    #signal = 'DIAGNOSIS'

    ontology_folder = os.path.join(code_path, '../Ontologies/')
    icd9_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.icd9dx')
    icd9_set_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.set_icd9dx')    
    icd9_df = pd.read_csv(icd9_dict, sep='\t', encoding='utf-8', names=['def', 'defid', 'code'])
    no_prefix_df = icd9_df[icd9_df['code'].str.contains('ICD9_CODE')].copy()
    no_prefix_df['code'] = no_prefix_df['code'].str.replace('ICD9_CODE:', '')
    icd9_df = icd9_df.append(no_prefix_df)
    maccbi_codes = maccbi_codes[~(maccbi_codes['code'].isin(no_prefix_df['code'].values))]
    print('2222')
    print(maccbi_codes[maccbi_codes['code'].astype(str).str.contains('71104')])
    maccbi_codes['desc'] = 'ICD9_DESC:' + maccbi_codes['code'] + ':' + replace_spaces(maccbi_codes['desc'].str.strip())
    maccbi_codes['code1'] = 'ICD9_CODE:' + maccbi_codes['code']
    maccbi_codes_dict_df = code_desc_to_dict_df_3(maccbi_codes, dc_start+icd9_df.shape[0]+1)
    print('3333')
    print(maccbi_codes[maccbi_codes['code'].astype(str).str.contains('71104')])
    icd9_df = icd9_df.append(maccbi_codes_dict_df[['def', 'defid', 'code']])
    missing_codes = missing_codes[missing_codes['code'].notnull()]
    missing_codes = missing_codes[~(missing_codes['code'].isin(no_prefix_df['code'].values))]
    missing_codes = missing_codes[~(missing_codes['code'].isin(maccbi_codes['code'].values))]
    maccbi_missing_dict_df = code_desc_to_dict_df(missing_codes, dc_start+icd9_df.shape[0]+1)
    icd9_df = icd9_df.append(maccbi_missing_dict_df[['def', 'defid', 'code']])
    icd9_df = icd9_df[(icd9_df['code'].notnull()) & (icd9_df['code'].str.strip() != '') & (icd9_df['code'].str.strip() != 'ICD9_CODE:')]
    icd9_df['code'] = icd9_df['code'].str.replace(',', '_')
    icd9_df.drop_duplicates('code', keep='first', inplace=True)
    icd9_df.sort_values(by='defid', inplace=True)

    
    
    write_tsv(icd9_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\tDIAGNOSIS,Hospital_diagnosis\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    
    all_set_files = [os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.set_icd9dx'),
                     os.path.join(ontology_folder, 'ELIX_CHARL', 'dicts', 'dict.comorbidity_scores'),
                     os.path.join(ontology_folder, 'CCS', 'dicts', 'dict.ccs_diag_sets')]
    for set_file in all_set_files:
        copy(set_file, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(set_file)))
    print('DONE icd dict and set')
    
    in_folder = os.path.join(cfg.data_folder, 'hospital_diagnosis_data')
    file_list = os.listdir(in_folder)
    hosp_df = pd.DataFrame()
    for fl in file_list:
        hops_diag_file = os.path.join(in_folder, fl)
        print(hops_diag_file)
        encoding='cp1255'
        if fl.endswith('xlsx'):
            continue
            df = pd.read_excel(hops_diag_file, usecols = [2,3])
        else:
            if 'delta' in fl:
                encoding = None
            df = pd.read_csv(hops_diag_file, sep='\t', encoding=encoding, usecols = ['DiagCode','DiagName'])
        df.drop_duplicates(inplace=True)
        hosp_df = hosp_df.append(df, sort=False)
        hosp_df.drop_duplicates(inplace=True)
        print(hosp_df.shape[0])
    
    hosp_df['DiagName'] = hosp_df['DiagName'].apply(lambda x: str(x).split('Start Date')[0].strip())
    
    hosp_df.rename(columns={'DiagCode':'code', 'DiagName': 'desc'}, inplace=True)
    hosp_df = hosp_df[(hosp_df['code'].notnull()) | (hosp_df['desc'].notnull())]
    hosp_df['code'] = hosp_df['code'].str.strip()    
    hosp_df.loc[hosp_df['code'].isnull(), 'split_code'] = hosp_df[hosp_df['code'].isnull()]['desc'].apply(lambda x: str(x).split(' ')[-1])
    cond = (hosp_df['code'].isnull()) & (hosp_df['split_code'].str[-1].str.isdigit()) & (hosp_df['split_code'].str.contains('.', regex=False))
    #print(hosp_df)
    hosp_df.loc[cond ,'code'] = hosp_df[cond]['split_code']
    hosp_df['desc'] = replace_spaces(hosp_df['desc'].str.strip())
    hosp_df['code'] = replace_spaces(hosp_df['code'].str.strip())
    hosp_df['code'] = hosp_df['code'].str.strip(',')
    hosp_df['code'] = hosp_df['code'].str.replace(',','.')
    hosp_df['code'] = hosp_df['code'].str.replace('9h_', '')
    cond2 = (hosp_df['code'].str[-1] == '0') & (hosp_df['code'].str[-2] != '.') & (hosp_df['code'].str.contains('.', regex=False))
    hosp_df.loc[cond2, 'code'] = hosp_df[cond2]['code'].str[:-1]
    
    hosp_df['desc'] = hosp_df['desc'].str.replace('"', '')
    hosp_df.loc[(hosp_df['code'].isnull()), 'code'] = hosp_df[(hosp_df['code'].isnull())]['desc']
    hosp_df.drop_duplicates(subset='code', inplace=True)
    
    icd_map = icd9_df.set_index('code')['defid']
    hosp_df['mapped'] = hosp_df['code'].map(icd_map)

    hosp_df = hosp_df[hosp_df['mapped'].isnull()]
    
    #cond2 = (hosp_df['code'].str[-1] == '0') & (hosp_df['code'].str[-2] != '.')
    #hosp_df.loc[cond2, 'code1'] = hosp_df[cond2]['code'].str[:-1]
    #hosp_df = hosp_df[~hosp_df['code'].isin(hosp_df['code1'].values)]
    hosp_df['desc'] = 'MACCABI_DIAG:'+ hosp_df['code'] +':' + hosp_df['desc']
   
    dc_start = 12000
    dict_file = 'dict.diag_hospital'
    hosp_dict_df = code_desc_to_dict_df(hosp_df, dc_start+hosp_df.shape[0]+1)
    hosp_dict_df = hosp_dict_df[(hosp_dict_df['code'].notnull()) & (hosp_dict_df['code'].str.strip() != '')]
    write_tsv(hosp_dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\tDIAGNOSIS,Hospital_diagnosis\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE hospital diagnosis dicts')


def create_vaccinations_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    
    vacc_codes = os.path.join(data_path, 'vaccine_codes.txt')
    vacc_codes_df = pd.read_csv(vacc_codes, sep='\t', encoding='cp1255')
    vacc_codes_df['cd2'] = vacc_codes_df['PARIT_IN_MAAKAV_CD2'].str.zfill(2).str.strip()
    vacc_codes_df['code'] = vacc_codes_df['PARIT_IN_MAAKAV_CD1'].astype(str) + '_'+ vacc_codes_df['cd2'] 
    vacc_codes_df.rename(columns={'PARIT_MAAKAV_DESC': 'desc'}, inplace=True)
    vacc_codes_df['desc'] = replace_spaces(vacc_codes_df['desc'].str.strip())
    vacc_codes_df['desc'] = vacc_codes_df['desc'].str.replace(',', '_')
    vacc_codes_df['desc'] = 'MACCABI_VACC:' + vacc_codes_df['code'] +':' + vacc_codes_df['desc']
    vacc_codes_df.drop_duplicates(subset=['code', 'desc'], inplace=True)
    dc_start = 5000
    dict_file = 'dict.vacc_defs'
    signal = 'Vaccination'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    dict_df = code_desc_to_dict_df(vacc_codes_df, dc_start)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+10, 'code': '90793_'}, ignore_index=True)
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE vacc_dicts')


def create_smoking_dict():
    signal = 'Smoking_Status'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 100
    dict_file = 'dict.smoking'
    dict_list = [{'code': 1, 'desc': 'Current'},
                  {'code': 2, 'desc': 'Former'},
                  {'code': 3, 'desc': 'Never'},
                  {'code': 4, 'desc': 'Unknown'}]
    dict_df = pd.DataFrame(dict_list)
    dict_df = code_desc_to_dict_df(dict_df, dc_start, desc_last=True)
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE smoking')


def create_departmet_dict():
    cfg = Configuration()   
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 100
    dict_file = 'dict.department'
    
    #hops_file = os.path.join(fixOS(cfg.data_folder), 'hospitalizations_data' , 'Medial_Flu_delta_hospitalizations_data.txt')
    hops_file = os.path.join(fixOS(cfg.data_folder), 'FLU_DATA_29_07_2020' , 'Medial_Flu_hospitlization_data.txt')
    hosp_df = pd.read_csv(hops_file, sep='\t', usecols = ['CARE_GIVER_DPRT_TYPE_CD','CARE_GIVER_DPRT_TYPE_DESC', 'CARE_GIVER_DPRT_CD', 'CARE_GIVER_DPRT_DESC'], encoding='cp1255')
    hosp_df.drop_duplicates(inplace=True)
    hosp_df.rename(columns={'CARE_GIVER_DPRT_TYPE_CD':'code1', 'CARE_GIVER_DPRT_TYPE_DESC': 'desc1'}, inplace=True)
    hosp_df.rename(columns={'CARE_GIVER_DPRT_CD':'code2', 'CARE_GIVER_DPRT_DESC': 'desc2'}, inplace=True)
    hosp_df = hosp_df[hosp_df['code1'].notnull()]
    hosp_df['code'] = hosp_df['code1'].astype(int).astype(str) + '_' + hosp_df['code2'].astype(int).astype(str)
    hosp_df.drop_duplicates(subset='code', inplace=True)
    hosp_df['desc1'] = hosp_df['desc1'].str.replace("'", "").str.replace(",", "_")
    hosp_df['desc2'] = hosp_df['desc2'].str.replace("'", "").str.replace(",", "_")
    hosp_df['code1'] = hosp_df['desc1'].str.strip() + '-' + hosp_df['desc2'].str.strip()
    hosp_df['code1'] = hosp_df['code'] + ':' + replace_spaces(hosp_df['code1'])
    
    hosp_df['desc1'] = hosp_df['desc1'].apply(lambda x: english_first(x))
    hosp_df['desc2'] = hosp_df['desc2'].apply(lambda x: english_first(x))
    hosp_df['desc'] = hosp_df['desc1'].str.strip() + '-' + hosp_df['desc2'].str.strip()
    hosp_df['desc'] = hosp_df['code'] + ':' + replace_spaces(hosp_df['desc'])
    
    hosp_df = code_desc_to_dict_df_3(hosp_df, dc_start)
    write_tsv(hosp_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\tSTAY,ADMISSION\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE department')


def create_cancer_dict():
    signal = 'Cancer_registry'
    cfg = Configuration()   
    out_folder = fixOS(cfg.work_path)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 100
    dict_file = 'dict.cancer'
    
    cancer_codes_file = os.path.join(data_path, 'Cancer_Codes_Descriptions.txt')
    cancer_codes_df = pd.read_csv(cancer_codes_file, sep='\t', names=['upgroup_code', 'upgroup_desc',
                                                                      'group_code', 'group_desc',
                                                                      'disease_code', 'disease_desc'], header=0)
    #print(cancer_codes_df)    
    cancer_codes_df['upgroup_desc'] = cancer_codes_df['upgroup_desc'].str.strip().str.replace(' ', '_')
    cancer_codes_df['group_desc'] = cancer_codes_df['group_desc'].str.strip().str.replace(' ', '_')
    cancer_codes_df['disease_desc'] = cancer_codes_df['disease_desc'].str.strip().str.replace(' ', '_')
    cancer_codes_df['code'] = cancer_codes_df['upgroup_code'].astype(int)*10 + cancer_codes_df['group_code'].astype(int) + cancer_codes_df['disease_code'].astype(int)
    cancer_codes_df['desc'] = cancer_codes_df['code'].astype(str) +':'+cancer_codes_df['upgroup_desc'] + ':' + cancer_codes_df['group_desc'] + ':' + cancer_codes_df['disease_desc']
    cancer_dict = code_desc_to_dict_df(cancer_codes_df, dc_start)
    
    grp_codes = (cancer_codes_df['upgroup_desc'] + ':' + cancer_codes_df['group_desc']).unique()
    grp_codes = grp_codes.tolist() + (cancer_codes_df['upgroup_desc'].unique()).tolist()
    cancer_dict_grp = pd.DataFrame(grp_codes, columns =['code'])
    dc_start = cancer_dict['defid'].max() + 1
    cancer_dict_grp = cancer_dict_grp.assign(defid=range(dc_start, dc_start + cancer_dict_grp.shape[0]))
    cancer_dict_grp['def'] = 'DEF'
    cancer_dict = pd.concat([cancer_dict, cancer_dict_grp])
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(cancer_dict[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    
    set_file = 'dict.cancer_set'
    cancer_set = pd.DataFrame(cancer_codes_df['desc'].values, columns=['inner'])
    cancer_set['outer'] = cancer_codes_df['upgroup_desc'] + ':' + cancer_codes_df['group_desc']
    cancer_set2 = pd.DataFrame(cancer_set['outer'].values, columns=['inner'])
    cancer_set2['outer'] = cancer_codes_df['upgroup_desc']
    cancer_set = pd.concat([cancer_set, cancer_set2])
    cancer_set['set'] = 'SET'
    #print(cancer_set)
    
    if os.path.exists(os.path.join(dict_path, set_file)):
        os.remove(os.path.join(dict_path, set_file))
    write_tsv(cancer_set[['set', 'outer', 'inner']], dict_path, set_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    
    
    print('DONE cancer registry')
    
    
def create_cat_labs_dict():
    signals = ['Urine_Leucocytes', 'Urine_Nitrit', 'Urine_PH', 'Urine_Protein', 'Urine_Glucose',
               'Urine_Ketone', 'Urine_Urobilinogen', 'Urine_Bilirubin', 'Urine_Erythrocytes', 'Urine_Spec_Gravity']
    cfg = Configuration()   
    out_folder = fixOS(cfg.work_path)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    signals_path = os.path.join(out_folder, 'FinalSignals')
    all_files = os.listdir(signals_path)
    dc_start = 1000
    dict_file = 'dict.urine_labs'
    
    remarks_file = os.path.join(data_path, 'lab_remark_codes.txt')
    remarks_df = pd.read_csv(remarks_file, sep='\t', encoding='cp1255', names=['rm_code', 'desc'])
    remarks_df['rm_code'] = remarks_df['rm_code'].str.strip()
    remarks_df['desc'] = remarks_df['rm_code'] + ':' + remarks_df['desc'].astype(str).str.strip().str.replace(' ', '_')
    remarks_df['desc'] = remarks_df['desc'].str.replace(',', '_')
    vals_list = []
    for sig in signals:
        sig_files = [x for x in all_files if x.startswith(sig)]        
        #sig_files = [sig+'1']
        print(sig_files)
        for fl in sig_files:
            if fl == 'Urine_Protein_24hr1':
                continue
            fullfile =os.path.join(signals_path, fl)            
            print(' Reading '  +fl)
            df = pd.read_csv(fullfile, sep='\t',  engine='python',usecols=[3], names=['value'], header=0)
            vals = list(df['value'].unique())
            vals_list = list(set(vals_list + vals))
    cats_df = pd.DataFrame(vals_list, columns=['code'])
    cats_df = cats_df.merge(remarks_df, how='left', left_on='code', right_on='rm_code')
    cats_dict = code_desc_to_dict_df(cats_df[cats_df['rm_code'].notnull()], dc_start)
    cat_dict2= cats_df[cats_df['rm_code'].isnull()][['code']]
    dc_start = cats_dict['defid'].max() + 1
    cat_dict2 = cat_dict2.assign(defid=range(dc_start, dc_start + cat_dict2.shape[0]))
    cat_dict2['def'] = 'DEF'
    cats_dict = pd.concat([cats_dict[['def', 'defid', 'code']], cat_dict2[['def', 'defid', 'code']]])
    #print(cats_dict)
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(cats_dict[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + ",".join(signals) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE urine labs')

def create_diabetic_registry_dict():
    signal = 'Diabetic_registry'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 1
    dict_file = 'dict.Diabetic_registry'
    dict_list = [{'code': 1, 'desc': 'Pre_Diabetic'},
                 {'code': 2, 'desc': 'Pre_Diabetic_High_Risk'},
                 {'code': 3, 'desc': 'Diabetic'}]
    dict_df = pd.DataFrame(dict_list)
    dict_df = code_desc_to_dict_df(dict_df, dc_start)
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE Diabetic_registry')
    
def create_procedure_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    data_path = os.path.join(fixOS(cfg.data_folder), 'codes')
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    
    prod_codes = os.path.join(data_path, 'treatments_codes2.txt')
    prod_codes_df = pd.read_csv(prod_codes, sep='\t', usecols=[0,1,2,4], encoding='utf-8')
    
    prod_codes_df['cd2'] = prod_codes_df['CARE_CHARACTERIZATION'].str.strip().str.zfill(2)
    prod_codes_df['cd2'].fillna('', inplace=True)
    prod_codes_df['code'] = prod_codes_df['CARE_CODE'].astype(str) + '_'+ prod_codes_df['cd2'] + '_' + prod_codes_df['CARE_NUMBER'].astype(str)

    prod_codes_df['len'] = prod_codes_df['CARE_ENG_DESC'].str.len()
    prod_codes_df.sort_values(by=['code', 'len'], ascending=[True, False], inplace=True)
    prod_codes_df = prod_codes_df.drop_duplicates(subset=['code'], keep='first')
    prod_codes_df.rename(columns={'CARE_ENG_DESC': 'desc'}, inplace=True)
    prod_codes_df['desc'] = prod_codes_df['code']+':'+replace_spaces(prod_codes_df['desc'].str.strip())
    prod_codes_df['desc'] = prod_codes_df['desc'].str.replace(',', '_')

    miss_prod_file = os.path.join(data_path, 'missing_proc.txt')
    miss_prod_codes = pd.read_csv(miss_prod_file, names=['code'])
    prod_codes_df = prod_codes_df.append(miss_prod_codes, sort=True)

    dc_start = 6000
    dict_file = 'dict.proc_defs'
    signal = 'Procedure'
    dict_df = code_desc_to_dict_df(prod_codes_df, dc_start)
    dict_df = dict_df[(dict_df['code'].notnull()) & (dict_df['code'] != '.')]
    '''
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+10, 'code': '0__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '90768__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '91744__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_06_40'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_06_60'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '67036__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '44200__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '1112__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '1573__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '1574__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '1581__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '474__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '5102__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_48_26'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '63185_02_0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_32_27'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_06_61'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99231_35_0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '4424__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '5011__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '44423__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '10098__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_26_26'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '864__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '6891__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_31_27'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '45__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'Z001 __0 '}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '72195_06_0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '93797_04_0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '5__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_24_27'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99373__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'K330 __0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '76094__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99337__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_30_27'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_43_98'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_99_1'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99281__0'}, ignore_index=True)
    
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '841__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'D010 __0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_63_22'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_29_27'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '83904_32_0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'D333 __0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '44421__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_45_1'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '572 __0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '851__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_67_23'}, ignore_index=True)
    
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '1704__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '6827__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': 'D200 __0 '}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_37_26'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_12_26'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_85_24'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_66_23'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '99199_39_23'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '90865__0'}, ignore_index=True)
    dict_df = dict_df.append({'def': 'DEF', 'defid': dict_df['defid'].max()+1, 'code': '90866__0'}, ignore_index=True)
    '''
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE proc_dicts')

    
def create_doctors_dict():
    signal = 'Drug_prescription,Drug_purchase'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    codes_list_path = fixOS(cfg.codes_folder)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    
    
    dc_start = 10000
    dict_file = 'dict.doctors'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    
    doc_codes = os.path.join(codes_list_path, 'Physician_random_id_desc.txt')
    docs_df = pd.read_csv(doc_codes, sep='\t', encoding='cp1255')
    docs_df.rename(columns={'PHYSICIAN_random_id': 'doc_id', 'SUP_GROUP_CD':'code', 'SUP_GROUP_DESC': 'desc'}, inplace=True)
    #docs_df['doc_id'] = 'DOC_ID:' + docs_df['doc_id'].astype(str)
    doc_num_dict = docs_df[['doc_id']].copy()
    doc_num_dict.drop_duplicates(inplace=True)
    doc_num_dict['def'] = 'DEF'
    doc_num_dict.rename(columns={'doc_id': 'code'}, inplace=True)
    doc_num_dict = doc_num_dict.assign(defid=range(dc_start, dc_start + doc_num_dict.shape[0]))
    dc_start = doc_num_dict['defid'].max() + 10

    doc_spec = docs_df[['doc_id', 'code', 'desc']].copy()
    doc_spec['code'] = 'SPEC_ID:' + doc_spec['code']
    doc_spec.drop_duplicates(inplace=True)
    doc_spec['desc'] = doc_spec['desc'].str.replace('"', '')
    doc_spec['code1'] = doc_spec['desc'].apply(lambda x: english_first(x))
    doc_spec['desc'] = doc_spec['code'].astype(str) + ':' + replace_spaces(doc_spec['desc'])
    doc_spec['code1'] = doc_spec['code'].astype(str) + ':' + replace_spaces(doc_spec['code1'])
    dec_spec_def = doc_spec[['code', 'code1', 'desc']].drop_duplicates()
    spec_dict = code_desc_to_dict_df_3(dec_spec_def, dc_start)
    
    cols = ['def', 'defid', 'code']
    doc_dict = pd.concat([doc_num_dict[cols], spec_dict[cols]])
    doc_dict = doc_dict.append({'def': 'DEF', 'defid': doc_dict['defid'].max()+1, 'code': '0'}, ignore_index=True)
    doc_dict = doc_dict.append({'def': 'DEF', 'defid': doc_dict['defid'].max()+1, 'code': '0:Unknown'}, ignore_index=True)
    doc_dict.drop_duplicates(inplace=True)
    write_tsv(doc_dict[['def', 'defid', 'code']], dict_path, dict_file)
    
    set_df = doc_spec[['doc_id','code1']].copy()
    set_df['def'] = 'SET'
    write_tsv(set_df[['def', 'code1', 'doc_id']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file)) # !!!!!!!!!!!!!!!!!!! ADD when knowen
    print('DONE doctors dict')

def create_assessment_dict():
    signal = 'ASSESMENT'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    codes_list_path = fixOS(cfg.codes_folder)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 900
    dict_file = 'dict.assessment'
    
    codes_list = [
    (21,'PHQ9'),
    (22,'ADL'),
    (38,'IADL'),
    (40,'PHQ2'),
    (43,'SW16'),
    (44,'BARTHEL')]

    dct_list = [{'code': 'ASSESSMENT_CODE:'+str(x[0]), 'desc': x[1]} for x in codes_list]
    as_df = pd.DataFrame(dct_list)

    dict_df = code_desc_to_dict_df(as_df, dc_start)
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE assessment dict')

def create_covid_dict():
    signal = 'COVID19_TEST,COVID19_COMP_REG'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 800
    dict_file = 'dict.covid19'
    stat_map = {1:'Mild' , 2: 'Moderate' , 3: 'Severe', 4: 'Critical', 5: 'Deceased' , 0:'Recovered', -1: 'Unknown',
                'COVID_RES:1': 'Negative', 'COVID_RES:2': 'Positive', 'COVID_RES:3': 'InProcess'}
    list_df = [{'code': k, 'desc': v} for k,v in stat_map.items()]
    print(pd.DataFrame(list_df))
    dict_df = code_desc_to_dict_df(pd.DataFrame(list_df), dc_start)
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE COVID19 dict')
    
def create_visits_dict():
    signal = 'VISITS'
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    dc_start = 7000000
    dict_file = 'dict.specialities'
    visits_path = '/data/VisitTexts/Rearranged'
    file_names = os.listdir(visits_path)
    
    list_df = [{'code': x.split('.')[1].strip()} for x in file_names]
    dict_df = pd.DataFrame(list_df)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def']  = 'DEF'
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    
if __name__ == '__main__':
    #create_drug_dicts()
    create_diagnosis_dicts()
    #create_vaccinations_dicts()
    #create_smoking_dict()
    #create_departmet_dict()
    #create_cancer_dict()
    #create_cat_labs_dict()
    #create_diabetic_registry_dict()
    #create_procedure_dict()
    #create_doctors_dict()
    #create_assessment_dict()
    #create_covid_dict()
    #create_visits_dict()