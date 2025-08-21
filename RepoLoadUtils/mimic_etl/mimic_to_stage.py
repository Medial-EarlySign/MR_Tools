import os
import sys
import traceback
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
#MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
#sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'common'))
from staging_config import MimicLabs, MimicDemographic
from utils import fixOS, is_nan
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table


columns_map = {'SUBJECT_ID': 'orig_pid', 'ITEMID': 'code', 'LABEL': 'description', 'VALUE': 'value',
               'VALUEUOM': 'unit', 'CHARTTIME': 'date1', 'STORETIME': 'date2'}

demo_columns_map = {'SUBJECT_ID': 'orig_pid', 'GENDER': 'gender', 'DOB': 'bdate', 'DOD': 'death',
                    'ETHNICITY': 'ethnicity', 'MARITAL_STATUS': 'marital_status', 'RELIGION': 'religion',
                    'INSURANCE': 'insurance'}


def load_one_file(mimic_def, mimic_file, item_file):
    db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username, mimic_def.password)
    source = os.path.basename(mimic_file)
    c_size = 5000000
    cnt = 0
    time2 = time.time()
    print('reading from ' + source)
    item_df = pd.read_csv(item_file, encoding='utf-8')
    for mim_df in pd.read_csv(mimic_file, chunksize=c_size, quotechar='"'):
        mim_df = mim_df.merge(item_df, how='left', on='ITEMID')
        mim_df.rename(columns=columns_map, inplace=True)
        time1 = time.time()
        mim_df['source'] = source
        if 'date2' not in mim_df.columns:
            mim_df['date2'] = pd.NaT
        mim_df['description'] = mim_df['description'].str.replace(',', '.')
        mim_df['value'] = mim_df['value'].astype(str).str.replace(',', '.')
        mim_df['value'] = mim_df['value'].str.replace('\\', '')
        mim_df['value2'] = np.nan
        print('    load cunk ' + str(cnt) + ' from ' + mimic_file + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))
        pd_to_sql(mimic_def.DBTYPE, mim_df[mimic_def.COLUMNS], db_engine, mimic_def.TABLE, if_exists='append')
        print('    saved ' + mimic_def.TABLE + ' to sql in ' + str(time.time() - time1))
        time2 = time.time()
        cnt += 1


def load_lab_files():
    cfg = Configuration()
    raw_path = fixOS(cfg.data_folder)
    mimic_def = MimicLabs()
    sql_create_table(mimic_def)
    lab_files = ['LABEVENTS.csv', 'CHARTEVENTS.csv', 'OUTPUTEVENTS.csv']
    item_files = ['D_LABITEMS.csv', 'D_ITEMS.csv', 'D_ITEMS.csv']
    for fl, dfl in zip(lab_files, item_files):
        mimic_full_file = os.path.join(raw_path, fl)
        item_full_file = os.path.join(raw_path, dfl)
        load_one_file(mimic_def, mimic_full_file, item_full_file)


def load_demographic_old():
    cfg = Configuration()
    raw_path = fixOS(cfg.data_folder)
    admissions_file = os.path.join(raw_path, 'ADMISSIONS.csv')
    patient_file = os.path.join(raw_path, 'PATIENTS.csv')
    mimic_def = MimicDemographic()
    db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username, mimic_def.password)
    sql_create_table(mimic_def)
    admissions_df = pd.read_csv(admissions_file, encoding='utf-8')
    admissions_df.drop_duplicates(subset='SUBJECT_ID', keep='last', inplace=True)
    patient_df = pd.read_csv(patient_file,  encoding='utf-8')
    demo_df = patient_df.merge(admissions_df, how='left', on='SUBJECT_ID')
    demo_df.rename(columns=demo_columns_map, inplace=True)
    pd_to_sql(mimic_def.DBTYPE, demo_df[mimic_def.COLUMNS], db_engine, mimic_def.TABLE, if_exists='append')


def columns_to_stage(mimic_def, mimic_file):
    source = os.path.basename(mimic_file)
    table_df = pd.read_csv(mimic_file, encoding='utf-8')
    db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username, mimic_def.password)
    rec_list = []
    keys = list(table_df.columns)
    keys.remove('ROW_ID')
    keys.remove('SUBJECT_ID')
    print('reading from ' + source)
    for i, row in table_df.iterrows():
        for k in keys:
            if str(row[k]) != 'nan' and row[k] is not None:
                row_dict = {'orig_pid': row['SUBJECT_ID'],
                            'code': k.lower(),
                            'value': str(row[k]).replace(',', ' '),
                            'description':  k.lower(),
                            'date1': None,
                            'source': source}
                rec_list.append(row_dict)
    pivoted_df = pd.DataFrame(rec_list)
    pd_to_sql(mimic_def.DBTYPE, pivoted_df[mimic_def.COLUMNS], db_engine, mimic_def.TABLE, if_exists='append')


def load_demographic():
    cfg = Configuration()
    raw_path = fixOS(cfg.data_folder)
    mimic_def = MimicDemographic()
    sql_create_table(mimic_def)
    demo_files = ['PATIENTS.csv', 'ADMISSIONS.csv']
    for fl in demo_files:
        mimic_full_file = os.path.join(raw_path, fl)
        columns_to_stage(mimic_def, mimic_full_file)


if __name__ == '__main__':
    load_lab_files()
    load_demographic()
