import pandas as pd
import os
import sys
import time
MR_ROOT = '/opt/medial/tools/bin/RepoLoadUtils'
sys.path.append(os.path.join(MR_ROOT, 'common'))
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces
from staging_config import MaccabiLabs, MaccabiDemographic, StageConfig
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files
from sql_utils import get_sql_engine
from unit_converts import round_ser


def maccabi_labs_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    maccabi_def = MaccabiLabs()

    macabi_map = pd.read_csv(os.path.join(code_folder, 'maccabi_signal_map.csv'), sep='\t')
    #lab_chart_cond = ((macabi_map['source'] == 'measurements') & (macabi_map['signal'] == 'SaO2'))
    lab_chart_cond = ((macabi_map['source'] == 'laboratory') | (macabi_map['source'] == 'measurements'))
    macabbi_map_numeric = macabi_map[(macabi_map['type'] == 'numeric') & lab_chart_cond]
    print(macabbi_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder, names=['signal', 'unit', 'mult', 'add'], header=0)
    id2nr = get_id2nr_map(work_folder)
    if os.path.exists(os.path.join(code_folder, 'mixture_units_cfg.txt')):
        special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    else:
        special_factors_signals = None
    numeric_to_files(maccabi_def, macabbi_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder)    

def maccabi_category_labs_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    maccabi_def = MaccabiLabs()
    
    macabi_map = pd.read_csv(os.path.join(code_folder, 'maccabi_signal_map.csv'), sep='\t')    
    lab_chart_cond = ((macabi_map['source'] == 'laboratory') & (macabi_map['type'] == 'category'))
    #lab_chart_cond = ((macabi_map['source'] == 'laboratory') & (macabi_map['type'] == 'category') & (macabi_map['signal'] == 'Urine_Leucocytes'))
    macabbi_map_cat = macabi_map[lab_chart_cond]
    print(macabbi_map_cat)
    id2nr = get_id2nr_map(work_folder)
    categories_to_files(maccabi_def, macabbi_map_cat, id2nr, out_folder)
    
    
def maccabi_demographic_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    maccabi_def = MaccabiDemographic()
    id2nr = get_id2nr_map(work_folder)
    macabi_map = pd.read_csv(os.path.join(code_folder, 'maccabi_signal_map.csv'), sep='\t')
    demo_cond = (macabi_map['source'] == 'demographics')
    maccabi_map_demo = macabi_map[demo_cond]
    demographic_to_files(maccabi_def, maccabi_map_demo, id2nr, out_folder)


def maccabi_hospitalizations_to_files():
    print('going to crate file for signals from  hospitalizations_data')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    '''
    hospitalization_path = os.path.join(raw_path, 'hospitalizations_data')
    hosp_file_list = os.listdir(hospitalization_path)
    '''
    hospitalization_path = os.path.join(raw_path, 'FLU_DATA_29_07_2020')
    hosp_file_list = os.listdir(hospitalization_path)
    hosp_file_list = [x for x in hosp_file_list if x.startswith('Medial_Flu_hospitlization')]
    print(hosp_file_list)
    hospitalization_df = pd.DataFrame()
    for fl in hosp_file_list:
        fl_df = pd.read_csv(os.path.join(hospitalization_path, fl), sep='\t', encoding='cp1255')        
        fl_df = fl_df[fl_df['CARE_GIVER_DPRT_TYPE_CD'].notnull()]
        fl_df['medialid'] = fl_df['random_id'].astype(str).map(id2nr)
        fl_df['code'] = fl_df['CARE_GIVER_DPRT_TYPE_CD'].astype(int).astype(str) + '_' + fl_df['CARE_GIVER_DPRT_CD'].astype(int).astype(str)
        hospitalization_df = hospitalization_df.append(fl_df)
    
    sig = 'ADMISSION'
    admissions_df = hospitalization_df[hospitalization_df['ISHPUZ_ENTRANCE_DATE'] == hospitalization_df['DPRT_ENTRANCE_DATE']].copy()
    admissions_df['signal'] = sig
    admissions_df.sort_values(by=['medialid', 'ISHPUZ_ENTRANCE_DATE'], inplace=True)
    cols = ['medialid', 'signal', 'ISHPUZ_ENTRANCE_DATE', 'ISHPUZ_RELEASE_DATE', 'code']
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(admissions_df[cols], out_folder, sig)
    print('DONE with ADMISSION')
    sig = 'STAY'
    hospitalization_df['signal'] = sig
    hospitalization_df.sort_values(by=['medialid', 'DPRT_ENTRANCE_DATE'], inplace=True)
    cols = ['medialid', 'signal', 'DPRT_ENTRANCE_DATE', 'DPRT_RELEASE_DATE', 'code']    
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(hospitalization_df[cols], out_folder, sig)
    print('DONE with STAY')


def cancer_registry_to_file():
    sig = 'Cancer_registry'
    print('going to crate file for signals from  Medial_Flu_cancer_registry_0420.txt')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    cr_df = pd.read_csv(os.path.join(raw_path, 'Medial_Flu_cancer_registry_0420.txt'), sep='\t')
    id2nr = get_id2nr_map(work_folder)
    cr_df['medialid'] = cr_df['random_id'].astype(str).map(id2nr)
    cr_df['code'] = cr_df['DISEAS_GROUPUP_CD'].astype(int)*10 + cr_df['DISEASE_GROUP_CODE'].astype(int) + cr_df['DISEASE_CODE'].astype(int)
    cr_df['date'] = cr_df['REGISTRY_DATE'].str.replace('-', '').str[0:8]
    cr_df['signal'] = sig
    cr_df.sort_values(by=['medialid', 'date'], inplace=True)
    cols = ['medialid', 'signal', 'date', 'code']    
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(cr_df[cols], out_folder, sig)
    print('DONE with '+ sig)
    
def prescription_to_file():
    sig = 'Drug'
    sig_pres = 'Drug_prescription'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    in_folder = os.path.join(raw_path, 'Prescription_data')
    id2nr = get_id2nr_map(work_folder)
    print(in_folder)
    file_list = os.listdir(in_folder)
    cols = ['medialid', 'signal', 'DATE_Prescription', 'ATC_CD', 'NUMBER_OF_DAYS', 'source'] 
    cols_pres = ['medialid', 'signal', 'DATE_Prescription', 'DATE_VISIT', 'purchase_date','ATC_CD', 'NUMBER_OF_DAYS', 'DOC_RANDOM_ID','source']
    file_cnt=0
    for fl in file_list:    
        all_diag = pd.DataFrame()
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(in_folder, fl)
        for mim_df in pd.read_csv(fullfile, sep='\t', chunksize=c_size, encoding='cp1255', error_bad_lines=False):
            mim_df['medialid'] = mim_df['random_id'].astype(str).map(id2nr)
            mim_df = mim_df[mim_df['medialid'].notnull()]
            mim_df['DATE_Prescription'] = pd.to_numeric(mim_df['DATE_Prescription'], errors='coerce')
            #mim_df = mim_df[mim_df['DATE_Prescription'] > 19000000]
            
            mim_df = mim_df[mim_df['DATE_Prescription'].notnull()]
            mim_df['purchase_date'] = pd.to_numeric(mim_df['purchase_date'], errors='coerce')
            print('purchase_date null values = ' + str(mim_df[mim_df['purchase_date'].isnull()].shape[0]))
            mim_df['purchase_date'].fillna(19000101, inplace=True)
            mim_df['purchase_date'] = mim_df['purchase_date'].astype(int)
            
            mim_df['DOC_RANDOM_ID'].fillna(0, inplace=True)
            mim_df['DOC_RANDOM_ID'] = mim_df['DOC_RANDOM_ID'].astype(int).astype(str)
            
            print('NUMBER_OF_DAYS  negative= ' + str(mim_df[mim_df['NUMBER_OF_DAYS'] < 0].shape[0]))
            mim_df['NUMBER_OF_DAYS'] = mim_df['NUMBER_OF_DAYS'].where(mim_df['NUMBER_OF_DAYS'] >=0, 0)
            print('NUMBER_OF_DAYS  negative= ' + str(mim_df[mim_df['NUMBER_OF_DAYS'] < 0].shape[0]))
            mim_df['ATC_CD'] = mim_df['ATC_CD'].astype(str).str.strip()
            mim_df = mim_df[mim_df['ATC_CD'].notnull()]
            
            grp = mim_df.groupby(['medialid', 'DATE_Prescription', 'DATE_VISIT', 'purchase_date', 'DOC_RANDOM_ID', 'ATC_CD'])['NUMBER_OF_DAYS'].sum()
            grp = grp.reset_index()
            grp['source'] = fl
            grp['signal'] = sig
            
            all_diag = all_diag.append(grp[cols_pres])
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records')
            cnt += 1

        print('    proccesed file ' + fl + ' in  ' + str(time.time() - time2))
        all_diag.sort_values(by=['medialid', 'DATE_Prescription'], inplace=True)
        file_cnt += 1
        all_diag['signal'] = sig
        sig_file_name =  sig+str(file_cnt)
        if os.path.exists(os.path.join(out_folder, sig_file_name)):
            os.remove(os.path.join(out_folder, sig_file_name))
        write_tsv(all_diag[cols], out_folder, sig_file_name)
        
        all_diag['signal'] = sig_pres
        sig_file_name =  sig_pres+str(file_cnt)
        if os.path.exists(os.path.join(out_folder, sig_file_name)):
            os.remove(os.path.join(out_folder, sig_file_name))
        write_tsv(all_diag[cols_pres], out_folder, sig_file_name)
        
        print('saved to file ' + sig_file_name)


def codes_to_file(signal,source_dir ,date_field, code_field, second_code_field=None):
    sig = signal
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    in_folder = os.path.join(raw_path, source_dir)
    id2nr = get_id2nr_map(work_folder)
    print(in_folder)
    file_list = os.listdir(in_folder)
    cols = ['medialid', 'signal', date_field, code_field, 'source'] 
    file_cnt=0
    for fl in file_list:    
        all_diag = pd.DataFrame()
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()
        fullfile = os.path.join(in_folder, fl)
        print('reading from: ' + fullfile) 
        sep=','
        encoding='cp1255'
        if 'hospital_diagnosis' in source_dir or 'delta0420' in fl or 'delta0720' in fl:
            sep='\t'
            if 'hospital_diagnosis' in source_dir and ('delta0420' in fl or 'delta0720' in fl):
                encoding=None
        print('Seperator ='+sep + '!!')
        for mim_df in pd.read_csv(fullfile, sep=sep, chunksize=c_size, encoding=encoding, error_bad_lines=False):
            if 'RANDOM_ID' in mim_df.columns:
                mim_df.rename(columns={'RANDOM_ID': 'random_id'}, inplace=True)
            if 'icd9_code' in mim_df.columns:
                mim_df['icd9_code'] = mim_df['icd9_code'].str.strip()
                mim_df['icd9_code'] = mim_df['icd9_code'].str.lstrip('0')
                mim_df['withdot'] = mim_df['icd9_code'].str.contains('.', regex=False)
                mim_df.loc[mim_df['withdot'] == True, 'icd9_code'] = mim_df['icd9_code'].str.rstrip('0')
                mim_df['icd9_code'] = mim_df['icd9_code'].str.strip('.')
                mim_df = mim_df[(mim_df['icd9_code'].notnull()) & (mim_df['icd9_code'] != '')]
            
            mim_df['source'] = fl
            mim_df['medialid'] = mim_df['random_id'].astype(str).map(id2nr)
            mim_df = mim_df[mim_df['medialid'].notnull()]
            mim_df[date_field] = pd.to_numeric(mim_df[date_field], errors='coerce')
            mim_df = mim_df[mim_df[date_field].notnull()]
            if 'hospital_diagnosis' in source_dir:  # Fix the cases where code is with description
                mim_df.loc[mim_df[code_field].isnull(), 'split_code'] = mim_df['DiagName'].apply(lambda x: str(x).split(' ')[-1])
                cond = (mim_df[code_field].isnull()) & (mim_df['split_code'].str[-1].str.isdigit())
                mim_df.loc[cond ,code_field] = mim_df['split_code']                
                mim_df.loc[(mim_df[code_field].isnull()), code_field] = mim_df['DiagName']
                mim_df[code_field] = replace_spaces(mim_df[code_field].str.strip())
                mim_df[code_field] = mim_df[code_field].str.strip(',')
                mim_df[code_field] = mim_df[code_field].str.replace(',','.')
                mim_df[code_field] = mim_df[code_field].str.replace('9h_','')
                cond2 = (mim_df[code_field].str[-1] == '0') & (mim_df[code_field].str[-2] != '.')
                mim_df.loc[cond2, code_field] = mim_df[cond2][code_field].str[:-1]
            mim_df[code_field] = mim_df[code_field].astype(str).str.strip()
            mim_df = mim_df[(mim_df[code_field].notnull()) & (mim_df[code_field] != '')]
            mim_df = mim_df[mim_df[date_field] > 19000000]
            mim_df['signal'] = sig
            if second_code_field:
                mim_df[code_field] = mim_df[code_field].astype(str) + '_' + mim_df[second_code_field].astype(str).str.strip()
            all_diag = all_diag.append(mim_df[cols])
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records')
            cnt += 1
        print('    proccesed file ' + fl + ' in  ' + str(time.time() - time2))
        all_diag.sort_values(by=['medialid', date_field], inplace=True)
        file_cnt += 1
        sig_file_name =  sig+str(file_cnt)
        if os.path.exists(os.path.join(out_folder, sig_file_name)):
            os.remove(os.path.join(out_folder, sig_file_name))
        write_tsv(all_diag[cols], out_folder, sig_file_name)
        print('saved to file ' + sig_file_name)

def codes_to_file_splitted(signal,source_dir , cols_dict):
    sig = signal
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    in_folder = os.path.join(raw_path, source_dir)
    id2nr = get_id2nr_map(work_folder)
    print(in_folder)
    file_list = os.listdir(in_folder)
    #file_list = ['Medial_Flu_Procedurs_data_delta0720.txt']
    cols = ['medialid', 'signal', 'date', 'code', 'source'] 
    file_cnt=0 
    for fl in file_list:    
        all_diag = pd.DataFrame()
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(in_folder, fl)       
        col_names = [cols_dict[k] for k in cols_dict.keys()]
        sep = ','
        if 'delta0420' in fl or 'delta0720' in fl:
            sep='\t'
        for mim_df in pd.read_csv(fullfile, chunksize=c_size, encoding='cp1255', error_bad_lines=False, usecols=cols_dict.keys(), names=col_names, header=0, sep=sep):
            mim_df = mim_df[(mim_df['cd1'].notnull()) & (mim_df['cd1'].str.strip() != '')]
            mim_df['num_code'] = pd.to_numeric(mim_df['cd1'].str.strip(), errors='coerce')
            mim_df['strip_code'] = mim_df['cd1']
            mim_df.loc[mim_df['num_code'].notnull(), 'strip_code'] = mim_df[mim_df['num_code'].notnull()]['num_code'].astype(int).astype(str)
            mim_df['code'] =  mim_df['strip_code'] + '_'+ mim_df['cd2'].str.strip() + '_' + mim_df['cd3'].astype(str)
            
            mim_df['source'] = fl
            mim_df['medialid'] = mim_df['pid'].astype(str).map(id2nr)
            mim_df = mim_df[mim_df['medialid'].notnull()]            
            mim_df = mim_df[mim_df['date'].astype(int) > 19000000]
            mim_df['signal'] = sig
            all_diag = all_diag.append(mim_df[cols])
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records')
            cnt += 1

        print('    proccesed file ' + fl + ' in  ' + str(time.time() - time2))
        all_diag.sort_values(by=['medialid', 'date'], inplace=True)
        file_cnt += 1
        sig_file_name =  sig+str(file_cnt)
        if os.path.exists(os.path.join(out_folder, sig_file_name)):
            os.remove(os.path.join(out_folder, sig_file_name))
        write_tsv(all_diag[cols], out_folder, sig_file_name)
        print('saved to file ' + sig_file_name)


def icd9_diagnosis_to_file():
    codes_to_file('DIAGNOSIS','diagnoses_data', 'DATE_DIAGNOSIS', 'icd9_code')  


def atc_medications_to_file():
    #codes_to_file('Drug_purchase','medications_data', 'ISSAPPDT8', 'ATC_CD') 
    codes_to_file('Drug','medications_data', 'ISSAPPDT8', 'ATC_CD')
    

    
def hospital_diag_to_file():
    codes_to_file('Hospital_diagnosis','hospital_diagnosis_data', 'ExecuteTime', 'DiagCode')
    

def vaccinations_to_file():
    codes_to_file('Vaccination','vaccinations_data', 'DATTPL8', 'CARECD', 'CHRCTCD')


def procedures_to_file():
    codes_to_file_splitted('Procedure','procedure_data', {0: 'pid', 1: 'date', 2: 'cd1', 4: 'cd2', 5: 'cd3' })
    
def hospital_diag_to_file2():
    sig = 'Hospital_diagnosis'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    in_folder = os.path.join(raw_path, 'hospital_diagnosis_data')
    id2nr = get_id2nr_map(work_folder)
    print(in_folder)
    file_list = os.listdir(in_folder)
    code_field = 'DiagCode'
    cols = ['medialid', 'signal', 'ExecuteTime', code_field, 'source'] 
    file_cnt=0
    for fl in file_list:    
        all_diag = pd.DataFrame()
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()
        fullfile = os.path.join(in_folder, fl)
        print('reading from: ' + fullfile) 
        encoding='cp1255'
        if 'delta' in fl:
            encoding = None
        mim_df = pd.read_csv(fullfile, sep='\t', encoding=encoding)
        if 'PID' in mim_df.columns:
            mim_df.rename(columns={'PID': 'random_id'}, inplace=True)     
        
        mim_df['source'] = fl
        mim_df['medialid'] = mim_df['random_id'].astype(str).map(id2nr)
        mim_df = mim_df[mim_df['medialid'].notnull()]
        mim_df['ExecuteTime'] = pd.to_datetime(mim_df['ExecuteTime'], errors='coerce')
        mim_df = mim_df[mim_df['ExecuteTime'].notnull()]
        
        mim_df['DiagName'] = mim_df['DiagName'].apply(lambda x: str(x).split('Start Date')[0].strip())
        
        mim_df.loc[mim_df[code_field].isnull(), 'split_code'] = mim_df['DiagName'].apply(lambda x: str(x).split(' ')[-1])
        cond = (mim_df[code_field].isnull()) & (mim_df['split_code'].str[-1].str.isdigit()) & (mim_df['split_code'].str.contains('.', regex=False))
        mim_df.loc[cond ,code_field] = mim_df['split_code']                
        mim_df.loc[(mim_df[code_field].isnull()), code_field] = mim_df['DiagName']
        mim_df[code_field] = replace_spaces(mim_df[code_field].str.strip())
        mim_df[code_field] = mim_df[code_field].str.strip(',')
        mim_df[code_field] = mim_df[code_field].str.replace(',','.')
        mim_df[code_field] = mim_df[code_field].str.replace('9h_','')
        cond2 = (mim_df[code_field].str[-1] == '0') & (mim_df[code_field].str[-2] != '.') & (mim_df[code_field].str.contains('.', regex=False))
        mim_df.loc[cond2, code_field] = mim_df[cond2][code_field].str[:-1]
        
        mim_df[code_field] = mim_df[code_field].astype(str).str.strip()
        mim_df = mim_df[(mim_df[code_field].notnull()) & (mim_df[code_field] != '')]
        mim_df = mim_df[mim_df['ExecuteTime'].dt.year > 1900]
        mim_df['signal'] = sig
        all_diag = mim_df[cols].copy()
        print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records')
        cnt += 1
        print('    proccesed file ' + fl + ' in  ' + str(time.time() - time2))
        all_diag.sort_values(by=['medialid', 'ExecuteTime'], inplace=True)
        file_cnt += 1
        sig_file_name =  sig+str(file_cnt)
        write_tsv(all_diag[cols], out_folder, sig_file_name, mode='w')
        print('saved to file ' + sig_file_name)

        
def bp_to_files():
    sig = 'BP'
    date_field ='Date_Medida_Refuit'
    code_field = 'Madad_Refui_CD'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    source_dirs = ['Measurements_data', 'Measurements_data_delta']
    file_list = []
    for sr_dir in source_dirs:
        in_folder = os.path.join(raw_path, sr_dir)
        print(in_folder)
        flist = os.listdir(in_folder)
        flist = [os.path.join(in_folder, fl) for fl in  flist if 'heart_rate' not in fl]
        file_list.extend(flist)
    cols = ['medialid', 'signal', date_field, 'Value2', 'Value1', 'source'] 
    file_cnt=0
    for fl in file_list:    
        all_diag = pd.DataFrame()
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + fl) 
        sep = ','
        if 'delta0420' in fl or 'delta0720' in fl:
            sep='\t'
        for mim_df in pd.read_csv(fl, chunksize=c_size, encoding='cp1255', error_bad_lines=False, sep=sep):
            bp_df = mim_df[mim_df[code_field]==10]
            bp_df['Value1'] = pd.to_numeric(bp_df['Value1'], errors='coerce')
            bp_df['Value2'] = pd.to_numeric(bp_df['Value2'], errors='coerce')
            print('Missing values = '+ str(bp_df[(bp_df['Value1'].isnull()) | (bp_df['Value2'].isnull())].shape[0]))
            bp_df = bp_df[(bp_df['Value1'].notnull()) & (bp_df['Value2'].notnull())]
            bp_df['source'] = fl
            bp_df['medialid'] = bp_df['random_id'].astype(str).map(id2nr)
            bp_df['Value1'] = round_ser(bp_df['Value1'], 0.2)
            bp_df['Value2'] = round_ser(bp_df['Value2'], 0.2)
            bp_df = bp_df[bp_df['medialid'].notnull()]
            bp_df = bp_df[bp_df[date_field] > 19000000]
            bp_df['signal'] = sig            
            all_diag = all_diag.append(bp_df[cols])
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(bp_df.shape[0]) + ' records')
            cnt += 1
        print('    proccesed file ' + fl + ' in  ' + str(time.time() - time2))
        all_diag.sort_values(by=['medialid', date_field], inplace=True)
        file_cnt += 1
        sig_file_name =  sig+str(file_cnt)
        if os.path.exists(os.path.join(out_folder, sig_file_name)):
            os.remove(os.path.join(out_folder, sig_file_name))
        write_tsv(all_diag[cols], out_folder, sig_file_name)
        print('saved to file ' + sig_file_name)

        
def diabetic_registry_to_file():
    sig = 'Diabetic_registry'
    print('going to create file for signals from  Diabetic_Registry.txt')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    dr_df = pd.read_csv(os.path.join(raw_path, 'Diabetic_Registry.txt'))
    id2nr = get_id2nr_map(work_folder)
    dr_df['medialid'] = dr_df['RANDOM_ID'].astype(str).map(id2nr)
    
    diab_df = dr_df[dr_df['STATUS_IN_DIABETIC'] != 0].copy()
    diab_df['start_date'] = diab_df['DATEFROMDAIBETIC'].str[0:10].str.replace('-', '')
    diab_df['end_date'] = diab_df['DATETODIABETIC'].str[0:10].str.replace('-', '')
    diab_df['code'] = 'Diabetic'
    
    pre_diab = dr_df[dr_df['Pre_Diabetic_Risk_CD'] != 0].copy()
    pre_diab['start_date'] = pre_diab['Pre_Diabetic_Risk_Date_From'].str[0:10].str.replace('-', '')
    pre_diab['end_date'] = pre_diab['Pre_Diabetic_Risk_Date_To'].str[0:10].str.replace('-', '')
    pre_diab['code'] = 'Pre_Diabetic'
    
    pre_diab_hr = dr_df[dr_df['Pre_Diabetic_High_Risk_CD'] != 0].copy()
    pre_diab_hr['start_date'] = pre_diab_hr['Pre_Diabetic_High_Risk_Date_From'].str[0:10].str.replace('-', '')
    pre_diab_hr['end_date'] = pre_diab_hr['Pre_Diabetic_High_Risk_Date_To'].str[0:10].str.replace('-', '')
    pre_diab_hr['code'] = 'Pre_Diabetic_High_Risk'    
    
    cols = ['medialid', 'start_date', 'end_date', 'code']
    all_reg = pd.concat([diab_df[cols], pre_diab[cols], pre_diab_hr[cols]])
    all_reg['sig'] = sig
    all_reg.sort_values(by=['medialid', 'start_date'], inplace=True)
    
    if os.path.exists(os.path.join(out_folder, sig)):
       os.remove(os.path.join(out_folder, sig))
    cols = ['medialid','sig', 'start_date', 'end_date', 'code']
    write_tsv(all_reg[cols], out_folder, sig)
    print('saved to file ' + sig)
        

def membership_to_file():
    sig = 'MEMBERSHIP'
    print('going to create file for MEMBERSHIP signal')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    mem_file = os.path.join(raw_path, 'Medial_flu_Customer_status0720.txt')
    mem_df = pd.read_csv(mem_file, sep='\t', error_bad_lines=False, warn_bad_lines=True, encoding='cp1255')
    mem_df.rename(columns={'STATUS_CODE': 'Status','INSURANCE_FROM_DATE': 'FROM_DATE', 'INSURANCE_TO_DATE': 'TO_DATE'}, inplace=True)
    id2nr = get_id2nr_map(work_folder)
    mem_df['medialid'] = mem_df['random_id'].astype(str).map(id2nr)
    mem_df = mem_df[mem_df['medialid'].notnull()]
    mem_df['medialid'] = mem_df['medialid'].astype(int)
    mem_df['TO_DATE'] = mem_df['TO_DATE'].str[0:10]
    mem_df['FROM_DATE'] = mem_df['FROM_DATE'].str[0:10]
    mem_df = mem_df[mem_df['Status'] == 1]  # ststus ==2 in active
    #last = mem_df.groupby('random_id')['TO_DATE'].max() takes a lot of time
    mem_df = mem_df.sort_values(by = ['random_id', 'TO_DATE'])
    last = mem_df.drop_duplicates(subset='random_id', keep='last')
    non_active = last[last['TO_DATE'].str[0:4] != '2999']['random_id'].values
    mem_df['active'] = 1
    mem_df.loc[mem_df['random_id'].isin(non_active), 'active'] = 0
    mem_df['sig'] = sig
    mem_df.sort_values(by = ['random_id', 'FROM_DATE'], inplace=True)
    if os.path.exists(os.path.join(out_folder, sig)):
       os.remove(os.path.join(out_folder, sig))
    cols = ['medialid','sig', 'FROM_DATE', 'TO_DATE', 'active']
    write_tsv(mem_df[cols], out_folder, sig)
    print('saved to file ' + sig)

def assessment_to_file():
    sig = 'ASSESMENT'
    print('going to create file for ASSESMENT signal')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    as_file = os.path.join(raw_path, 'Data_24_02_2020', 'assessment_data_02.2020.csv')
    as_df = pd.read_csv(as_file, sep=',', error_bad_lines=False, warn_bad_lines=True)
    id2nr = get_id2nr_map(work_folder)
    as_df['medialid'] = as_df['Customer_SEQ'].astype(str).map(id2nr)
    as_df = as_df[as_df['medialid'].notnull()]    
    as_df['medialid'] = as_df['medialid'].astype(int)
    as_df = as_df[as_df['RESULT_FIELD_CODE'] == 1]  # code 'RESULT_FIELD_CODE' ==2 is duplication 

    as_df['date'] = as_df['MEDICAL_ASSESSMENT_DATETIME'].str[0:4]+as_df['MEDICAL_ASSESSMENT_DATETIME'].str[5:7]+as_df['MEDICAL_ASSESSMENT_DATETIME'].str[8:10]
    as_df['MEDICAL_ASSESSMENT_CODE'] = 'ASSESSMENT_CODE:'+ as_df['MEDICAL_ASSESSMENT_CODE'].astype(str).str.strip()
    as_df['sig'] = sig
    as_df.sort_values(by=['medialid', 'date'], inplace=True)
    cols = ['medialid','sig', 'date', 'MEDICAL_ASSESSMENT_CODE', 'RESULT_FIELD_VALUE_NUMERIC']
    write_tsv(as_df[cols], out_folder, sig, mode='w')
    print('saved to file ' + sig)
    
    
def covid_to_files():
    sig = 'COVID19_TEST'
    print('going to create file for COVID19  signals')
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    covid_test_file = os.path.join(raw_path, 'corona4medial', 'Test_18_08.xlsx')
    covid_test_df = pd.read_excel(covid_test_file)
    
    id2nr = get_id2nr_map(work_folder)
    covid_test_df['medialid'] = covid_test_df['random_id'].astype(str).map(id2nr)
    print( 'null pids: ' + str(covid_test_df[covid_test_df['medialid'].isnull()].shape[0]))
    covid_test_df = covid_test_df[covid_test_df['medialid'].notnull()]
    print('early dates: ' + str(covid_test_df[covid_test_df['SAMPLE_EXECUTION_DATE'] < '2020-01-01'].shape[0]))
    covid_test_df = covid_test_df[covid_test_df['SAMPLE_EXECUTION_DATE'] > '1800-01-01']
    covid_test_df['medialid'] = covid_test_df['medialid'].astype(int)
    covid_test_df['date'] = pd.to_datetime(covid_test_df['SAMPLE_RESULT_DATE']).dt.date
    covid_test_df['TEST_RESULT_CD'] = 'COVID_RES:' + covid_test_df['TEST_RESULT_CD'].astype(int).astype(str)
    covid_test_df['sig'] = sig
    covid_test_df.sort_values(by=['medialid', 'date'], inplace=True)
    cols = ['medialid','sig', 'date', 'TEST_RESULT_CD']
    write_tsv(covid_test_df[cols], out_folder, sig, mode='w')
    
    sig = 'COVID19_REG'
    # take only first positive
    covid_reg = covid_test_df[covid_test_df['TEST_RESULT_CD'].str.endswith('2')]
    covid_reg.drop_duplicates('medialid', keep='first', inplace=True)
    covid_reg['val'] = 1
    covid_reg['sig'] = sig
    write_tsv(covid_reg[['medialid','sig', 'date', 'val']], out_folder, sig, mode='w')
    
    ###
    sig = 'COVID19_COMP_REG'
    stat_map = {'קל' : 1, 'בינוני':2 , 'קשה':3, 'קריטי':4, 'נפטר':5 , 'החלים': 0}
    covid_path = os.path.join(raw_path, 'corona4medial', 'done_HOSPITAL_DATA')
    names = ['RANDOM_ID','CODE_ID','CODE_NS_TYPE','CODE_NS', 'NAME_NS','DEPT_ADMIT_DATE','ADMIT_DATE',
             'NS_GROUP_CODE', 'SN_GROUP_NAME', 'DEPARTMENT', 'AGE', 'DISCHARGE_DATE',
             'PATIENT_STATUS',  'SNIF_NAME', 'SNIF_CODE', 'DISTRICT', 'ADDRESS', 'CALC_AGE', 'SOURCE']
    names2 = ['RANDOM_ID','CODE_ID','CODE_NS_TYPE','CODE_NS', 'DEPT_ADMIT_DATE','ADMIT_DATE',
             'NS_GROUP_CODE', 'SN_GROUP_NAME', 'DEPARTMENT', 'AGE', 'DISCHARGE_DATE',
             'PATIENT_STATUS',  'SNIF_NAME', 'SNIF_CODE', 'DISTRICT', 'ADDRESS','CALC_AGE', 'SOURCE']
    hosp_files = os.listdir(covid_path)
    short_hosp_files = ['2020_07_16.xlsx']
    covid_comp_df = pd.DataFrame()
    for fl in hosp_files:
        #print(fl)
        ff = os.path.join(covid_path, fl)
        if fl in short_hosp_files:
            df = pd.read_excel(ff, names=names2)
        else:
            df = pd.read_excel(ff, names=names)
        covid_comp_df = covid_comp_df.append(df, sort=False)
        #print(covid_comp_df.columns)
    dup_cols = ['RANDOM_ID','CODE_ID','CODE_NS_TYPE','CODE_NS', 'DEPT_ADMIT_DATE','ADMIT_DATE',
                'NS_GROUP_CODE', 'SN_GROUP_NAME', 'DEPARTMENT', 'AGE',
                'PATIENT_STATUS',  'SNIF_NAME', 'SNIF_CODE', 'DISTRICT', 'ADDRESS']
    #covid_comp_df.drop(columns=['CALC_AGE', 'NAME_NS'], inplace=True)
    covid_comp_df.drop_duplicates(subset=dup_cols, inplace=True)
    #covid_comp_df['DEPT_ADMIT_DATE'] = covid_comp_df['DEPT_ADMIT_DATE'].astype(int) + 19000000
    covid_comp_df['ADMIT_DATE'] = covid_comp_df['ADMIT_DATE'].astype(int) + 19000000
    #covid_comp_df['DISCHARGE_DATE'] = covid_comp_df['DISCHARGE_DATE'].astype(int) + 19000000
    covid_comp_df['stst'] = covid_comp_df['PATIENT_STATUS'].map(stat_map)
    covid_comp_df['stst'].fillna(-1, inplace=True)
    covid_comp_df['stst'] = covid_comp_df['stst'].astype(int)
    covid_comp_df.sort_values(['RANDOM_ID', 'ADMIT_DATE', 'stst'], inplace=True)
    dedup_df  = covid_comp_df.drop_duplicates('RANDOM_ID', keep='last')
    dedup_df['medialid'] = dedup_df['RANDOM_ID'].astype(str).map(id2nr)
    print( 'null pids: ' + str(dedup_df[dedup_df['medialid'].isnull()].shape[0]))
    dedup_df = dedup_df[dedup_df['medialid'].notnull()]
    dedup_df['medialid'] = dedup_df['medialid'].astype(int)
    dedup_df['sig'] = sig
    dedup_df.sort_values(by=['medialid', 'ADMIT_DATE'], inplace=True)
    cols = ['medialid','sig', 'ADMIT_DATE', 'stst']
    write_tsv(dedup_df[cols], out_folder, sig, mode='w')
    
def visits_to_files():
    sig = 'VISITS'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')  
    id2nr = get_id2nr_map(work_folder)
    
    visits_path = '/data/VisitTexts/Rearranged'
    file_names = os.listdir(visits_path)
    all_df = pd.DataFrame()
    for fl in file_names:
        print(fl)
        ff = os.path.join(visits_path, fl)
        spec = fl.split('.')[1]
        df = pd.read_csv(ff, sep='\t', encoding='cp1255', usecols=[0,2, 6], names=['random_id','ReferralDate', 'ConsultationDate'])
        df['spec'] = spec.strip()
        df['ConsultationDate'] = pd.to_datetime(df['ConsultationDate'], errors='coerce').dt.date
        df['ReferralDate'] = pd.to_datetime(df['ReferralDate'], errors='coerce').dt.date
        df['ConsultationDate'] = df['ConsultationDate'].where(df['ConsultationDate'].notnull(), df['ReferralDate'])
        all_df = all_df.append(df)
    all_df['medialid'] = all_df['random_id'].astype(str).map(id2nr)
    all_df.drop_duplicates(inplace=True)
    print( 'null pids: ' + str(all_df[all_df['medialid'].isnull()].shape[0]))
    all_df = all_df[all_df['medialid'].notnull()]
    all_df['medialid'] = all_df['medialid'].astype(int)
    all_df['sig'] = sig
    all_df.sort_values(by=['medialid', 'ConsultationDate'], inplace=True)
    cols = ['medialid','sig', 'ConsultationDate', 'spec']
    write_tsv(all_df[cols], out_folder, sig, mode='w') 
    
    
if __name__ == '__main__':
    #maccabi_labs_to_files()
    #maccabi_category_labs_to_files()
    #maccabi_demographic_to_files()
    #maccabi_hospitalizations_to_files()
    #icd9_diagnosis_to_file()
    #atc_medications_to_file()
    #prescription_to_file()
    #vaccinations_to_file()
    #cancer_registry_to_file()
    #bp_to_files()
    #diabetic_registry_to_file()
    #procedures_to_file()
    hospital_diag_to_file2()
    #membership_to_file()
    #assessment_to_file()
    #covid_to_files()
    #visits_to_files()