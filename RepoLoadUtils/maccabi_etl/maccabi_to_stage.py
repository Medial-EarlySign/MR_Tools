import os
import sys
import traceback
import pandas as pd
import time
from Configuration import Configuration
MR_ROOT = '/opt/medial/tools/bin/RepoLoadUtils/'
sys.path.append(os.path.join(MR_ROOT, 'common'))
from staging_config import MaccabiLabs, MaccabiDemographic, MaccabiLabsDelta
from utils import fixOS, is_nan
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table


columns_map = {'random_id': 'orig_pid', 'LAB_TEST_CD': 'code', 'TEST_DESC': 'description', 'LAB_RESULT': 'value',
               'RESULT_UNIT': 'unit', 'SAMPLE_DATE': 'date1'}
               
columns_map_meas1 = {'random_id': 'orig_pid', 'Madad_Refui_CD': 'code', 'Madad_Refui_desc': 'description', 'Value1': 'value',
                     'Date_Medida_Refuit': 'date1'}
columns_map_meas2 = {'random_id': 'orig_pid', 'Madad_Refui_CD': 'code', 'Madad_Refui_desc': 'description', 'Value2': 'value',
                     'Date_Medida_Refuit': 'date1'} 

columns_map_asses = {'random_id': 'orig_pid', 'MEDICAL_ASSESSMENT_CODE': 'code', 'MEDICAL_ASSESSMENT_RESULT': 'value', 'MEDICAL_ASSESSMENT_DATETIME': 'date1'}


def load_measurmants_split(maccabi_def, type_dir):
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)  
    print(type_dir)
    file_list = os.listdir(type_dir)
    for fl in file_list:
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(type_dir, fl)       
        for mim_df in pd.read_csv(fullfile, chunksize=c_size, encoding='cp1255', error_bad_lines=False):
            mim_df = mim_df[(mim_df['Madad_Refui_CD'] == 10) | (mim_df['Madad_Refui_CD'] == 40)]
            mim_df2 = mim_df[mim_df['Value2'] != 0].copy()
            mim_df.rename(columns=columns_map_meas1, inplace=True)
            mim_df2.rename(columns=columns_map_meas2, inplace=True)
            mim_df2['description'] = mim_df2['description']+'_2'
            
            time1 = time.time()
            mim_df['source'] = source
            mim_df2['source'] = source
            mim_df['unit'] = ''
            mim_df2['unit'] = ''
            if 'date2' not in mim_df.columns: 
                mim_df['date2'] = pd.NaT            
                mim_df2['date2'] = pd.NaT
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) +'/'+str(mim_df2.shape[0])+ ' records in ' + str(time1 - time2))
            pd_to_sql(maccabi_def.DBTYPE, mim_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            pd_to_sql(maccabi_def.DBTYPE, mim_df2[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            print('    saved ' + maccabi_def.TABLE + ' to sql in ' + str(time.time() - time1))
            time2 = time.time()
            cnt += 1

            
def load_measurmants(maccabi_def, type_dir):
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)  
    print(type_dir)
    file_list = os.listdir(type_dir)
    for fl in file_list:
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(type_dir, fl)       
        for mim_df in pd.read_csv(fullfile, chunksize=c_size, encoding='cp1255', error_bad_lines=False):
            mim_df.rename(columns=columns_map_meas1, inplace=True)
            time1 = time.time()
            mim_df['source'] = source
            mim_df['unit'] = ''
            if 'date2' not in mim_df.columns: 
                mim_df['date2'] = pd.NaT            
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))
            print(mim_df['value'].dtype)
            mim_df['value_num'] = pd.to_numeric(mim_df['value'],errors='coerce')
            print(mim_df[mim_df['value_num'].isnull()]['value'].value_counts())
            pd_to_sql(maccabi_def.DBTYPE, mim_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            print('    saved ' + maccabi_def.TABLE + ' to sql in ' + str(time.time() - time1))
            time2 = time.time()
            cnt += 1

def load_assessment(maccabi_def, type_dir, sep= ','):
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)  
    print(type_dir)
    file_list = os.listdir(type_dir)    
    for fl in file_list:        
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(type_dir, fl)       
        for mim_df in pd.read_csv(fullfile, sep=sep, chunksize=c_size, encoding='cp1255', error_bad_lines=False, usecols=[0,1,2,3,4,5]):
            mim_df.rename(columns=columns_map_asses, inplace=True)
            time1 = time.time()
            mim_df['source'] = source
            mim_df['unit'] = ''
            if 'date2' not in mim_df.columns: 
                mim_df['date2'] = pd.NaT
            if 'description' not in mim_df.columns: 
                mim_df['description'] = ''
            mim_df['date1'] = mim_df['date1'].str[0:4]+mim_df['date1'].str[5:7]+mim_df['date1'].str[8:10]
            mim_df.loc[mim_df['code'] == 8, 'code'] = mim_df['code']*10 + mim_df['RESULT_FIELD_CODE']
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))            
            pd_to_sql(maccabi_def.DBTYPE, mim_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            print('    saved ' + maccabi_def.TABLE + ' to sql in ' + str(time.time() - time1))
            time2 = time.time()
            cnt += 1
            

def load_one_file(fullfile, maccabi_def, col_map,  sep=',', encoding='cp1255'):
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)
    source = os.path.basename(fullfile)
    c_size = 5000000
    cnt = 0
    time2 = time.time()     
    print('reading from ' + fullfile)   
    for mim_df in pd.read_csv(fullfile, sep=sep, chunksize=c_size, encoding=encoding, error_bad_lines=False):          
        mim_df.rename(columns=col_map, inplace=True)
        time1 = time.time()
        mim_df['source'] = source
        if 'date2' not in mim_df.columns: 
            mim_df['date2'] = pd.NaT            
        if 'unit' not in mim_df.columns:
            mim_df['unit'] = ''
        if 'description' not in mim_df.columns: 
            mim_df['description'] = ''
            mim_df['date1'] = mim_df['date1'].str[0:4]+mim_df['date1'].str[5:7]+mim_df['date1'].str[8:10]
            mim_df.loc[mim_df['code'] == 8, 'code'] = mim_df['code']*10 + mim_df['RESULT_FIELD_CODE']
        print('    load cunk ' + str(cnt) + ' from ' + source + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))
        pd_to_sql(maccabi_def.DBTYPE, mim_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
        print('    saved ' + maccabi_def.TABLE + ' to sql in ' + str(time.time() - time1))
        time2 = time.time()
        cnt += 1
        
        
def load_one_type(maccabi_def, type_dir, sep=','):
    print(type_dir)
    file_list = os.listdir(type_dir)
    for fl in file_list:
        fullfile = os.path.join(type_dir, fl)
        load_one_file(fullfile, maccabi_def, columns_map)


def load_one_urine(maccabi_def, type_dir):
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)  
    print(type_dir)
    file_list = os.listdir(type_dir)
    file_list = [f for f in file_list if 'Additional' in f]
    for fl in file_list:
        source = os.path.basename(fl)
        c_size = 5000000
        cnt = 0
        time2 = time.time()     
        print('reading from ' + source)   
        fullfile = os.path.join(type_dir, fl)       
        for mim_df in pd.read_csv(fullfile, chunksize=c_size, encoding='cp1255', error_bad_lines=False):          
            mim_df.rename(columns=columns_map, inplace=True)
            mim_df['value'] = mim_df['value'].where((mim_df['value'] !=0) | (mim_df['ANS_CD'].str.strip() ==''), mim_df['ANS_CD'])
            time1 = time.time()
            mim_df['source'] = source
            if 'date2' not in mim_df.columns: 
                mim_df['date2'] = pd.NaT            
            print('    load cunk ' + str(cnt) + ' from ' + fl + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))
            pd_to_sql(maccabi_def.DBTYPE, mim_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            print('    saved ' + maccabi_def.TABLE + ' to sql in ' + str(time.time() - time1))
            time2 = time.time()
            cnt += 1

def load_lab_files():
    cfg = Configuration()
    raw_path = os.path.join(fixOS(cfg.data_folder), 'Laboratory_data')
    maccabi_def = MaccabiLabs()
    load_one_type(maccabi_def, raw_path)


def load_lab_urine_files():
    cfg = Configuration()
    raw_path = os.path.join(fixOS(cfg.data_folder), 'Laboratory_data')
    maccabi_def = MaccabiLabs()
    load_one_urine(maccabi_def, raw_path)
    

def load_measur_files():
    cfg = Configuration()
    raw_path = os.path.join(fixOS(cfg.data_folder), 'Measurements_data')
    maccabi_def = MaccabiLabs()
    load_measurmants(maccabi_def, raw_path)
    
    raw_path2 = os.path.join(fixOS(cfg.data_folder), 'Assessment_data')
    #load_assessment(maccabi_def, raw_path2)


def columns_to_stage(maccabi_def, source_file):
    source = os.path.basename(source_file)
    table_df = pd.read_csv(source_file, encoding='cp1255', sep='\t')
    print('Demographic lines: '+str(table_df.shape[0]))
    db_engine = get_sql_engine(maccabi_def.DBTYPE, maccabi_def.DBNAME, maccabi_def.username, maccabi_def.password)
    rec_list = []
    keys = list(table_df.columns) 
    keys.remove('random_id')    
    print('reading from ' + source + ' row count = ' + str(table_df.shape[0]))
    for i, row in table_df.iterrows():                
        for k in keys:
            if str(row[k]) != 'nan' and row[k] is not None and str(row[k]) !='99991231':
                row_dict = {'orig_pid': row['random_id'],
                            'code': k.lower(),
                            'value': str(row[k]).replace(',', ' '),
                            'description':  k.lower(),
                            'date1': None,
                            'source': source}
                rec_list.append(row_dict)
        if (i%10000) == 0:
            print(i)
            pivoted_df = pd.DataFrame(rec_list)
            pd_to_sql(maccabi_def.DBTYPE, pivoted_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
            rec_list = []
    # save the remainings:
    pivoted_df = pd.DataFrame(rec_list)
    pd_to_sql(maccabi_def.DBTYPE, pivoted_df[maccabi_def.COLUMNS], db_engine, maccabi_def.TABLE, if_exists='append')
    rec_list = []
    


def load_demographic():
    cfg = Configuration()
    raw_path = fixOS(cfg.data_folder)   
    maccabi_def = MaccabiDemographic()
    sql_create_table(maccabi_def)
    demo_files = ['Medial_Flu_demographics.txt']
    for fl in demo_files:
        demo_full_file = os.path.join(raw_path, 'FLU_DATA_29_07_2020', fl)
        print(demo_full_file)
        columns_to_stage(maccabi_def, demo_full_file)


if __name__ == '__main__':
    #maccabi_def = MaccabiLabs()
    #sql_create_table(maccabi_def)
    #load_lab_files()
    load_demographic()
    #load_measur_files()
    #load_lab_urine_files()
    
    ### Load the delta files
    cfg = Configuration()
    maccabi_def_delta = MaccabiLabsDelta()
    #sql_create_table(maccabi_def_delta)
    
    #raw_path = os.path.join(fixOS(cfg.data_folder), 'Laboratory_data_delta')    
    #load_one_type(maccabi_def_delta, raw_path, sep='\t')
    
    #raw_path = os.path.join(fixOS(cfg.data_folder), 'Measurements_data_delta')
    #load_measurmants(maccabi_def_delta, raw_path)
    
    #raw_path2 = os.path.join(fixOS(cfg.data_folder), 'Assessment_data_delta')
    #load_assessment(maccabi_def_delta, raw_path2, sep='\t')
    
    '''
    ### Load the April 20 delta
    delta_folder = os.path.join(fixOS(cfg.data_folder), 'FLU_DATA_04_2020')
    full_file = os.path.join(delta_folder, 'Medal_Flu_Laboratory.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map, sep='\t')
    
    full_file = os.path.join(delta_folder, 'Medial_Flu_measurements.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_meas1, sep='\t')
    full_file = os.path.join(delta_folder, 'Measurements_heart_rate.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_meas1, sep='\t')
    
    full_file = os.path.join(delta_folder, 'assessment_breath_data.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_asses, sep='\t')
    full_file = os.path.join(delta_folder, 'assessment_fever_data.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_asses, sep='\t')
    '''
    
    
    '''
    ### Load the Aug 20 delta
    delta_folder = os.path.join(fixOS(cfg.data_folder), 'FLU_DATA_29_07_2020')
    full_file = os.path.join(delta_folder, 'Medal_Flu_Laboratory.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map, sep='\t')
    
    full_file = os.path.join(delta_folder, 'Medial_Flu_measurements.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_meas1, sep='\t')
    full_file = os.path.join(delta_folder, 'Measurements_heart_rate.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_meas1, sep='\t', encoding=None)
    
    #full_file = os.path.join(delta_folder, 'assessment_breath_data.txt', )
    #load_one_file(full_file, maccabi_def_delta, columns_map_asses, sep='\t'
    full_file = os.path.join(delta_folder, 'assessment_fever_data.txt')
    load_one_file(full_file, maccabi_def_delta, columns_map_asses, sep='\t')
    '''