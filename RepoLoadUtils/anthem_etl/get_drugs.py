#!/home/ubuntu/anaconda3/bin/python
from DB import DB
from common import *
from config import Config
import os, argparse
import pandas as pd

def fill_df(df, batch, file_writter, ndc_set, id2nr, sig_name, date_col_name, select_cols):
    max_file_lines=10000000
    col_names=list(df.df.columns)
    lines = list(map(lambda r: [ r[0], fix_date(r[1]), 'NDC:' + r[2], float(r[3]), float(r[4]) ] , batch))
    d=pd.DataFrame(lines, columns=col_names)
    #print(d.head())
    df.df=df.df.append(d, ignore_index=True)
    ndc_set.df=ndc_set.df.append(d['ndc'], ignore_index=True)
    #print(df.head())
    #check if too big and need to clear buffer:
    if len(df.df.index) > max_file_lines:
        #join to find pid and convert them, sort by pid, time:
        full_res=join_pid_map(df.df, id2nr, sig_name, date_col_name, select_cols)
        #save file
        full_res.to_csv(file_writter.getPath(),sep='\t', index=False, header=False)
        df.df=pd.DataFrame(columns=col_names)
        file_writter.next()

SIG_NAME='Drug'
parser = argparse.ArgumentParser(description='Create Drugs flat file and dict for loading repository')
parser.add_argument('id2nr',help='id2nr file path')

args = parser.parse_args()

cfg=Config()
fpath=os.path.join(cfg.output_before_load, 'Drugs_data')
ndc_dict=os.path.join(cfg.output_before_load, 'dicts', 'dict.ndc_defs')
file_w=FileWriter(fpath)
id2nr=read_id2nr(args.id2nr)
id2nr.set_index('pid', inplace=True)

db=DB()
db.open()
sql="""
SELECT membernumberhci,filldate,  ndc,
       dayssupply,
       quantitydispensed
FROM "5e7cff5094fe29000a4e40eb"."5e7cff5094fe29000a4e40eb".pk_us_516_o_kj9fj1q4w4nf_anthem_datascience_poc0_pharmacy_sample_3years
"""
#limit 100000 - add this in the end of query for quick test

db.execute(sql)

df=pd.DataFrame(columns=['pid', 'date', 'ndc', 'days_supply', 'quantity_dispensed'])
df_w=DF_Wrapper(df)
ndc_set=pd.DataFrame(columns=['ndc'])
ndc_set_w=DF_Wrapper(ndc_set['ndc']) #holds series
date_col_name='date'
cols_after_join=['target_pid', 'SIG_NAME', 'date', 'ndc', 'days_supply', 'quantity_dispensed']

db.process_all_batch(lambda b : fill_df(df_w, b, file_w, ndc_set_w, id2nr, SIG_NAME,  date_col_name, cols_after_join) , 1000000, True)
if len(df_w.df.index) > 0:
    full_res=join_pid_map(df_w.df, id2nr, SIG_NAME, date_col_name, cols_after_join)
    full_res.to_csv(file_w.getPath(True),sep='\t', index=False, header=False)

#use ndc_set_w to define NDC dict:
write_dict(ndc_set_w.df, ndc_dict, SIG_NAME)

db.close()
print('Done')

