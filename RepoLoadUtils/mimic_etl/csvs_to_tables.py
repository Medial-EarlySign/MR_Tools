import os
import sys
import pandas as pd
import io
import time
from utils import fixOS
from sql_utils import get_sql_engine
import d6tstack
#SQL_SERVER = 'MSSQL'
SQL_SERVER = 'POSTGRESSQL'
#SQL_SERVER = 'D6_POSTGRESSQL'
DBNAME = 'RawMimic'
username = 'postgres'
password=''

demo_dict_list = []

mimic_source_dir = fixOS('T:\\ICU\\Mimic-3-1.4\\')
out_folder = fixOS('W:\\Users\\Tamar\\\mimic_load\\')


def mimic_table_to_sql(mimic_file, db_engine):
    mimic_full_file = os.path.join(mimic_source_dir, mimic_file)
    c_size = 1000000
    cnt = 0
    time2 = time.time()
    print('reading from ' + mimic_file)
    for mim_df in pd.read_csv(mimic_full_file, chunksize=c_size):  # , skiprows=32000000):
        print(mim_df.shape)
        ren_cols = {x: x.replace('"', '').lower() for x in mim_df.columns}
        mim_df.rename(columns=ren_cols, inplace=True)
        time1 = time.time()
        print('    load cunk ' + str(cnt) + ' from ' + mimic_file + ' file ' + str(mim_df.shape[0]) + ' records in ' + str(time1 - time2))
        table = mimic_file[:-4].lower()
        #table = '"' + table + '"'
       # if cnt == 0:
       #     mim_df.to_sql(table, db_engine, if_exists='replace')
       #     #d6tstack.utils.pd_to_psql(mim_df, db_engine, table, if_exists='replace')
       # else:
        mim_df.to_sql(table, db_engine, if_exists='append', index=False)
            #d6tstack.utils.pd_to_psql(mim_df, db_engine, table, if_exists='append')
        print('    saved ' + table + ' to sql in ' + str(time.time() - time1))
        time2 = time.time()
        cnt += 1


if __name__ == '__main__':
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    mimic_files = os.listdir(mimic_source_dir)
    db_engine = get_sql_engine(SQL_SERVER, DBNAME, username, password)
    for fl in mimic_files:
        mimic_table_to_sql(fl, db_engine)



