import os
import sys
import traceback
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
#MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
#sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'common'))
from staging_config import JilinLabs, JilinDemographic
from utils import fixOS, is_nan
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table
from dictionery_chinese import ch_en_dict

columns_map = {'patient_id': 'orig_pid', 'result_item': 'description', 'result_value': 'value',
               'results_unit': 'unit', 'bad_code_time': 'date1'}


def lab_file_to_sql(jilin_def, excl_file, path, db_engine):
    full_file = os.path.join(path, excl_file)
    orig_df = pd.read_excel(full_file)
    en_columns = {}
    orig_columns = orig_df.columns
    time1 = time.time()
    cnt=1
    for col in orig_columns:
        #col_en = ch_en_dict[col]
        col_en = ch_en_dict.get(col, 'col'+str(cnt))
        en_columns[col] = col_en.replace(' ', '_').lower()
        cnt += 1
    print(en_columns)
    orig_df.rename(columns=en_columns, inplace=True)
    orig_df = orig_df[orig_df['patient_id'].notnull()]
    #### Labs loading
    eng_df = pd.DataFrame()
    eng_df['orig_pid'] = orig_df['patient_id'].astype(int)
    eng_df['code'] = orig_df['result_item'].apply(lambda x:  ch_en_dict.get(x, x))
    eng_df['description'] = eng_df['code']
    eng_df['value'] = orig_df['result_value']
    eng_df['unit'] = orig_df['results_unit']
    eng_df['date1'] = orig_df['bad_code_time']
    eng_df['date2'] = pd.NaT
    eng_df['value2'] = np.nan
    eng_df['source'] = excl_file

    # demo loading
    eng_demo_df = pd.DataFrame()
    eng_demo_df['orig_pid'] = orig_df['patient_id'].astype(int)

    time2 = time.time()
    print('    load ' + full_file + ' file ' + str(eng_df.shape[0]) + ' records in ' + str(time1 - time2))
    pd_to_sql(jilin_def.DBTYPE, eng_df[jilin_def.COLUMNS], db_engine, jilin_def.TABLE, if_exists='append')
    print('    saved ' + jilin_def.TABLE + ' to sql in ' + str(time1-time.time()))

    def lab_file_to_sql(jilin_def, excl_file, path, db_engine):
        full_file = os.path.join(path, excl_file)
        orig_df = pd.read_excel(full_file)
        en_columns = {}
        orig_columns = orig_df.columns
        time1 = time.time()
        cnt = 1
        for col in orig_columns:
            # col_en = ch_en_dict[col]
            col_en = ch_en_dict.get(col, 'col' + str(cnt))
            en_columns[col] = col_en.replace(' ', '_').lower()
            cnt += 1
        print(en_columns)
        orig_df.rename(columns=en_columns, inplace=True)
        orig_df = orig_df[orig_df['patient_id'].notnull()]
        #### Labs loading
        eng_df = pd.DataFrame()
        eng_df['orig_pid'] = orig_df['patient_id'].astype(int)
        eng_df['code'] = orig_df['result_item'].apply(lambda x: ch_en_dict.get(x, x))
        eng_df['description'] = eng_df['code']
        eng_df['value'] = orig_df['result_value']
        eng_df['unit'] = orig_df['results_unit']
        eng_df['date1'] = orig_df['bad_code_time']
        eng_df['date2'] = pd.NaT
        eng_df['value2'] = np.nan
        eng_df['source'] = excl_file

        # demo loading
        eng_demo_df = pd.DataFrame()
        eng_demo_df['orig_pid'] = orig_df['patient_id'].astype(int)

        time2 = time.time()
        print('    load ' + full_file + ' file ' + str(eng_df.shape[0]) + ' records in ' + str(time1 - time2))
        pd_to_sql(jilin_def.DBTYPE, eng_df[jilin_def.COLUMNS], db_engine, jilin_def.TABLE, if_exists='append')
        print('    saved ' + jilin_def.TABLE + ' to sql in ' + str(time1 - time.time()))


def lab_file_to_demographic(excl_file, path):
    full_file = os.path.join(path, excl_file)
    orig_df = pd.read_excel(full_file)
    en_columns = {}
    orig_columns = orig_df.columns
    time1 = time.time()
    cnt = 1
    for col in orig_columns:
        # col_en = ch_en_dict[col]
        col_en = ch_en_dict.get(col, 'col' + str(cnt))
        en_columns[col] = col_en.replace(' ', '_').lower()
        cnt += 1
    #print(en_columns)
    orig_df.rename(columns=en_columns, inplace=True)
    orig_df = orig_df[orig_df['patient_id'].notnull()]

    # demo loading
    eng_demo_df = pd.DataFrame()
    eng_demo_df['orig_pid'] = orig_df['patient_id'].astype(int)
    eng_demo_df['gender'] = orig_df['gender'].apply(lambda x: ch_en_dict.get(x, x))
    eng_demo_df['dob'] = orig_df['bad_code_time'].apply(lambda x: x.year) - orig_df['age']
    eng_demo_df['dob'] = eng_demo_df['dob'].astype(float)
    rec_list = []
    for i, row in eng_demo_df.iterrows():
        for k in ['gender', 'dob']:
            if str(row[k]) != 'nan' and row[k] is not None:
                row_dict = {'orig_pid': row['orig_pid'],
                            'code': k,
                            'value': row[k],
                            'description':  k,
                            'date1': None,
                            'source': excl_file}
                rec_list.append(row_dict)
    pivoted_df = pd.DataFrame(rec_list).drop_duplicates(subset=['orig_pid', 'code', 'description', 'value'])
    return pivoted_df


def load_lab_files():
    cfg = Configuration()
    data_path = fixOS(cfg.data_folder)
    jilin_def = JilinLabs()
    #sql_create_table(jilin_def)
    jilin_demo_df = JilinDemographic()
    #sql_create_table(jilin_demo_df)
    db_engine = get_sql_engine(jilin_def.DBTYPE, jilin_def.DBNAME, jilin_def.username, jilin_def.password)
    lab_dir = os.path.join(data_path, 'laboratory_results')
    all_demo_df = pd.DataFrame()
    for subdir, dirs, files in os.walk(lab_dir):
        for file in files:
            if file != 'colon.xlsx':
                continue
            print(os.path.join(subdir, file))
            #lab_file_to_sql(jilin_def, file, subdir, db_engine)
            demo_df = lab_file_to_demographic(file, subdir)
            all_demo_df = all_demo_df.append(demo_df)
            all_demo_df.drop_duplicates(subset=['orig_pid', 'code', 'description', 'value'], inplace=True)
    print('Going to save demographic table of ' + str(all_demo_df.shape[0]) + ' records')
    #pd_to_sql(jilin_demo_df.DBTYPE, all_demo_df[jilin_demo_df.COLUMNS], db_engine, jilin_demo_df.TABLE, if_exists='replace')


if __name__ == '__main__':
    load_lab_files()
