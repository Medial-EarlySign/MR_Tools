import os
import sys
import traceback
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
#MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
#sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'common'))
from staging_config import KPNWLabs, KPNWDemographic, KPNWVitals, KPNWLabs2
from utils import fixOS, is_nan, read_tsv
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table

columns_map = {'PAT_ID_GEN': 'orig_pid', 'RC': 'code', 'RC_DESC': 'description', 'TRESULT': 'value',
               'UNITS': 'unit', 'RECV_DATE': 'date1', 'RDATE': 'date2'}

columns_map2 = {'PAT_ID_GEN': 'orig_pid', 'RC': 'code', 'TRESULT': 'value', 'RN': 'description',
                'UNITS': 'unit', 'RECV_DATE': 'date1', 'RDATE': 'date2'}

vital_map = {'PAT_ID_GEN': 'orig_pid', 'DISP_NAME': 'code', 'FLO_MEAS_NAME': 'description', 'MEAS_VALUE': 'value',
             'RECORDED_TIME': 'date1'}


def one_lab_file_to_sql(kpnw_def, db_engine, full_file):
    print('Reading file ' + full_file)
    for kp_labs in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
        time1 = time.time()
        kp_labs.rename(columns=columns_map, inplace=True)
        kp_labs['orig_pid'] = kp_labs['orig_pid'].astype(int)
        kp_labs['source'] = full_file
        kp_labs['value2'] = np.NaN
        pd_to_sql(kpnw_def.DBTYPE, kp_labs[kpnw_def.COLUMNS], db_engine, kpnw_def.TABLE, if_exists='append')
        time2 = time.time()
        print('    saving labs to sql ' + str(kp_labs.shape[0]) + ' records in ' + str(time2 - time1))


def one_vital_file_to_sql(kpnw_def, db_engine, full_file):
    print('Reading file ' + full_file)
    src = full_file.split('\\')[2]
    for kp_vit in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
        time1 = time.time()
        kp_vit.rename(columns=vital_map, inplace=True)
        kp_vit['orig_pid'] = kp_vit['orig_pid'].astype(int)
        kp_vit['code'] = kp_vit['code'].str.replace('?', '')
        kp_vit['code'] = kp_vit['code'].str[0:99]
        kp_vit['description'] = kp_vit['description'].str.replace('?', '')
        kp_vit['source'] = src
        kp_vit['value2'] = np.NaN
        kp_vit['unit'] = np.NaN
        kp_vit['date2'] = kp_vit['date1']
        print('Saving chunk to sql')
        pd_to_sql(kpnw_def.DBTYPE, kp_vit[kpnw_def.COLUMNS], db_engine, kpnw_def.TABLE, if_exists='append')
        time2 = time.time()
        print('    saving labs to sql ' + str(kp_vit.shape[0]) + ' records in ' + str(time2 - time1))


def labs_to_sql():
    kpnw_def = KPNWLabs()
    sql_create_table(kpnw_def)
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    cfg = Configuration()

    labs_files = [os.path.join(fixOS(cfg.delta_data_folder1), 'medial_flu_lab_reslt.sas7bdat'),
                  os.path.join(fixOS(cfg.delta_data_folder2), 'medial_flu_lab_reslt.sas7bdat'),
                  os.path.join(fixOS(cfg.data_folder), 'medial_flu_lab_reslt_tbl1a.sas7bdat'),
                  os.path.join(fixOS(cfg.data_folder), 'medial_flu_lab_reslt_tbl1b.sas7bdat')]

    work_path = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(work_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')
    for labs_file in labs_files:
        one_lab_file_to_sql(kpnw_def, db_engine, labs_file)


def delta_labs_to_sql(labs_file):
    kpnw_def = KPNWLabs()
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    one_lab_file_to_sql(kpnw_def, db_engine, labs_file)


def vitals_to_sql():
    kpnw_def = KPNWVitals()
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    cfg = Configuration()
    sql_create_table(kpnw_def)
    vit_files = [os.path.join(fixOS(cfg.delta_data_folder2), 'medial_flu_vitals_flowsheets.sas7bdat'),
                 os.path.join(fixOS(cfg.delta_data_folder1), 'medial_flu_vitals_flowsheets.sas7bdat'),
                 os.path.join(fixOS(cfg.data_folder), 'medial_flu_vitals_flowsheets.sas7bdat')]

    if not (os.path.exists(fixOS(cfg.data_folder))):
        raise NameError('config error - raw_path don''t exists')
    for vit_file in vit_files:
        one_vital_file_to_sql(kpnw_def, db_engine, vit_file)


def delta_vitals_to_sql(vit_file):
    kpnw_def = KPNWVitals()
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    one_vital_file_to_sql(kpnw_def, db_engine, vit_file)


def labs2_to_sql():
    kpnw_def = KPNWLabs2()
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    sql_create_table(kpnw_def)
    cfg = Configuration()
    lab2_file = 'medial_flu_lab_reslt_tbl2.sas7bdat'
    data_path = fixOS(cfg.data_folder)
    work_path = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(work_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')
    full_file = os.path.join(data_path, lab2_file)
    rc_map_file = pd.read_csv(os.path.join(code_folder, 'rc_rn_map.txt'), sep='\t')
    pc_map_file = pd.read_csv(os.path.join(code_folder, 'pc_pn_map.txt'), sep='\t')
    cnt=0
    for kp_labs in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
        time1 = time.time()
        kp_labs = kp_labs.merge(rc_map_file, on='RC')
        kp_labs = kp_labs.merge(pc_map_file, on='PC')
        kp_labs.rename(columns=columns_map2, inplace=True)
        kp_labs['orig_pid'] = kp_labs['orig_pid'].astype(int)
        kp_labs['description'] = kp_labs['description'].str.replace('%', 'percent')
        kp_labs['description'] = kp_labs['description']+'('+kp_labs['PN']+')'
        kp_labs['source'] = lab2_file
        kp_labs['value2'] = np.NaN
        pd_to_sql(kpnw_def.DBTYPE, kp_labs[kpnw_def.COLUMNS], db_engine, kpnw_def.TABLE, if_exists='append')
        time2 = time.time()
        cnt+=1
        print(str(cnt) + '   saving labs to sql ' + str(kp_labs.shape[0]) + ' records in ' + str(time2 - time1))


# def demographic_to_sql():
#     cfg = Configuration()
#     data_path = fixOS(cfg.data_folder)
#     delta_data_path = fixOS(cfg.delta_data_folder)
#     kp__demo_def = KPNWDemographic()
#     sql_create_table(kp__demo_def)
#     db_engine = get_sql_engine(kp__demo_def.DBTYPE, kp__demo_def.DBNAME, kp__demo_def.username, kp__demo_def.password)
#     pat_demo_file = 'medial_flu_pat.sas7bdat'
#     full_files = [os.path.join(data_path, pat_demo_file), os.path.join(delta_data_path, pat_demo_file)]
#     for full_file in full_files:
#         print('reading ' + full_file)
#         for demo_df in pd.read_sas(full_file, chunksize=500000, encoding='utf-8'):
#             demo_df['PAT_ID_GEN'] = demo_df['PAT_ID_GEN'].astype(int)
#             demo_df.set_index('PAT_ID_GEN', inplace=True)
#             demo_df = demo_df.stack().to_frame().reset_index()
#             demo_df.rename(columns={'PAT_ID_GEN': 'orig_pid', 'level_1': 'code', 0: 'value'}, inplace=True)
#             demo_df['description'] = demo_df['code']
#             demo_df['date1'] = pd.NaT
#             demo_df['source'] = np.nan
#             print(' Going to save chunk in sql table ' + kp__demo_def.TABLE)
#             pd_to_sql(kp__demo_def.DBTYPE, demo_df[kp__demo_def.COLUMNS], db_engine, kp__demo_def.TABLE, if_exists='append')


def demographic_to_sql():
    cfg = Configuration()
    kp__demo_def = KPNWDemographic()
    sql_create_table(kp__demo_def)
    db_engine = get_sql_engine(kp__demo_def.DBTYPE, kp__demo_def.DBNAME, kp__demo_def.username, kp__demo_def.password)
    pat_demo_file = 'medial_flu_pat.sas7bdat'
    #demo_files = [os.path.join(fixOS(cfg.delta_data_folder2), pat_demo_file),
    #              os.path.join(fixOS(cfg.delta_data_folder), pat_demo_file),
    #              os.path.join(fixOS(cfg.data_folder), pat_demo_file)]
    demo_files = []
    for dataf in cfg.data_folders:
        demo_files.append(os.path.join(fixOS(dataf), pat_demo_file))

    demo_df = pd.DataFrame()
    for i, d_file in zip(range(1, len(demo_files)+1), demo_files):
        print('Reading file ' + d_file + ' (' + str(i) + ')')
        demo_one_df = pd.read_sas(d_file, encoding='utf-8')
        demo_one_df['ver'] = i
        demo_df = demo_df.append(demo_one_df)
    demo_df.loc[demo_df['GENDER'] == 'U', 'ver'] = 100
    demo_df.sort_values(['PAT_ID_GEN', 'ver'], inplace=True)
    demo_df.drop_duplicates('PAT_ID_GEN', keep='first', inplace=True)

    demo_df['PAT_ID_GEN'] = demo_df['PAT_ID_GEN'].astype(int)
    demo_df.set_index('PAT_ID_GEN', inplace=True)
    demo_df = demo_df.stack().to_frame().reset_index()
    demo_df.rename(columns={'PAT_ID_GEN': 'orig_pid', 'level_1': 'code', 0: 'value'}, inplace=True)
    demo_df['description'] = demo_df['code']
    demo_df['date1'] = pd.NaT
    demo_df['source'] = np.nan
    print(' Going to save in to sql table ' + kp__demo_def.TABLE)
    chunksize = 500000
    for i in range(0, demo_df.shape[0]+1, chunksize):
        print(' Going to write demo_df['+str(i)+':'+str(i+chunksize)+']')
        pd_to_sql(kp__demo_def.DBTYPE, demo_df[kp__demo_def.COLUMNS][i:i+chunksize], db_engine, kp__demo_def.TABLE, if_exists='append')


def vitals_by_pat_to_sql():
    kpnw_def = KPNWVitals()
    db_engine = get_sql_engine(kpnw_def.DBTYPE, kpnw_def.DBNAME, kpnw_def.username, kpnw_def.password)
    cfg = Configuration()
    data_path = fixOS(cfg.data_folder)

    vital_file = 'medial_flu_vitals.sas7bdat'
    full_file = os.path.join(data_path, vital_file)
    cnt = 1
    time2 = time.time()
    for kp_vit in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
        time1 = time.time()
        print('read chunk ' + str(cnt) + ' in ' + str(time1-time2))
        kp_vit.drop(columns=['LINE', 'PAIN_CAT'], inplace=True)
        kp_vit['PAT_ID_GEN'] = kp_vit['PAT_ID_GEN'].astype(int)
        kp_vit.set_index(['PAT_ID_GEN', 'CONTACT_DATE'], inplace=True)
        kp_vit = kp_vit.stack().to_frame().reset_index()
        kp_vit.rename(columns={'PAT_ID_GEN': 'orig_pid', 'CONTACT_DATE': 'date1',  'level_2': 'code', 0: 'value'}, inplace=True)
        #kp_vit['value'] = kp_vit['value'].str[0:200]
        kp_vit['description'] = kp_vit['code']
        kp_vit['date2'] = pd.NaT
        kp_vit['value2'] = np.NaN
        kp_vit['unit'] = np.NaN
        kp_vit['source'] = vital_file
        time3 = time.time()
        print('procss chunk ' + str(cnt) + ' size ' + str(kp_vit.shape[0]) + ' in ' + str(time3 - time1))
        pd_to_sql(kpnw_def.DBTYPE, kp_vit[kpnw_def.COLUMNS], db_engine, kpnw_def.TABLE, if_exists='append')
        print('saved chunk ' + str(cnt) + ' size ' + str(kp_vit.shape[0]) + ' in ' + str(time.time() - time3))
        cnt += 1
        time2 = time.time()


if __name__ == '__main__':
    #labs_to_sql()
    demographic_to_sql()
    #vitals_to_sql()
    #vitals_by_pat_to_sql()
    #labs2_to_sql()

    cfg = Configuration()
    #delta_labs_file = os.path.join(fixOS(cfg.delta_data_folder3), 'medial_flu_lab_reslt.sas7bdat')
    #delta_labs_to_sql(delta_labs_file)

    #delta_vit_file = os.path.join(fixOS(cfg.delta_data_folder3), 'medial_flu_vitals_flowsheets.sas7bdat')
    #delta_vitals_to_sql(delta_vit_file)

