import pandas as pd
import os, re, sys
sys.path.insert(0, os.environ['ETL_LIB_PATH'])
from data_fetcher.files_fetcher import big_files_fetcher, files_fetcher, list_directory_files

def get_translation_dict():
    translation_dict = {}
    translation_dict['JAN'] = 1
    translation_dict['FEB'] = 2
    translation_dict['MAR'] = 3
    translation_dict['APR'] = 4
    translation_dict['MAY'] = 5
    translation_dict['JUN'] = 6
    translation_dict['JUL'] = 7
    translation_dict['AUG'] = 8
    translation_dict['SEP'] = 9
    translation_dict['OCT'] = 10
    translation_dict['NOV'] = 11
    translation_dict['DEC'] = 12
    return translation_dict
translation_dict=get_translation_dict()

def fix_date(s):
    tokens=s.split('-')
    if len(tokens)!=3:
        return s
    month='%02d'%(translation_dict[tokens[1].upper()]) if tokens[1].upper() in translation_dict else token[1]
    return int(tokens[0]+month+tokens[2])

def read_file(file_p, add_file_name=False):
    df = pd.read_csv(file_p, sep='\t', encoding_errors='replace', low_memory=False)
    df=df.rename(columns={'Input': 'Signal'})
    used_cols= ['ID', 'Signal', 'Date', 'Value', 'Unit']
    df=df[used_cols]
    df=df.rename(columns={'ID':'pid', 'Signal': 'signal', 'Date': 'time_0', 'Value': 'value_0', 'Unit': 'unit'})
    df.loc[df['time_0'].notnull(),'time_0']=df.loc[df['time_0'].notnull(),'time_0'].astype(str).apply(fix_date)
    if add_file_name: #add filename if there are multiple files - to debug problems
        df['FILENAME']=file_p
    return df

def read_file_iterator(file_p, batch_size, start_from_row):
    used_cols= ['ID', 'Signal', 'Date', 'Value', 'Unit']
    if batch_size > 0:
        df_i=pd.read_csv(file_p, sep='\t', encoding_errors='replace', skiprows=start_from_row, chunksize=batch_size, low_memory=False)
    else:
        df_i=[pd.read_csv(file_p, sep='\t', encoding_errors='replace', skiprows=start_from_row, low_memory=False)]
    for df in df_i:
        df=df[used_cols]
        df=df.rename(columns={'ID':'pid', 'Signal': 'signal', 'Date': 'time_0', 'Value': 'value_0', 'Unit': 'unit'})
        df.loc[df['time_0'].notnull(),'time_0']=df.loc[df['time_0'].notnull(),'time_0'].astype(str).apply(fix_date)
        #df['FILENAME']=file_p
        yield df

def data_fetcher_file_api(base_path, file_regex='.*', batch_file_rows=False):
    files = list_directory_files(base_path, file_regex)
    if len(files)==0:
        raise NameError(f'Can\'t find files to match pattern {file_regex}')
    #Do lazy:
    if not(batch_file_rows):
        return lambda bt_size,start_r: files_fetcher(files, bt_size, lambda file_path: read_file(file_path, len(files)>1),start_r)
    else:
        return lambda bt_size,start_r: big_files_fetcher(files, bt_size, read_file_iterator, has_header=True,start_batch=start_r)
