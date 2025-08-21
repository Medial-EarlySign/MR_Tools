#!/usr/bin/python
from basic_loader import read_table_united, read_column_united
from Configuration import Configuration
import os, sys
import pandas as pd
from datetime import datetime
from load_data import *

def load_test(cfg):
    #data_headers=['pid', 'source', 'status', 'pid2', 'update_date', 'code1', 'byear', 'sex', 'state', 'payer', 'code2', 'other', 'other2']
    #res=read_table_united(cfg.data_dir, 'v_demographic', columns = data_headers, process_function=process_demo)

    #data_headers=['pid', 'source', 'status', 'rowid', 'update_date', 'answer', 'id2', 'id3', 'date']
    #res=read_table_united(cfg.data_dir, 'v_habit', columns = data_headers, process_function=lambda data: data[['pid', 'id2', 'id3', 'rowid', 'source', 'status', 'answer', 'date', 'update_date']].drop_duplicates())
    #res=res[res['answer'].notnull()].reset_index(drop=True)
    #res.answer = res.answer.map(lambda x: 'tobacco_passive:no' if x=='tobacco_passive_no' else x )
    #res[['signal','value']] = res.answer.str.split("_", expand=True)

    #res.signal = res.signal.map( {'tobacco': 'SMOKING_STATUS', 'alcohol': 'ALCOHOL_STATUS'} )
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'loinc_test_id', 'loinc_category_id', 'std_uom', 'std_value', 'std_value_txt', 'std_report_status', 'code1', 'encounter_join_id', 'encounter_record_id_hash', 'observation_date', 'std_observation_high_ref', 'std_observation_low_ref']
    #res=read_table_united(cfg.data_dir, 'v_observation', columns = data_headers, process_function=lambda data: data[['pid', 'observation_date', 'update_date', 'loinc_test_id', 'loinc_category_id', 'std_uom', 'std_value', 'std_value_txt', 'std_report_status']].drop_duplicates())
    #res=read_table_united(cfg.data_dir, 'v_observation', columns = data_headers, process_function=lambda data: data[['loinc_test_id', 'loinc_category_id']].drop_duplicates())
    data=read_column_united(cfg.data_dir, 'v_observation', columns = data_headers, cols=['loinc_test_id'])


    return data


def process_demo(data):
    #print(data.head())
    #preprocess data
    #end preprocess
    return data[['pid', 'sex', 'byear', 'source', 'update_date', 'status']].drop_duplicates()


cfg=Configuration()
data=load_test(cfg)
#data['cnt']=1
data.to_csv('/mnt/work/LOINC_CNTs.tsv', sep='\t', index=False)
data[['loinc_test_id', 'cnt']].groupby('loinc_test_id').sum().reset_index().sort_values('cnt', ascending=False).to_csv('/mnt/work/LOINC_CNT.sorted.tsv', sep='\t', index=False)
#data.groupby('loinc_test_id').count().reset_index().sort_values('cnt', ascending=False).to_csv('/mnt/work/LOINC_CNTs.tsv', sep='\t', index=False)
#data=read_sig_from_pre(cfg,'Hemoglobin')
