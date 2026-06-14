import pandas as pd
import os, re
from ETL_Infra.data_fetcher.files_fetcher import files_fetcher, list_directory_files

def list_files(file_prefix):
    base_path='/nas1/Data/Roche_Denmark/Roche/Population2'
    return list_directory_files(base_path, file_prefix)

def labs_file_parser(filepath):
    df = pd.read_csv(filepath, names= ['pid', 'index_date', 'lab_date', 'lab_name', 'value_0', 'lab_name_unfiltered'] )
    df['signal'] = df['lab_name'] + '::' + df['lab_name_unfiltered']
    df.loc[df['signal'].isnull(), 'signal']= df['lab_name_unfiltered']
    return df

def labs_data_fetcher(batch_size, start_batch):
    #files = list_files('pop2_datasetC_labresults_firstvisit_for_all')
    files = list_files('pop2_datasetB_labresults_firstvisit_for_controls_LCdate_for_cases')
    return files_fetcher(files, batch_size, labs_file_parser, start_batch)

def generic_file_fetcher(file_pattern):
    file_fetcher_function = lambda batch_size, start_batch :\
           files_fetcher(list_files(file_pattern), batch_size, lambda file_path: \
                         pd.read_csv(file_path, encoding='unicode_escape').rename(columns = {'cpr_hash':'pid'}) , start_batch)
    return file_fetcher_function
