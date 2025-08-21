import os
import sys
import traceback
import pandas as pd
import numpy as np
import time

from Configuration import Configuration
# MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from staging_config import ThinLabs, ThinDemographic, ThinReadcodes, ThinLabsCat
from utils import fixOS, is_nan, read_tsv
from const_and_utils import read_fwf
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table


columns_map = {'combid': 'orig_pid', 'medcode': 'code', 'description_y': 'description', 'data2_x': 'value',
               'lookupdesc': 'unit', 'eventdate': 'date1', 'source': 'source'}

columns_map_cat = {'combid': 'orig_pid', 'ahdcode': 'code', 'description': 'description', 'lookup': 'value',
                   'eventdate': 'date1', 'source': 'source'}

columns_map_clinic = {'combid': 'orig_pid', 'ahdcode': 'code', 'description': 'description', 0: 'value',
                      'eventdate': 'date1', 'source': 'source'}

medical_map = {'combid': 'orig_pid', 'medcode': 'code',
               'eventdate': 'date1', 'enddate': 'date2', 'source': 'source'}


def numeric_to_sql(db_engine, thin_def,  num_df, read_codes, ahd_lookup):
    time1 = time.time()
    num_df = num_df.merge(read_codes, how='left', on='medcode')
    num_df = num_df.merge(ahd_lookup[ahd_lookup['datadesc'] == 'MEASURE_UNIT'], how='left',
                          left_on='data3_x', right_on='lookup')
    num_df.rename(columns=columns_map, inplace=True)
    num_df['description'] = num_df['description'].str.replace(',', ' ')
    num_df['value2'] = np.NaN
    num_df['date2'] = pd.NaT
    pd_to_sql(thin_def.DBTYPE, num_df[thin_def.COLUMNS], db_engine, thin_def.TABLE, if_exists='append')
    time2 = time.time()
    print('    saving labs to sql ' + str(num_df.shape[0]) + ' records in ' + str(time2 - time1))


def cats_to_sql(db_engine, thin_def,  cat_df, ahd_lookup):
    time1 = time.time()
    cat_df = cat_df[cat_df['data4_x'].notnull()]
    cat_df = cat_df.merge(ahd_lookup[ahd_lookup['datadesc'] == 'QUALIFIER'], how='left',
                          left_on='data4_x', right_on='lookup')
    cat_df.rename(columns=columns_map_cat, inplace=True)
    cat_df['description'] = cat_df['description'].str.replace(',', ' ')
    cat_df['value'] = cat_df['dataname'] + ':' + cat_df['value']  # .astype(str).str.replace(',', ' ')
    cat_df['unit'] = np.NaN
    cat_df['value2'] = np.NaN
    cat_df['date2'] = pd.NaT
    pd_to_sql(thin_def.DBTYPE, cat_df[thin_def.COLUMNS], db_engine, thin_def.TABLE, if_exists='append')
    #cat_df[thin_def.COLUMNS].to_sql(thin_def.TABLE, db_engine, if_exists='append', index=False)
    time2 = time.time()
    print('    saving cats to sql ' + str(cat_df.shape[0]) + ' records in ' + str(time2 - time1))


def clinic_to_sql(db_engine, thin_def,  clinc_df, ahd_codes, read_codes):
    time1 = time.time()
    clinc_df = clinc_df[['combid', 'eventdate', 'ahdcode', 'medcode', 'source',
                         'data1', 'data2', 'data3', 'data4', 'data5', 'data6']]
    clinc_df.drop_duplicates(inplace=True)
    clinc_df.set_index(['combid', 'eventdate', 'ahdcode', 'medcode', 'source'], inplace=True)
    clinc_df = clinc_df.stack(dropna=False).to_frame().reset_index()
    clinc_df = clinc_df[(clinc_df['level_5'] == 'data1') | (clinc_df[0].notnull())]
    clinc_df = clinc_df.merge(ahd_codes, how='left', on='ahdcode')
    #clinc_df['filed_desc'] = clinc_df.apply(lambda x: x[x['level_5']], axis=1)
    for dt in ['data1', 'data2', 'data3', 'data4', 'data5', 'data6']:
        cond = clinc_df['level_5'] == dt
        clinc_df.loc[cond, 'filed_desc'] = clinc_df[cond][dt]
    clinc_df['ahdcode'] = clinc_df['ahdcode'].astype(str) + '_' + clinc_df['level_5']
    clinc_df['description'] = clinc_df['description'].str.replace(',', ' ')
    clinc_df['description'] = clinc_df['description'] + '_' + clinc_df['filed_desc']

    clinc_df.rename(columns=columns_map_clinic, inplace=True)
    clinc_df['value'] = clinc_df['value'].astype(str).str.replace(',', ' ')
    clinc_df['unit'] = np.NaN
    clinc_df['value2'] = np.NaN
    clinc_df['date2'] = pd.NaT
    pd_to_sql(thin_def.DBTYPE, clinc_df[thin_def.COLUMNS], db_engine, thin_def.TABLE, if_exists='append')
    time2 = time.time()
    print('    saving clinic to sql ' + str(clinc_df.shape[0]) + ' records in ' + str(time2 - time1))


def load_ahd():
    thin_def = ThinLabs()
    db_engine = get_sql_engine(thin_def.DBTYPE, thin_def.DBNAME, thin_def.username, thin_def.password)
    sql_create_table(thin_def)
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')

    ahd_lookup = read_fwf('AHDlookups', raw_path)
    read_codes = read_fwf('Readcodes', raw_path)
    ahd_codes = read_fwf('AHDCodes', raw_path)
    clinic_ahd = ahd_codes[ahd_codes['datafile'] == 'CLINICAL']['ahdcode'].unique()

    cnt=0
    print(data_path)
    in_file_names = list(filter(lambda f: f.startswith('ahd.'), os.listdir(data_path)))
    start_parc = 'ahd.a0001'
    for in_file_name in in_file_names:
        cnt = cnt+1
        if in_file_name < start_parc:
            print(str(cnt) + ") skiping file " + in_file_name)
            continue

        pracid = in_file_name[-5:]
        print(str(cnt) + ") reading from " + in_file_name)
        time1 = time.time()
        ahd_df = read_fwf('ahd', data_path, in_file_name)
        time2 = time.time()
        print('    load ahd file ' + str(ahd_df.shape[0]) + ' records in ' + str(time2 - time1))
        # Setting for all ahd
        ahd_df['combid'] = pracid + ahd_df['patid']
        ahd_df = ahd_df[(ahd_df['ahdflag'] == 'Y')]

        #ahd_df['eventdate'] = ahd_df['eventdate'].astype(int)
        # Fix cases where month and/or day = 00
        if in_file_name == 'ahd.g9974':
            ahd_df = ahd_df[ahd_df['eventdate'].str.isdigit()]
            ahd_df['eventdate'] = ahd_df['eventdate'].astype(int)
            ahd_df['ahdcode'] = ahd_df['ahdcode'].astype(int)
        if in_file_name == 'ahd.j9855':
            ahd_df = ahd_df[ahd_df['data3'] != "\\"]
        ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 10000) > 0 else x + 100)
        ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 100) > 0 else x + 1)
        ahd_df['source'] = ahd_df['ahdcode'].astype(str) + '|' + ahd_df['medcode'] + '|' + in_file_name

        clinc_df = ahd_df[(ahd_df['ahdcode'].isin(clinic_ahd))].copy()
        clinic_to_sql(db_engine, thin_def, clinc_df, ahd_codes, read_codes)

        ahd_df = ahd_df.merge(ahd_codes, how='left', on='ahdcode')
        #num lab values
        ahd_labs = ahd_df[(ahd_df['datafile'] == 'TEST') & (ahd_df['data2_y'] == 'NUM_RESULT')]
        numeric_to_sql(db_engine, thin_def, ahd_labs, read_codes, ahd_lookup)

        ahd_cat = ahd_df[(ahd_df['datafile'] == 'TEST') & (ahd_df['data2_y'] != 'NUM_RESULT')]
        cats_to_sql(db_engine, thin_def, ahd_cat, ahd_lookup)

        print('Total time for file ' + in_file_name + ': ' + str(time.time() - time1))

def load_ahd_only_cats():
    thin_def = ThinLabsCat()
    db_engine = get_sql_engine(thin_def.DBTYPE, thin_def.DBNAME, thin_def.username, thin_def.password)
    #sql_create_table(thin_def)
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')

    ahd_lookup = read_fwf('AHDlookups', raw_path)
    read_codes = read_fwf('Readcodes', raw_path)
    ahd_codes = read_fwf('AHDCodes', raw_path)
    clinic_ahd = ahd_codes[ahd_codes['datafile'] == 'CLINICAL']['ahdcode'].unique()

    cnt = 0
    print(data_path)
    in_file_names = list(filter(lambda f: f.startswith('ahd.j'), os.listdir(data_path)))
    start_parc = 'ahd.a0001'
    for in_file_name in in_file_names:
        cnt = cnt + 1
        if in_file_name < start_parc:
            print(str(cnt) + ") skiping file " + in_file_name)
            continue

        pracid = in_file_name[-5:]
        print(str(cnt) + ") reading from " + in_file_name)
        time1 = time.time()
        ahd_df = read_fwf('ahd', data_path, in_file_name)
        time2 = time.time()
        print('    load ahd file ' + str(ahd_df.shape[0]) + ' records in ' + str(time2 - time1))
        # Setting for all ahd
        ahd_df['combid'] = pracid + ahd_df['patid']
        ahd_df = ahd_df[(ahd_df['ahdflag'] == 'Y')]

        # ahd_df['eventdate'] = ahd_df['eventdate'].astype(int)
        # Fix cases where month and/or day = 00
        if in_file_name == 'ahd.g9974':
            ahd_df = ahd_df[ahd_df['eventdate'].str.isdigit()]
            ahd_df['eventdate'] = ahd_df['eventdate'].astype(int)
            ahd_df['ahdcode'] = ahd_df['ahdcode'].astype(int)
        if in_file_name == 'ahd.j9855':
            ahd_df = ahd_df[ahd_df['data3'] != "\\"]
        ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 10000) > 0 else x + 100)
        ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 100) > 0 else x + 1)
        ahd_df['source'] = ahd_df['ahdcode'].astype(str) + '|' + ahd_df['medcode'] + '|' + in_file_name
        ahd_df = ahd_df.merge(ahd_codes, how='left', on='ahdcode')
        ahd_cat = ahd_df[(ahd_df['datafile'] == 'TEST') & (ahd_df['data2_y'] != 'NUM_RESULT')]
        cats_to_sql(db_engine, thin_def, ahd_cat, ahd_lookup)

        print('Total time for file ' + in_file_name + ': ' + str(time.time() - time1))

def load_demography():
    thin_demo_def = ThinDemographic()
    sql_create_table(thin_demo_def)
    db_engine = get_sql_engine(thin_demo_def.DBTYPE, thin_demo_def.DBNAME, thin_demo_def.username, thin_demo_def.password)
    cfg = Configuration()
    pat_demo_file = fixOS(cfg.patient_demo)
    valid_pat_flags = ['A', 'C', 'D']
    chunksize = 500000
    cnt = 0
    for demo_df in pd.read_csv(pat_demo_file, chunksize=chunksize):
        time1 = time.time()
        demo_df = demo_df[demo_df['patflag'].isin(valid_pat_flags)]
        demo_df.set_index('combid', inplace=True)
        demo_df = demo_df.stack().to_frame().reset_index()
        demo_df.rename(columns={'combid': 'orig_pid', 'level_1': 'code', 0: 'value'}, inplace=True)
        demo_df['description'] = demo_df['code']
        demo_df['date1'] = pd.NaT
        demo_df['source'] = np.nan
        cnt += 1
        pd_to_sql(thin_demo_def.DBTYPE, demo_df[thin_demo_def.COLUMNS], db_engine, thin_demo_def.TABLE, if_exists='append')
        print('Chunk num ' + str(cnt) + ' processed ' + str(chunksize) + ' patients in ' + str(time.time() - time1))



#medical.g9911
def load_medical():
    thin_def = ThinReadcodes()
    db_engine = get_sql_engine(thin_def.DBTYPE, thin_def.DBNAME, thin_def.username, thin_def.password)
    sql_create_table(thin_def)
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')
    read_codes = read_fwf('Readcodes', raw_path)
    cnt = 0
    in_file_names = list(filter(lambda f: f.startswith('medical.'), os.listdir(data_path)))
    start_proc = 'medical.a0000'
    for in_file_name in in_file_names:
        cnt = cnt + 1
        pracid = in_file_name[-5:]
        if in_file_name < start_proc:
            print(str(cnt) + ") skipping file " + in_file_name)
            continue

        print(str(cnt) + ") reading from " + in_file_name)
        time1 = time.time()
        medical_df = read_fwf('medical', data_path, in_file_name)
        time2 = time.time()
        print('    load ahd file ' + str(medical_df.shape[0]) + ' records in ' + str(time2 - time1))
        medical_df['eventdate'] = medical_df['eventdate'].apply(lambda x: x if ((x % 10000) > 0) | (x == 0) else x + 100)
        medical_df['eventdate'] = medical_df['eventdate'].apply(lambda x: x if ((x % 100) > 0) | (x == 0) else x + 1)
        medical_df['enddate'] = medical_df['enddate'].apply(lambda x: x if ((x % 10000) > 0) | (x == 0) else x + 100)
        medical_df['enddate'] = medical_df['enddate'].apply(lambda x: x if ((x % 100) > 0) | (x == 0) else x + 1)

        medical_df = medical_df[medical_df['medflag'].isin(['R', 'S'])]
        medical_df['combid'] = pracid + medical_df['patid']
        medical_df = medical_df.merge(read_codes, how='left', on='medcode')
        medical_df.rename(columns=medical_map, inplace=True)
        medical_df.loc[medical_df['date2'] == 0, 'date2'] = pd.NaT
        medical_df.loc[medical_df['date1'] == 0, 'date1'] = pd.NaT
        medical_df['description'] = medical_df['description'].str.replace(',', ' ')
        medical_df['value'] = medical_df['code']
        medical_df['value2'] = np.nan
        medical_df['source'] = in_file_name
        medical_df['unit'] = np.nan
        pd_to_sql(thin_def.DBTYPE, medical_df[thin_def.COLUMNS], db_engine, thin_def.TABLE, if_exists='append')
        print('Total time for file ' + in_file_name + ': ' + str(time.time() - time1))
        #if cnt>10:
        #    break

if __name__ == '__main__':
    #load_ahd()
    #load_demography()
    #load_medical()
    load_ahd_only_cats()
