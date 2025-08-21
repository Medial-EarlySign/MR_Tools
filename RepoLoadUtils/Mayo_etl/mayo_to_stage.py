import os
import sys
import traceback
import pandas as pd
import numpy as np
import time
from Configuration import Configuration
#MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
#sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'common'))
from staging_config import MayoLabs, MayoDemographic
from utils import fixOS, is_nan, read_tsv
from sql_utils import get_sql_engine, pd_to_sql, sql_create_table

columns_map_lab = {'Clinic': 'orig_pid', 'Lab_Date': 'date1', 'TestDesc': 'code', 'Resultn': 'value',
                   'Resultc': 'value2', 'Units': 'unit'}


def cbc_to_sql():
    mayo_def = MayoLabs()
    db_engine = get_sql_engine(mayo_def.DBTYPE, mayo_def.DBNAME, mayo_def.username, mayo_def.password)
    sql_create_table(mayo_def)
    cfg = Configuration()
    data_path = fixOS(cfg.data_folder)
    labs_file = 'CBC.csv'
    full_file = os.path.join(data_path, labs_file)
    labs_df = pd.read_csv(full_file)
    time1 = time.time()
    labs_df.rename(columns=columns_map_lab, inplace=True)
    labs_df['orig_pid'] = labs_df['orig_pid'].astype(int)
    labs_df.loc[:, 'description'] = labs_df['code']
    labs_df['code'] = labs_df['code'].str.replace('%', 'per')
    labs_df['source'] = labs_file
    labs_df['date1'] = labs_df['date1'] + ' ' + labs_df['Lab_Time']
    labs_df['date1'] = pd.to_datetime(labs_df['date1'], format='%m/%d/%Y %H:%M:%S').dt.date
    labs_df['date2'] = np.nan
    pd_to_sql(mayo_def.DBTYPE, labs_df[mayo_def.COLUMNS], db_engine, mayo_def.TABLE, if_exists='append')
    time2 = time.time()
    print('    saving labs to sql ' + str(labs_df.shape[0]) + ' records in ' + str(time2 - time1))


def demo_from_pci():
    mayo_def = MayoDemographic()
    db_engine = get_sql_engine(mayo_def.DBTYPE, mayo_def.DBNAME, mayo_def.username, mayo_def.password)
    sql_create_table(mayo_def)
    cfg = Configuration()
    data_path = fixOS(cfg.data_folder)
    demo_file = 'results_pci_EVENTS.csv'
    full_file = os.path.join(data_path, demo_file)
    demo_df = pd.read_csv(full_file, usecols=[0, 2, 3])
    demo_df.drop_duplicates(inplace=True)

    demo_df.set_index('clinic', inplace=True)
    demo_df = demo_df.stack().to_frame().reset_index()
    demo_df.rename(columns={'clinic': 'orig_pid', 'level_1': 'code', 0: 'value'}, inplace=True)
    demo_df['description'] = demo_df['code']
    demo_df['date1'] = pd.NaT
    demo_df['source'] = demo_file

    pd_to_sql(mayo_def.DBTYPE, demo_df[mayo_def.COLUMNS], db_engine, mayo_def.TABLE, if_exists='append')


if __name__ == '__main__':
    cbc_to_sql()
    #demo_from_pci()
