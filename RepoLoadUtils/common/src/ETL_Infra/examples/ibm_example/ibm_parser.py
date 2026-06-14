import pandas as pd
import os, gzip
from ETL_Infra.data_fetcher.files_fetcher import files_fetcher, list_directory_files

def ibm_parser_diagnosis(batch_size, start_batch):
    files = list_ibm_files('^v_diagnosis')
    columns=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'diagnosis_code', 'icd_code', 'icd_version', 'encounter_join_id', 'encounter_join_hash', 'diagnosis_date', 
            'is_principal', 'is_admitting', 'is_reason_for_visit', 'status', 'claim_type', 'snomed_join_id']
    minimal_take_cols=['pid', 'diagnosis_date', 'icd_code', 'icd_version']
    return files_fetcher(files, batch_size, lambda f: ibm_file_parser(f, columns, minimal_take_cols)  , start_batch)

def ibm_file_parser(f, columns, minimal_take_cols = None):
    if minimal_take_cols is not None:
        return pd.read_csv(f, compression='gzip', sep='|', header=None, index_col=False, names=columns, usecols=minimal_take_cols)
    else:
        return pd.read_csv(f, compression='gzip', sep='|', header=None, index_col=False, names=columns)

def list_ibm_files(file_prefix):
    base_path='/mnt/s3mnt_pt'
    return list_directory_files(base_path, file_prefix)
