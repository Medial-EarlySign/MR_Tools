import pandas as pd
import numpy as np
import os
import sys
from shutil import copy
#sys.path.append(os.path.join('/opt/medial/tools/bin/', 'RepoLoadUtils','common'))
sys.path.append('/opt/medial_sign/med_scripts/ETL/common')
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df
from db_connect import DB
from db_to_load_files import get_map, get_flu_pcr_query
from dicts_utils import create_dict_generic


gender_map = {1: 'Male', 2: 'Female'}


def create_gender_dict(dict_path):
    sec = 'GENDER'
    dict_file = 'dict.gender'
    dict_df = pd.Series(gender_map).reset_index()
    dict_df['def'] = 'DEF'
    cols = ['def', 'index', 0]
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sec + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_demographic_dict(dict_path, db_con):
    demo_sigs = ['RACE', 'ETNICITY', 'INSURENCE', 'INSURENCE_LOB']
    dict_file = 'dict.demo'
    dc_start = 1000
    query = "SELECT DISTINCT(col_name) FROM [flu].[DEMOGRAPHICS]"
    demo_cols = ['PT_RACE_1', 'PT_ETHNICITY', 'PT_INS_TYPE_NM']
    dict_df = pd.DataFrame()
    for col in demo_cols:
        sql_query = query.replace('col_name', col)
        df = pd.read_sql(sql_query, db_con)
        df.rename(columns={col:'desc'}, inplace=True)
        df = df[(df['desc'].notnull()) & (df['desc'].str.strip() != '')]
        dict_df = dict_df.append(df, sort=False)
    dict_df['desc'] = replace_spaces(dict_df['desc'].str.upper())
    dict_df.drop_duplicates(inplace=True)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'desc']
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(demo_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_diagnosis_dict(onto_path, dict_path, db_con):
    sig = 'DIAGNOSIS' #,Drug_detailed'
    dict_file = 'dict.diag'
    dc_start = 10000
    
    icd9_dict_file = os.path.join(onto_path, 'ICD9', 'dicts', 'dict.icd9dx')
    icd9_dict = pd.read_csv(icd9_dict_file, sep='\t', names=['def', 'defid', 'code'])
    icd10_dict_file = os.path.join(onto_path, 'ICD10', 'dicts', 'dict.icd10')
    icd10_dict = pd.read_csv(icd10_dict_file, sep='\t', names=['def', 'defid', 'code'])
    exists_codes = pd.concat([icd9_dict[icd9_dict['code'].str.contains('ICD9_CODE')]['code'], 
                   icd10_dict[icd10_dict['code'].str.contains('ICD10_CODE')]['code']])
    query1 = "SELECT DX_CD, CODE_SYSTEM, max(DX_NM) as desc1 FROM [flu].[ENCOUNTERS_DX] GROUP BY DX_CD, CODE_SYSTEM"
    query2 = "SELECT PROB_DX_CD as DX_CD, CODE_SYSTEM, max(PROB_DX_NM) as desc1 FROM [flu].[PROBLEM_LIST] GROUP BY PROB_DX_CD, CODE_SYSTEM"
    all_diag = pd.DataFrame()
    for query in [query1, query2]:
        df = pd.read_sql(query, db_con)
        df['code'] = df['CODE_SYSTEM'].str.replace('CM', '_CODE') + ':' + replace_spaces(df['DX_CD'].str.replace('.', ''))
        df = df[~df['code'].isin(exists_codes)]
        df['desc1'] = df['code'] + ':' + replace_spaces(df['desc1'].str.upper())
        all_diag = all_diag.append(df, sort=False)
    all_diag.drop_duplicates('code', inplace=True)
    diag_dict = code_desc_to_dict_df(all_diag, dc_start, ['code', 'desc1'])
    write_tsv(diag_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)


def copy_diag_dicts(onto_path, dict_path):
    sig = 'DIAGNOSIS' #,Drug_detailed'
    first_line = 'SECTION\t' + sig + '\n'
    diag_dict_files = [os.path.join(onto_path, 'ICD9', 'dicts', 'dict.icd9dx'),
                       os.path.join(onto_path, 'ICD9', 'dicts', 'dict.set_icd9dx'),
                       os.path.join(onto_path, 'ICD10', 'dicts', 'dict.icd10'),
                       os.path.join(onto_path, 'ICD10', 'dicts', 'dict.set_icd10')]
    for dict_file in diag_dict_files:
        copy(dict_file, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(dict_file)))

def map_dx_icd(dict_path, db_con):
    sig = 'DIAGNOSIS' #,Drug_detailed'
    dict_file = 'dict.dx_icd_set'
    query9 = "SELECT DISTINCT DX_ID, CS_CD, CODE_SYSTEM FROM [medial].[flu].[DXID_TO_ICD9] WHERE CONCEPT_NM != 'ICD CONCEPT NAME NOT AVAILABLE' AND CODE_SYSTEM = 'ICD9CM' AND DX_ID IN (SELECT DISTINCT(DX_CD) FROM [medial].[flu].[ENCOUNTERS_DX] WHERE [CODE_SYSTEM] = 'EDG')"
    query10 = "SELECT DISTINCT DX_ID, CS_CD, CODE_SYSTEM FROM [medial].[flu].[DXID_TO_ICD10] WHERE CONCEPT_NM != 'ICD CONCEPT NAME NOT AVAILABLE' AND CODE_SYSTEM = 'ICD10CM' AND DX_ID IN (SELECT DISTINCT(DX_CD) FROM [medial].[flu].[ENCOUNTERS_DX] WHERE [CODE_SYSTEM] = 'EDG')"
    set_df = pd.DataFrame()
    for query in [query9, query10]:
        df = pd.read_sql(query, db_con)
        df['icd_code'] = df['CODE_SYSTEM'].str.replace('CM', '_CODE') + ':' + replace_spaces(df['CS_CD'].str.replace('.', ''))
        df['DX_ID'] = 'EDG:' + df['DX_ID'].astype(str)
        set_df = set_df.append(df)
    set_df['set'] = 'SET'
    # fix mapping errors in AAA/TAA in mapping
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4412') & (set_df['DX_ID'] == 'EDG:17119'), 'icd_code'] = 'ICD9_CODE:4419'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:332549'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD10_CODE:I719') & (set_df['DX_ID'] == 'EDG:332549'), 'icd_code'] = 'ICD10_CODE:I712'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:312797'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:506658'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4415') & (set_df['DX_ID'] == 'EDG:15782'), 'icd_code'] = 'ICD9_CODE:4411'
    set_df.loc[(set_df['icd_code'] == 'ICD10_CODE:I718') & (set_df['DX_ID'] == 'EDG:15782'), 'icd_code'] = 'ICD10_CODE:I711'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:15783'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:505898'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:332548'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD10_CODE:I719') & (set_df['DX_ID'] == 'EDG:332548'), 'icd_code'] = 'ICD10_CODE:I712'
    set_df.loc[(set_df['icd_code'] == 'ICD9_CODE:4419') & (set_df['DX_ID'] == 'EDG:159307'), 'icd_code'] = 'ICD9_CODE:4412'
    set_df.loc[(set_df['icd_code'] == 'ICD10_CODE:I719') & (set_df['DX_ID'] == 'EDG:159307'), 'icd_code'] = 'ICD10_CODE:I712'


    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:229794')]
    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:229793')]
    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:505829')]
    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:408135')]
    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:528127')]
    set_df = set_df[(set_df['icd_code'] != 'ICD9_CODE:4419') | (set_df['DX_ID'] != 'EDG:1349927')]
    set_df = set_df[(set_df['icd_code'] != 'ICD10_CODE:I719') | (set_df['DX_ID'] != 'EDG:1349927')]
    write_tsv(set_df[['set', 'icd_code', 'DX_ID']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    
    
    
def create_smoke_dict(dict_path, db_con):
    sig = 'Smoking_Status'
    req_stst = ['Never', 'Passive', 'Former', 'Current', 'Never_or_Former', 'Unknown']
    map_stat = {'Never': ['NEVER_SMOKER'],
                'Passive': ['PASSIVE_SMOKE_EXPOSURE_-_NEVER_SMOKER'],
                'Former': ['FORMER_SMOKER'],
                'Current': ['CURRENT_EVERY_DAY_SMOKER', 'CURRENT_SOME_DAY_SMOKER', 'HEAVY_TOBACCO_SMOKER', 'LIGHT_TOBACCO_SMOKER', 'SMOKER_CURRENT_STATUS_UNKNOWN'],
                'Unknown': ['UNKNOWN_IF_EVER_SMOKED', 'NEVER_ASSESSED']
                }
    dict_file = 'dict.smoke'
    dc_start = 20000
    query = "SELECT DISTINCT(SOC_HX_SMOKE_STTS) FROM [medial].[flu].[SOCIAL_HISTORY]"
    dict_df = pd.read_sql(query, db_con)
    dict_df = dict_df.append(pd.DataFrame(data=req_stst, columns=['SOC_HX_SMOKE_STTS']))
    dict_df['code'] = replace_spaces(dict_df['SOC_HX_SMOKE_STTS'])
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'code']
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    set_list = [{'set': 'SET', 'outer': mp, 'inner': st} for mp, lst in map_stat.items() for st in lst]
    set_df = pd.DataFrame(set_list)
    write_tsv(set_df[['set', 'outer', 'inner']], dict_path, dict_file, mode='a')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('Wrote %s/%s'%(dict_path, dict_file))


def create_enc_dicts(dict_path, db_con):
    enc_sigs = ['ADMISSION', 'VISIT', 'Reason', 'TRANSFERS']
    dict_file = 'dict.encouters'
    dc_start = 30000
    query1 = 'SELECT DISTINCT(ENC_TYPE) as val FROM [flu].[ENCOUNTERS]'
    query2 = 'SELECT DISTINCT(ENC_RSN) as val FROM [flu].[ENCOUNTERS]'
    query3 = 'SELECT DISTINCT(ENC_RSN) as val FROM [flu].[ENC_RSN_ADDITIONAL]'
    query4 = 'SELECT DISTINCT(CASE WHEN ENC_PROV_SPEC IS null THEN ENC_DEP_SPEC ELSE ENC_PROV_SPEC END) as val FROM [flu].[ENCOUNTERS]'
    query5 = "SELECT DISTINCT(DEP_NM) as val FROM [flu].[HOSPITAL_ADT] WHERE ADT_TYPE  in ('ADMISSION', 'TRANSFER IN', 'TRANSFER OUT', 'DISCHARGE')"
    all_res = pd.DataFrame()
    for query in [query1, query2, query3, query4, query5]:
        df = pd.read_sql(query, db_con)
        df['code'] = replace_spaces(df['val'])
        all_res = all_res.append(df, sort=False)
    all_res = all_res.append([{'code':'SPEC:UNKNOWN'}, {'code':'RSN:UNKNOWN'}, {'code':'TYPE:UNKNOWN'}])
    all_res.drop_duplicates('code', inplace=True)
    all_res = all_res[(all_res['code'].notnull()) & (all_res['code'].str.strip() !='')]
    all_res = all_res.assign(defid=range(dc_start, dc_start + all_res.shape[0]))
    all_res['def'] = 'DEF'
    cols = ['def', 'defid', 'code']
    write_tsv(all_res[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(enc_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)


def create_vacc_dicts(dict_path, db_con):
    sig = 'Vaccination'
    dict_file = 'dict.vaccination'
    dc_start = 40000
    query = 'SELECT DISTINCT(IMM_NM) FROM [flu].[IMMUNIZATION_HISTORY]'
    vacc_dict = pd.read_sql(query, db_con)
    vacc_dict['code'] = replace_spaces(vacc_dict['IMM_NM'])
    vacc_dict = vacc_dict.assign(defid=range(dc_start, dc_start + vacc_dict.shape[0]))
    vacc_dict['def'] = 'DEF'
    cols = ['def', 'defid', 'code']
    write_tsv(vacc_dict[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)


def create_drug_dicts(dict_path, db_con):
    sigs = 'Drug'#,Drug_detailed'
    dict_file = 'dict.drugs'
    dc_start = 500000
    query_dose = "SELECT DISTINCT MED_STRENGTH as code FROM flu.MEDICATION_ORDERS WHERE MED_ORD_SETTING = 'OUTPATIENT' AND MED_STRENGTH IS NOT NULL"
    dose_df = pd.read_sql(query_dose, db_con)
    dose_df['code'] = replace_spaces(dose_df['code'])
    dose_df = dose_df.append({'code':'DOSE:UNKNOWN'}, ignore_index=True)
    query_form = "SELECT DISTINCT MED_FORM as code FROM flu.MEDICATION_ORDERS WHERE MED_ORD_SETTING = 'OUTPATIENT' AND MED_FORM IS NOT NULL"
    form_df = pd.read_sql(query_form, db_con)
    form_df['code'] = replace_spaces(form_df['code'])
    form_df = form_df.append({'code': 'FORM:UNKNOWN'}, ignore_index=True)
    
    drug_dict1 = dose_df.append(form_df)
    drug_dict1.drop_duplicates(inplace=True)
    drug_dict1 = drug_dict1.assign(defid=range(dc_start, dc_start + drug_dict1.shape[0]))
    drug_dict1['def'] = 'DEF'
    dc_start = drug_dict1['defid'].max() + 10
    write_tsv(drug_dict1[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    
    query = "SELECT DISTINCT MED_ID, MED_NM FROM flu.MEDICATION_ORDERS WHERE MED_ORD_SETTING = 'OUTPATIENT'"
    drug_df = pd.read_sql(query, db_con)
    drug_df.drop_duplicates('MED_ID', inplace=True)
    drug_df['MED_NM'] = drug_df['MED_ID'] +':' + replace_spaces(drug_df['MED_NM'])
    drug_dict = code_desc_to_dict_df(drug_df, dc_start, ['MED_ID', 'MED_NM'])
    write_tsv(drug_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='a')
    first_line = 'SECTION\t' + sigs + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)
    
    
    rx_query = "SELECT DISTINCT RXN_CD, RXN_NM FROM [flu].[MEDID_RXNCD] WHERE RXN_CD is not null and RXN_NM is not null"
    rx_df = pd.read_sql(rx_query, db_con)
    
    dc_start = 600000
    dict_file = 'dict.rx_defs'
    rx_def_df = rx_df[['RXN_CD', 'RXN_NM']].drop_duplicates()
    rx_def_df['RXN_CD'] = 'RX_CODE:' + rx_def_df['RXN_CD'].astype(str)
    rx_def_df['RXN_NM'] = replace_spaces(rx_def_df['RXN_NM'])
    rx_def_df = code_desc_to_dict_df(rx_def_df, dc_start, ['RXN_CD', 'RXN_NM'])
    write_tsv(rx_def_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)


    set_query = "SELECT DISTINCT MED_ID, RXN_CD FROM [flu].[MEDID_RXNCD] WHERE RXN_CD is not null and RXN_NM is not null and MED_ID IN (SELECT DISTINCT(MED_ID) FROM [flu].[MEDICATION_ORDERS] WHERE MED_ORD_SETTING = 'OUTPATIENT')"
    rx_df = pd.read_sql(set_query, db_con)

    dict_file = 'dict.rx_set'
    set_df = rx_df[['RXN_CD', 'MED_ID']].drop_duplicates()
    set_df['RXN_CD'] = 'RX_CODE:' + set_df['RXN_CD'].astype(str)
    set_df['set'] = 'SET'
    write_tsv(set_df[['set', 'RXN_CD', 'MED_ID']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)
    

def copy_drug_dicts(onto_path, dict_path):
    sig = 'Drug'#,Drug_detailed'
    first_line = 'SECTION\t' + sig + '\n'
    drug_dict_files = [os.path.join(onto_path, 'ATC', 'dicts', 'dict.atc_defs'),
                       os.path.join(onto_path, 'ATC', 'dicts', 'dict.atc_sets')]
    for dict_file in drug_dict_files:
        copy(dict_file, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(dict_file)))


def create_flu_lab_dict(dict_path, db_con):
    sig = 'Flu_lab'
    dict_file = 'dict.flu_lab'
    dc_start = 500
    query = get_flu_pcr_query(distinct=True)
    #query = "SELECT DISTINCT(LAB_RES_VAL_TXT) as value FROM flu.LAB_RESULTS WHERE LAB_COMP_CD in ('9188','9187','8553','8552','8550','8549','10856','10857','9209','9207','211708','211709','100603','100604','11000717','9208','9230','9228')"
    dict_df = pd.read_sql(query, db_con)
    print(dict_df.head(5))
    dict_df['value'] = dict_df['value'].str.replace('"', '').str.replace('&', '_AND_').str.replace('/', '_OR_')
    print(dict_df.head(5))
    dict_df['value'] = replace_spaces(dict_df['value'].str.strip().str.upper())
    print(dict_df.head(5))
    sets = pd.DataFrame(data=['FLU_LAB_RESULT:NEGATIVE', 'FLU_LAB_RESULT:POSITIVE', 'FLU_LAB_RESULT:UNKNOWN'], columns=['value'])
    dict_df = dict_df.append(sets, ignore_index=True)
    dict_df.drop_duplicates(inplace=True)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'value']
    print(dict_df.head(5))
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    
    # ADD set to negative positive using Alon's list
    flu_set_file = '/opt/medial_sign/LOADING_PROCESS/geisinger_load/flu_lab.map_codes'
    set_df = pd.read_csv(flu_set_file, sep='\t')
    set_df['Val'] = set_df['Val'].str.replace('"', '').str.replace('&', '_AND_').str.replace('/', '_OR_')
    set_df['Val'] = replace_spaces(set_df['Val'].str.strip().str.upper())
    set_df['MAP'] = set_df['MAP'].str.replace('::', ':')
    set_df.drop_duplicates(inplace=True)
    set_df = set_df[set_df['Val'].isin(dict_df['value'])]
    set_df['set'] = 'SET'
    write_tsv(set_df[['set', 'MAP', 'Val']], dict_path, dict_file, mode='a')
    print('DONE ' + dict_file)


def create_cat_labs_dict(code_folder, dict_path, db_con):
    lab_sigs = ['Urine_Bacteria', 'Urine_Blood', 'Urine_Glucose', 'Urine_Ketone', 'Urine_Leukocyte_Esterase', 'Urine_Nitrite', 'Urine_Total_Protein',
                'Urine_Urobilinogen', 'Urine_WBC', 'Vancomycin', 'Tobramycin', 'Microcytosis', 'Ethanol', 'Urine_Bilirubin', 'Urine_RBC']
    dict_file = 'dict.cat_labs'
    dc_start = 100000
    map_df = get_map(code_folder, 'category', 'LAB_RESULTS')
    codes_list = [str(x) for x in map_df[map_df['signal'].isin(lab_sigs)]['code'].values]
    query = "SELECT DISTINCT(LAB_RES_VAL_TXT) FROM flu.LAB_RESULTS WHERE LAB_COMP_CD in ('" + "','".join(codes_list) + "')"
    dict_df = pd.read_sql(query, db_con)
    dict_df['value'] = replace_spaces(dict_df['LAB_RES_VAL_TXT'].str.strip().str.upper())
    dict_df = dict_df[(dict_df['value'].str.strip() != '') & (dict_df['value'].notnull())]
    dict_df.drop_duplicates('value', inplace=True)
    dict_df = dict_df.append({'value': 'EMPTY_FIELD'}, ignore_index=True)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'value']
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(lab_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)

def copy_bill_dicts(onto_path, dict_path):
    sig = 'BILLING_CODE'
    first_line = 'SECTION\t' + sig + '\n'
    diag_dict_files = [os.path.join(onto_path, 'ICD9', 'dicts', 'dict.icd9sg'),
                       os.path.join(onto_path, 'ICD9', 'dicts', 'dict.set_icd9sg'),
                       os.path.join(onto_path, 'ICD10', 'dicts', 'dict.icd10pcs'),
                       os.path.join(onto_path, 'ICD10', 'dicts', 'dict.set_icd10pcs'),
                       os.path.join(onto_path, 'CPT', 'dicts', 'dict.cpt'),
                       os.path.join(onto_path, 'HCPCS', 'dicts', 'dict.hcpcs_2011')]
    for dict_file in diag_dict_files:
        copy(dict_file, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(dict_file)))


def creat_bill_dict(work_folder, dict_path, db_con):
    cfg = Configuration()
    def_dicts = [ 'dict.icd9sg', 'dict.icd10pcs', 'dict.cpt', 'dict.hcpcs_2011']
    set_dicts= [ 'dict.set_icd9sg', 'dict.set_icd10pcs' ]
    signal= 'BILLING_CODE'
    data_files_prefix = signal
    header = ['pid', 'signal', 'date', 'code_billing']
    to_use_list = [ 'code_billing' ]
    create_dict_generic(cfg, def_dicts, set_dicts, signal, data_files_prefix, header, to_use_list)
    return 
    sig = 'BILLING_CODE'
    dict_file = 'dict.billing'
    dc_start = 100
    query = "SELECT DISTINCT PX_CD  FROM flu.BILLING_PROCEDURES  WHERE PX_CD_TYPE  = 'GHS'"
    dict_df = pd.read_sql(query, db_con)
    dict_df['value'] = 'GHS:' + dict_df['PX_CD'].str.strip()
    dict_df.drop_duplicates(inplace=True)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'value']
    # Add manual (freqant) codes
    max_def = dict_df['defid'].max() + 10
    manual_list = [{'def': 'DEF', 'defid':max_def+1, 'value': 'CPT_CODE:90686'}, {'def': 'DEF', 'defid':max_def+1, 'value': 'Influenza virus vaccine, quadrivalent'},
                   {'def': 'DEF', 'defid':max_def+2, 'value': 'HCPCS_CODE:G0001'}, {'def': 'DEF', 'defid':max_def+2, 'value': 'G0001:ROUTINE VENIPUNCTURE FOR COLLECTION OF SPECIMEN(S)'},
                   {'def': 'DEF', 'defid':max_def+3, 'value': 'CPT_CODE:93793'}, {'def': 'DEF', 'defid':max_def+3, 'value': 'Home and Outpatient International Normalized Ratio (INR) Monitoring Services'},
                   {'def': 'DEF', 'defid':max_def+4, 'value': 'CPT_CODE:87633'}, {'def': 'DEF', 'defid':max_def+4, 'value': 'Infectious agent detection by nucleic acid (DNA or RNA)'},
                   {'def': 'DEF', 'defid':max_def+4, 'value': 'CPT_CODE:71045'}, {'def': 'DEF', 'defid':max_def+4, 'value': 'Radiologic examination, chest'}
                   ]
                   
    man_df = pd.DataFrame(data=manual_list)
    man_df['value'] = replace_spaces(man_df['value'])
    dict_df = dict_df.append(man_df, ignore_index=True, sort=False)
    
    # Add from missing list
    max_def = dict_df['defid'].max() + 10
    miss_df = pd.read_csv(os.path.join(work_folder, 'missing_codes_for_billing.txt'), usecols=[0], names=['value'])
    miss_df = miss_df.assign(defid=range(max_def, max_def + miss_df.shape[0]))
    miss_df['def'] = 'DEF'
    dict_df = dict_df.append(miss_df, ignore_index=True, sort=False)
    dict_df.drop_duplicates('value', inplace=True)
    write_tsv(dict_df[cols], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)


def create_procedures_dict(dict_path, db_con):
    sig = 'PROCEDURES'
    dict_file = 'dict.procedures'
    dc_start = 10000
    
    query1 = "SELECT DISTINCT PX_ORD_CD as code ,PX_ORD_NM as desc1, 'PX' as source FROM flu.PROCEDURE_ORDERS"
    query2 = "SELECT DISTINCT OR_PROC_ID as code, OR_PROC_NM as desc1, 'SURGERY' as source FROM flu.SURGERY"
    all_diag = pd.DataFrame()
    for query in [query1, query2]:
        df = pd.read_sql(query, db_con)
        df['desc1'] = df['code'] + ':' + replace_spaces(df['desc1'].str.upper())
        df['code'] = df['source'] + ':' + replace_spaces(df['code'].str.replace('.', ''))
        all_diag = all_diag.append(df, sort=False)
    all_diag.drop_duplicates('code', inplace=True)
    diag_dict = code_desc_to_dict_df(all_diag, dc_start, ['code', 'desc1'])
    write_tsv(diag_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE ' + dict_file)

def create_tumor_dict(work_folder, dict_path, db_con):
    sig = 'TUMORS,LUNG_CANCER_STAGE'
    dict_file = 'dict.tumors'
    dc_start = 4000
    sql_query = "SELECT PT_ID, INIT_DX_DT, ICDO_SITE_CD,ICDO_SITE_NM, LATERALITY, ICDO_HISTOLOGY_CD, ICDO_HISTOLOGY_NM, ICDO_MORPHOLOGY_NM,TUMOR_SIZE, SEER_SUMMARY, AJCC_STG FROM flu.TUMOR_DX"
    tum_df = pd.read_sql(sql_query, db_con)
    site_df = tum_df[['ICDO_SITE_CD','ICDO_SITE_NM']].drop_duplicates()
    site_df['desc'] = 'ICDO_DESC:' + site_df['ICDO_SITE_CD'] + ':' + replace_spaces(site_df['ICDO_SITE_NM'].str.upper())
    site_df['code'] = 'ICDO_CODE:' + site_df['ICDO_SITE_CD']
    
 
    hist_df = tum_df[['ICDO_HISTOLOGY_CD','ICDO_HISTOLOGY_NM']].drop_duplicates()
    hist_df['desc'] = 'ICDO_DESC:' + hist_df['ICDO_HISTOLOGY_CD'] + ':' +  replace_spaces(hist_df['ICDO_HISTOLOGY_NM'].str.upper())
    hist_df['code'] = 'ICDO_CODE:' + hist_df['ICDO_HISTOLOGY_CD']
    
    later_df = tum_df[['LATERALITY']].drop_duplicates()
    later_df['code']= 'LATERALITY:' + replace_spaces(later_df['LATERALITY'].str.upper())
    
    morph_df = tum_df[['ICDO_MORPHOLOGY_NM']].drop_duplicates()
    morph_df['code']= 'MORPHOLOGY:' + replace_spaces(morph_df['ICDO_MORPHOLOGY_NM'].str.upper())
    
    
    stage_df = tum_df[['SEER_SUMMARY', 'AJCC_STG']].drop_duplicates()
    stage_df['SEER_SUMMARY'].fillna('NULL', inplace=True)
    stage_df['AJCC_STG'].fillna('NULL', inplace=True)
    stage_df['code'] = 'STAGE:' + replace_spaces(stage_df['SEER_SUMMARY'] + '_' + stage_df['AJCC_STG'])
    stage_df.drop_duplicates('code', inplace=True)
    
    stage_df2 = pd.read_csv(os.path.join(work_folder, 'lung_cancer_stage_map.txt'), sep='\t', keep_default_na=False, usecols=[0,1,3])
    stage_df2['SEER_SUMMARY'].fillna('NULL', inplace=True)
    stage_df2['AJCC_STG'].fillna('NULL', inplace=True)
    stage_df2['STAGE'] = stage_df2['STAGE'].astype(str).replace('-1', 'UNKNOWN')
    stage_df2['STAGE'] =  'STAGE:' + stage_df2['STAGE'].astype(str)
    stage_df2['code'] = 'STAGE:' + replace_spaces(stage_df2['SEER_SUMMARY'] + '_' + stage_df2['AJCC_STG'])
    stage_df2.drop_duplicates('code', inplace=True)
    stage_df3 = stage_df2[['STAGE']].drop_duplicates()
    stage_df3.rename(columns={'STAGE': 'code'}, inplace=True)
    
    df = pd.concat([site_df, hist_df, later_df, morph_df, stage_df, stage_df3])
    diag_dict = code_desc_to_dict_df(df, dc_start, ['code', 'desc'])
    write_tsv(diag_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    
    map_stage = stage_df2[['code', 'STAGE']].drop_duplicates()
    map_stage['set'] = 'SET'
    write_tsv(map_stage[['set', 'STAGE', 'code']], dict_path, dict_file, mode='a')
    print('DONE ' + dict_file)
    
    
if __name__ == '__main__':
    cfg = Configuration()
    dict_folder = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    db = DB()
    db_con = db.get_connect()
    
    #create_gender_dict(dict_folder)
    #create_demographic_dict(dict_folder, db_con)
    #create_diagnosis_dict(cfg.ontology_folder, dict_folder, db_con)
    #copy_diag_dicts(cfg.ontology_folder, dict_folder)
    map_dx_icd(dict_folder, db_con)
    #create_smoke_dict(dict_folder, db_con)
    #create_enc_dicts(dict_folder, db_con)
    #create_vacc_dicts(dict_folder, db_con)
    #create_drug_dicts(dict_folder, db_con)
    #copy_drug_dicts(cfg.ontology_folder, dict_folder)
    #create_flu_lab_dict(dict_folder, db_con)
   # create_cat_labs_dict(cfg.code_folder, dict_folder, db_con)
    
    #copy_bill_dicts(cfg.ontology_folder, dict_folder)
    #creat_bill_dict(cfg.work_path, dict_folder, db_con)
    #create_procedures_dict(dict_folder, db_con)
    #create_tumor_dict(cfg.work_path, dict_folder, db_con)
