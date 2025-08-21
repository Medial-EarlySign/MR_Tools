from sql_utils import get_sql_engine
from staging_config import KPNWLabs, KPNWVitals, KPNWLabs2, MayoLabs
import pandas as pd
import os
from search_and_save import source

df_dict = {}


#stage_def = MayoLabs()
#source = 'mayo'
#default_labs = ['RDW\tRDW\t62647']
stage_def = KPNWLabs
source = 'kpnw'
default_labs = ['18841130\tHgb A1c\t542794', '22897436\tHbA1c Screen\t518282']
db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)


def get_all_labs_sql():
    file = os.path.join('data', source+'_labs_list.txt')
    if os.path.exists(file):
        labs_df = pd.read_csv(file, sep='\t')
    else:
        sql_query = "SELECT code, description, COUNT(*) as count FROM " + stage_def.TABLE + " GROUP BY  code, description"
        print(sql_query)
        labs_df = pd.read_sql_query(sql_query, db_engine)
        labs_df.to_csv(file, sep='\t', index=False)
    labs_df = labs_df[labs_df['count'] > 100]
    labs_df.sort_values(by='count', ascending=False, inplace=True)
    labs_list = labs_df['code'].astype(str) + '\t' + labs_df['description'].astype(str) + '\t' + labs_df['count'].astype(str)
    return labs_list.tolist()


def get_data_sql(codes_list):
    all_df = pd.DataFrame()
    for cd_dsc in codes_list:
        if cd_dsc in df_dict.keys():
            all_df = all_df.append(df_dict[cd_dsc])
        else:
            cd = cd_dsc.split('\t')[0]
            sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code = '" + cd + "'"
            print(sql_query)
            df = pd.read_sql_query(sql_query, db_engine)
            # remove outliers and nulls
            df['value'] = pd.to_numeric(df['value'], errors='coerse')
            df = df[df['value'].notnull()]
            df = df[(df['value'] > df['value'].quantile(0.01)) & (df['value'] < df['value'].quantile(0.99))]
            df_dict[cd_dsc] = df.copy()  # save in mem to improve performance
            all_df = all_df.append(df)
    all_df['unit'] = all_df['unit'].fillna('NaN')
    return all_df
