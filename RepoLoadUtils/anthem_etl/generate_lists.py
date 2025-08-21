import os
import pandas as pd
import numpy as np
from DB import DB
from sql_utils import create_postgres_engine_generic
categories = ['23_KD_IGG_BAND', 'ACPA', 'AFP_MOM']
pre2d_signals = ['Glucose', 'HbA1C', 'Triglycerides', 'ALT', 'WBC']
alon_file = '/mnt/project/work/rep_load/configs/LABS_MAP.list'
alon_df = pd.read_csv(alon_file, sep='\t', usecols=[0,3], names=['description', 'signal'])
alon_df.dropna(inplace=True)
alon_df.loc[:, 'code'] = alon_df['description']
alon_df.loc[:, 'type'] = 'numeric'
alon_df.loc[alon_df['signal'].isin(categories), 'type'] = 'category'
alon_df.loc[:, 'source'] = 'labs_sample_3years'
### only pre2D signals:
alon_df_pre = alon_df[alon_df['signal'].isin(pre2d_signals)].copy()
# print(alon_df)
out_file = '/mnt/project/Tools/RepoLoadUtils/anthem_etl/anthem_pre2d_signal_map.csv'
alon_df_pre[['signal','source','code', 'description', 'type']].to_csv(out_file, sep='\t', index=False)

at_map = pd.read_csv(out_file, sep='\t')
at_map_numeric = at_map[(at_map['type'] == 'numeric')]
db_det = DB()
db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
lab_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_labs_sample_3years'
print(at_map_numeric)
cnt=0
dct_list = []
for sig, sig_grp in at_map_numeric.groupby('signal'):
    cnt+=1
    codes_list = [str(x) for x in sig_grp['code'].values]
    select = "membernumberhci as orig_pid, testname as code, testname as description, resultnum as value, resulttext as value2, servicedate as date1, unitsid as unit, 'abs_sample_3years' as source"
    sql_query = "SELECT " + select + " FROM " + lab_table + " WHERE code in ('" + "','".join(codes_list) + "')"
    sql_query = sql_query.replace('%', '%%')
    print(sql_query)

    for vals in pd.read_sql_query(sql_query, db_engine, chunksize=5000000):
        for un in vals['unit'].unique():
            dict1 = {'signal': sig, 'unit': un, 'muliplier':1, 'addition':0, 'Round': 0.01}
            dct_list.append(dict1)
        print(sig, vals['unit'].unique(), vals.shape[0], vals[vals['value'].notnull()].shape[0])

    #if cnt > 4:
    #    break
df = pd.DataFrame(dct_list)
df.drop_duplicates(inplace=True)
df['rndf'] = np.nan
unit_file = '/mnt/project/Tools/RepoLoadUtils/anthem_etl/unitTranslator.txt'
df[['signal', 'unit', 'muliplier', 'addition', 'Round', 'rndf']].to_csv(unit_file, sep='\t', index=False)
