from Configuration import Configuration
import os,sys
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, '/mnt/work/Infra/tools/common')
from dicts_utils import create_dict_generic

def fix_def_dict(dict_path, prefix_orig, prefix_in_data, out_dict_path, signal='DIAGNOSIS'):
    dict_header=['DEF', 'ID', 'VALUE']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    #transform prefix. for example ICD10_CODE: to ICD10:
    if prefix_orig is not None and len(prefix_orig)>0:
        dict_df.loc[ dict_df['VALUE'].str.startswith(prefix_orig) ,'VALUE']= dict_df.loc[ dict_df['VALUE'].str.startswith(prefix_orig) ,'VALUE'].apply(lambda x: prefix_in_data+x[len(prefix_orig):])

    #Add header SECTION and store file
    of_file=open(out_dict_path, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    return dict_df

def fix_set_dict(dict_path, prefix_orig, prefix_in_data, out_dict_path, signal='DIAGNOSIS', child_prefix_orig=None, child_prefix_in_data=None):
    dict_header=['SET', 'PARENT', 'CHILD']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    #transform PARENT
    if prefix_orig is not None and len(prefix_orig)>0:
        dict_df.loc[ dict_df['PARENT'].str.startswith(prefix_orig) ,'PARENT']= dict_df.loc[ dict_df['PARENT'].str.startswith(prefix_orig) ,'PARENT'].apply(lambda x: prefix_in_data+x[len(prefix_orig):])
    if child_prefix_orig is None:
        child_prefix_orig=prefix_orig
    if child_prefix_in_data is None:
        child_prefix_in_data=prefix_in_data
    if child_prefix_orig is not None and len(child_prefix_orig)>0:
        dict_df.loc[ dict_df['CHILD'].str.startswith(child_prefix_orig) ,'CHILD']= dict_df.loc[ dict_df['CHILD'].str.startswith(child_prefix_orig) ,'CHILD'].apply(lambda x: child_prefix_in_data+x[len(child_prefix_orig):])
    
    of_file=open(out_dict_path, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    return dict_df

def create_diagnosis_dict(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(os.path.join(cfg.work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(cfg.work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    existing_dict_folder=cfg.dict_folder
    #ICD10:
    icd10_dict=fix_def_dict(os.path.join(existing_dict_folder, 'dict.icd10'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.icd10'), 'DIAGNOSIS')
    #ICD9:
    icd9_dict=fix_def_dict(os.path.join(existing_dict_folder, 'dict.icd9dx'), 'ICD9_CODE:', 'ICD9:', os.path.join(out_dict, 'dict.icd9dx'), 'DIAGNOSIS')
    
    #Handle sets:
    fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd10'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.set_icd10'), 'DIAGNOSIS')
    fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd9dx'), 'ICD9_CODE:', 'ICD9:', os.path.join(out_dict, 'dict.set_icd9dx'), 'DIAGNOSIS')
    fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd10_2_icd9'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.set_icd10_2_icd9'), 'DIAGNOSIS',  'ICD9_CODE:', 'ICD9:')

    #aggregate existing codes
    existing_cd=icd10_dict[['VALUE']].copy().drop_duplicates().reset_index(drop=True)
    existing_cd=existing_cd.append(icd9_dict[['VALUE']].copy().drop_duplicates().reset_index(drop=True), ignore_index=True)
    existing_cd.rename(columns={'VALUE':'diagnosis'}, inplace=True)
    
    header=['pid', 'signal', 'date', 'diagnosis', 'source']
    diag_files=sorted(list(filter(lambda x: x.startswith('DIAGNOSIS'), os.listdir(final_sig_folder))), key = lambda x: int(x.split('.')[1]))
    all_codes=None
    for file_name in diag_files:
        print('Reading %s'%(file_name),flush=True)
        df=pd.read_csv(os.path.join(final_sig_folder, file_name), sep='\t', names=header, usecols=['diagnosis']).drop_duplicates().reset_index(drop=True)
        if all_codes is None:
            all_codes = df
        else:
            all_codes=all_codes.append(df, ignore_index=True).drop_duplicates().reset_index(drop=True)

    #create dict - validate it appeasrs in "existing_cd". if not, add missing codes
    max_code=max(icd9_dict['ID'].max(), icd10_dict['ID'].max())

    missing_codes=all_codes[~all_codes['diagnosis'].isin(existing_cd['diagnosis'])].copy()
    missing_codes['def']='DEF'
    missing_codes['code']=np.asarray(range(len(missing_codes)))+10000+max_code
    missing_codes=missing_codes[['def', 'code', 'diagnosis']]
    print('Have %d diagnosis codes, out of therm %d is missing (%2.4f%%)'%(len(all_codes), len(missing_codes), float(100.0*len(missing_codes))/len(all_codes) ), flush=True)
    if len(missing_codes) > 0:
        of_file=open(os.path.join(out_dict, 'dict.def_DIAGNOSIS'), 'w')
        of_file.write('SECTION\t%s\n'%('DIAGNOSIS'))
        missing_codes.to_csv(of_file, sep='\t', index=False, header=False)
        of_file.close()
    #create source with "DIAGNOSIS", "MEDICAL_HISTORY", "PROBLEM_LIST":
    source_df=pd.DataFrame(columns={'def': ['DEF', 'DEF', 'DEF'], 'code': [1,2,3], 'source':['DIAGNOSIS', 'MEDICAL_HISTORY', 'PROBLEM_LIST']})
    source_df['code']=source_df['code'] + max( missing_codes['code'].max(), max_code )+10000
    of_file=open(os.path.join(out_dict, 'dict.def_DIAGNOSIS_source'), 'w')
    of_file.write('SECTION\t%s\n'%('DIAGNOSIS'))
    source_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()



def create_demo_dict(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(os.path.join(cfg.work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(cfg.work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    df=pd.DataFrame( {'code': [1,1,2,2], 'value': ['Male','1', 'Female', '2']})
    df['def']='DEF'
    df=df[['def', 'code', 'value']]
    of_file=open(os.path.join(out_dict, 'dict.demo'), 'w')
    of_file.write('SECTION\t%s\n'%('GENDER'))
    df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()


def create_admission_dict(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(os.path.join(cfg.work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(cfg.work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    header=['pid', 'signal', 'start_date', 'end_date', 'admission_source']
    adm_files=sorted(list(filter(lambda x: x.startswith('ADMISSION.'), os.listdir(final_sig_folder))), key = lambda x: int(x.split('.')[1]))
    all_codes=None
    for file_name in adm_files:
        print('Reading %s'%(file_name),flush=True)
        df=pd.read_csv(os.path.join(final_sig_folder, file_name), sep='\t', names=header, usecols=['admission_source']).drop_duplicates().reset_index(drop=True)
        if all_codes is None:
            all_codes = df
        else:
            all_codes=all_codes.append(df, ignore_index=True).drop_duplicates().reset_index(drop=True)

    all_codes['def']='DEF'
    all_codes['code']=np.asarray(range(len(all_codes)))+10000
    all_codes=all_codes[['def', 'code', 'admission_source']]
    print('Have %d Admission codes'%(len(all_codes)), flush=True)
    of_file=open(os.path.join(out_dict, 'dict.def_ADMISSION'), 'w')
    of_file.write('SECTION\t%s\n'%('ADMISSION'))
    all_codes.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()

def create_encounters_dict(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(os.path.join(cfg.work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(cfg.work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    header=['pid', 'signal', 'date', 'encounter_type']
    adm_files=sorted(list(filter(lambda x: x.startswith('ENCOUNTER.'), os.listdir(final_sig_folder))), key = lambda x: int(x.split('.')[1]))
    all_codes=None
    for file_name in adm_files:
        print('Reading %s'%(file_name),flush=True)
        df=pd.read_csv(os.path.join(final_sig_folder, file_name), sep='\t', names=header, usecols=['encounter_type']).drop_duplicates().reset_index(drop=True)
        if all_codes is None:
            all_codes = df
        else:
            all_codes=all_codes.append(df, ignore_index=True).drop_duplicates().reset_index(drop=True)

    all_codes['def']='DEF'
    all_codes['code']=np.asarray(range(len(all_codes)))+10000
    all_codes=all_codes[['def', 'code', 'encounter_type']]
    print('Have %d Admission codes'%(len(all_codes)), flush=True)
    of_file=open(os.path.join(out_dict, 'dict.def_ENCOUNTER'), 'w')
    of_file.write('SECTION\t%s\n'%('ENCOUNTER'))
    all_codes.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()


def create_procedure_dict(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(os.path.join(cfg.work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(cfg.work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    header=['pid', 'signal', 'date', 'procedure_code', 'procedure_status']
    proc_files= sorted(list(filter(lambda x: x.startswith('PROCEDURES.'), os.listdir(final_sig_folder))), key = lambda x: int(x.split('.')[1]))

    existing_dict_folder=cfg.dict_folder
    #ICD10:
    icd10_dict=fix_def_dict(os.path.join(existing_dict_folder, 'dict.icd10pcs'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.icd10pcs'), 'PROCEDURE,PROCEDURE_PRIMARY')
    #ICD9:
    icd9_dict=fix_def_dict(os.path.join(existing_dict_folder, 'dict.icd9sg'), 'ICD9_CODE:', 'ICD9:', os.path.join(out_dict, 'dict.icd9sg'), 'PROCEDURE,PROCEDURE_PRIMARY')
    #CPT
    cpt_dict=fix_def_dict(os.path.join(existing_dict_folder, 'dict.cpt'), 'CPT_CODE:', 'CPT_CODE:', os.path.join(out_dict, 'dict.cpt'), 'PROCEDURE,PROCEDURE_PRIMARY')

    #Handle sets:
    fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd10pcs'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.set_icd10pcs'), 'PROCEDURE,PROCEDURE_PRIMARY')
    fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd9sg'), 'ICD9_CODE:', 'ICD9:', os.path.join(out_dict, 'dict.set_icd9sg'), 'PROCEDURE,PROCEDURE_PRIMARY')
    #fix_set_dict(os.path.join(existing_dict_folder, 'dict.set_icd10_2_icd9'), 'ICD10_CODE:', 'ICD10:', os.path.join(out_dict, 'dict.set_icd10_2_icd9'), 'DIAGNOSIS',  'ICD9_CODE:', 'ICD9:')

    #aggregate existing codes
    existing_cd=icd10_dict[['VALUE']].copy().drop_duplicates().reset_index(drop=True)
    existing_cd=existing_cd.append(icd9_dict[['VALUE']].copy().drop_duplicates().reset_index(drop=True), ignore_index=True)
    existing_cd=existing_cd.append(cpt_dict[['VALUE']].copy().drop_duplicates().reset_index(drop=True), ignore_index=True)
    existing_cd.rename(columns={'VALUE':'procedure_code'}, inplace=True)

    all_codes=None
    all_status=None
    for file_name in proc_files:
        print('Reading %s'%(file_name),flush=True)
        df=pd.read_csv(os.path.join(final_sig_folder, file_name), sep='\t', names=header, usecols=['procedure_code', 'procedure_status']).drop_duplicates().reset_index(drop=True)
        if all_codes is None:
            all_codes = df[['procedure_code']].drop_duplicates().reset_index(drop=True)
            all_status = df[['procedure_status']].drop_duplicates().reset_index(drop=True)
        else:
            all_codes=all_codes.append(df[['procedure_code']].drop_duplicates().reset_index(drop=True), ignore_index=True).drop_duplicates().reset_index(drop=True)
            all_status=all_status.append(df[['procedure_status']].drop_duplicates().reset_index(drop=True), ignore_index=True).drop_duplicates().reset_index(drop=True)

    #create dict - validate it appeasrs in "existing_cd". if not, add missing codes
    max_code=max(icd9_dict['ID'].max(), icd10_dict['ID'].max(), cpt_dict['ID'].max())

    missing_codes=all_codes[~all_codes['procedure_code'].isin(existing_cd['procedure_code'])].copy()
    missing_codes['def']='DEF'
    missing_codes['code']=np.asarray(range(len(missing_codes)))+10000+max_code
    missing_codes=missing_codes[['def', 'code', 'procedure_code']]
    print('Have %d procedure codes, out of them %d is missing (%2.4f%%)'%(len(all_codes), len(missing_codes), float(100.0*len(missing_codes))/len(all_codes) ), flush=True)
    if len(missing_codes) > 0:
        of_file=open(os.path.join(out_dict, 'dict.def_PROCEDURE'), 'w')
        of_file.write('SECTION\t%s\n'%('PROCEDURE,PROCEDURE_PRIMARY'))
        missing_codes.to_csv(of_file, sep='\t', index=False, header=False)
        of_file.close()
    #create source with "DIAGNOSIS", "MEDICAL_HISTORY", "PROBLEM_LIST":
    all_status=all_status.sort_values('procedure_status').reset_index(drop=True)
    all_status['def']='DEF'
    max_code=max( missing_codes['code'].max(), max_code )
    all_status['code']=np.asarray(range(len(all_status)))+10000+max_code
    all_status=all_status[['def', 'code', 'procedure_status']]
 
    of_file=open(os.path.join(out_dict, 'dict.def_PROCEDURE_status'), 'w')
    of_file.write('SECTION\t%s\n'%('PROCEDURE,PROCEDURE_PRIMARY'))
    all_status.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()


def create_drugs_dict(cfg):
    def_dicts=['dict.defs_rx', 'dict.atc_defs']
    set_dicts=['dict.atc_sets', 'dict.set_atc_rx']
    header=['pid', 'signal', 'start_date', 'end_date', 'rx_cui', 'std_ordering_mode', 'std_order_status', 'std_quantity']
    to_use_list=['rx_cui', 'std_ordering_mode', 'std_order_status']
    create_dict_generic(cfg, def_dicts, set_dicts, 'Drug', 'Drug', header, to_use_list)

def create_dicts_for_lab_categ(cfg):
    def_dicts=[]
    set_dicts=[]
    categ_df=pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'categorical_signals.list'), names=['signal']).drop_duplicates().reset_index(drop=True)
    header=['pid', 'signal', 'date', 'val_txt']
    to_use_list=['val_txt']
    for signal in list(categ_df.signal):
        sig_name='%s.Categorical'%(signal)
        print('Processing %s'%(sig_name))
        create_dict_generic(cfg, def_dicts, set_dicts, sig_name, sig_name, header, to_use_list)


if __name__ == '__main__':
    cfg=Configuration()
    #create_admission_dict(cfg)
    #create_diagnosis_dict(cfg)
    #create_demo_dict(cfg)
    #create_encounters_dict(cfg)
    #create_procedure_dict(cfg)
    #create_drugs_dict(cfg)
    create_dicts_for_lab_categ(cfg)
