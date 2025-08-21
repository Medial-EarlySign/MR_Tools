#!/nas1/Work/python-env/python38/bin/python
import os
import sys, datetime
import pandas as pd

def handle_file(dir_out, file_path):
    all_df = pd.DataFrame()
    print_head = False
    last_prt = datetime.datetime.now()
    start_prt = last_prt
    min_prt_sec = 60
    output = os.path.join(dir_out, os.path.basename(file_path).replace('.sas7bdat','.tsv'))
    if os.path.exists(output):
        print('Output file "%s" exists'%(output))
        override=input('Override %s? Y/N:'%(output)).upper()
        if not(override == 'Y' or override == 'YES'):
            return 
    fp = open(output, 'w')
    fp.close() #erase file
    print('START %s'%file_path)
    for i,kp_diagnosis in enumerate(pd.read_sas(file_path, chunksize=500000, iterator=True, encoding='latin-1')):
        kp_diagnosis.to_csv(output, sep='\t', mode='a', header = not(print_head))
        if not(print_head):
            print('\n'.join(kp_diagnosis.columns.values.tolist()))
            print(kp_diagnosis.head())
            print_head = True
        diff = (datetime.datetime.now() - last_prt)
        if (diff.seconds + diff.days * 24 * 3600 > min_prt_sec):
            last_prt = datetime.datetime.now()
            tm_took = last_prt - start_prt
            print('In %d - Took %2.1f Minutes till now'%(i + 1, (tm_took.days* 24 * 3600.0 + tm_took.seconds)/60.0))
    print('DONE %s'%file_path)

full_files = ['/home/Work/Biotronik/July_22_2021_Data_Transfer_1/iegm_raw_data_1.sas7bdat',
              '/home/Work/Biotronik/July_22_2021_Data_Transfer_1/iegm_raw_data_2.sas7bdat',
              '/home/Work/Biotronik/July_22_2021_Data_Transfer_2/iegm_raw_data_3.sas7bdat',
              '/home/Work/Biotronik/July_22_2021_Data_Transfer_2/hm_tachy_episode.sas7bdat']
output_dir = '/nas1/Work/Mayo_Biotronic_Load/July_22_2021_Data_Transfer'

for file_path in full_files:
    handle_file(output_dir, file_path)