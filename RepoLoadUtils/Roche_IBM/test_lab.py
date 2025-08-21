import pandas as pd
pids=[13252320]
pids_df=pd.DataFrame({'pid':pids})
data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'loinc_test_id', 'loinc_category_id', 'std_uom', 'std_value', 'std_value_txt', 'std_report_status', 'code1', 'encounter_join_id', 'encounter_record_id_hash', 'observation_date', 'std_observation_high_ref', 'std_observation_low_ref']

df=pd.read_csv('/mnt/s3mnt_pt/v_observation.csv.v_db1_node0001.gz',compression='gzip', sep='|', header=None, index_col=False, names=data_headers)

filt=df[df['pid'].isin(pids)].reset_index(drop=True)

loinc=['20509-6','55782-7','59260-0','717-9','718-7','30350-3']

filt[(filt['observation_date'].str.startswith('2015-03-28')) & (filt['loinc_test_id'].isin(loinc))][['std_value', 'rowid', 'code1', 'observation_date']].sort_values(['observation_date']).drop_duplicates().reset_index(drop=True)
