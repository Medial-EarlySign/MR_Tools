import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df, get_dict_set_df
from DB import DB
from sql_utils import create_postgres_engine_generic
from shutil import copy

#file1 = '/home/LinuxDswUser/work/anthem_load/FinalSignals/HbA1C1'
#file2 = '/home/LinuxDswUser/work/anthem_load/FinalSignals/HbA1C2'
#df1 = pd.read_csv(file1, sep='\t', names=['pid', 'date', 'v1', 'unit', 'source'], usecols=[0, 2,3,4,5])
#df2 = pd.read_csv(file2, sep='\t', names=['pid', 'date', 'v1', 'unit', 'source'], usecols=[0, 2,3,4,5])
#df1 = df1.append(df2)



'''
dc_start = 10000
ndc_dict_file = '/home/LinuxDswUser/work/anthem_load/rep_configs/dicts/dict.drugs'
unique_drug = pd.read_csv(ndc_dict_file, sep='\t', usecols=[2], names=['code'], skiprows=1)
unique_drug.drop_duplicates(inplace=True)
unique_drug = unique_drug.assign(defid=range(dc_start, dc_start + unique_drug.shape[0]))
unique_drug['def'] = 'DEF'
write_tsv(unique_drug[['def', 'defid', 'code']], '/home/LinuxDswUser/work/anthem_load/rep_configs/dicts/', 'dict.drugs1')
first_line = 'SECTION\t' + 'Drug' + '\n'
add_fisrt_line(first_line, ndc_dict_file+'1')

ndc_dict_df = pd.read_csv(ndc_dict_file, sep='\t', names=['code'], usecols=[2])
ndc_dict_df = ndc_dict_df[ndc_dict_df['code'].str.contains('NDC_CODE')]
ndc_dict_df['code'] = ndc_dict_df['code'].str.replace('NDC_CODE:', '')
mrg = ndc_df.merge(ndc_dict_df, on='code', how='right')



db_det = DB()
idc10_table = 'pk_us_487_o_rgprc2ltzklg_anthem_opendata_ndc_product'
db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
sql_query = "SELECT product_ndc as code, proprietary_name as desc FROM " + idc10_table
ndc_df = pd.read_sql_query(sql_query, db_engine)

ndc_dict_file = '/mnt/project/Tools/DictUtils/Ontologies/NDC/dicts/dict.ndc_defs'
ndc_dict_df = pd.read_csv(ndc_dict_file, sep='\t', names=['code'], usecols=[2])
ndc_dict_df = ndc_dict_df[ndc_dict_df['code'].str.contains('NDC_CODE')]
ndc_dict_df['code'] = ndc_dict_df['code'].str.replace('NDC_CODE:', '')
mrg = ndc_df.merge(ndc_dict_df, on='code', how='right')
print(mrg)
'''

'''
cfg = Configuration()
dict_df = get_dict_set_df(cfg.repo_folder, 'Drug')
print(dict_df.head(10))

list_file = '/mnt/project/Tools/Registries/Lists/diabetes_ATC_codes.full'
reg_list_df = pd.read_csv(list_file, usecols=[0], names=['desc'])
print(reg_list_df)

relevant_codes = reg_list_df.merge(dict_df, how='left', on='desc')
print(relevant_codes)
atc10_drugs = relevant_codes.merge(dict_df, on='codeid', how='left')
atc10_drugs.to_csv('/home/LinuxDswUser/work/anthem_load/temp/ATC10_drugs.txt', sep='\t', index=False)

#reg = sig_df[sig_df['val'].isin(relevant_codes['codeid'].values)].copy()
'''

'''
file1 = '/home/LinuxDswUser/work/Pre2D/RegistryAndSamples/diabetes.DM_Registry_mem'
df = pd.read_csv(file1, sep='\t', names=['pid','sig', 'd1', 'd2', 'val'])
df.loc[df['d1']<=2018, 'd1'] = df[df['d1']<=2018]['d1']*10000 + 100
df['d1'] = df['d1'].astype(int)
df['d2'] = df['d2'].astype(int)
print(df)
df[['pid', 'sig', 'd1', 'd2', 'val']].to_csv(file1+'1', sep='\t', index=False, header=False)
'''

file1 = '/home/LinuxDswUser/work/Pre2D/RegistryAndSamples/diabetes.DM_Registry'
file2 = '/home/LinuxDswUser/work/Pre2D/RegistryAndSamples/diabetes.DM_Registry_mem1'
df1 = pd.read_csv(file1, sep='\t', names=['pid','sig', 'd1', 'd2', 'val'])
df2 = pd.read_csv(file2, sep='\t', names=['pid','sig', 'd1', 'd2', 'val'])
mrg = df1.merge(df1, on='pid', how='left')
print(mrg)