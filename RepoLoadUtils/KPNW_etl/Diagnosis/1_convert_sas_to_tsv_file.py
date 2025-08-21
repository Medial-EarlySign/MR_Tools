#!/opt/medial/dist/usr/bin/python
import os
import sys, datetime
import pandas as pd

#full_file = sys.argv[1]
full_file = '/server/Data/NWP/DeltaNov20/medial_flu_diagnosis.sas7bdat'
output = '/nas1/Work/Users/Tamar/kpnw_load/data/medial_flu_diagnosis_3.tsv'

fp = open(output, 'w')
fp.close() #erase file

all_df = pd.DataFrame()
print_head = False
last_prt = datetime.datetime.now()
start_prt = last_prt
min_prt_sec = 60
for i,kp_diagnosis in enumerate(pd.read_sas(full_file, chunksize=500000, iterator=True, encoding='latin-1')):
    kp_diagnosis.to_csv(output, sep='\t', mode='a', header = not(print_head))
    if not(print_head):
        print(kp_diagnosis.head())
        print_head = True
    diff = (datetime.datetime.now() - last_prt)
    if (diff.seconds + diff.days * 24 * 3600 > min_prt_sec):
        last_prt = datetime.datetime.now()
        tm_took = last_prt - start_prt
        print('In %d - Took %2.1f Minutes till now'%(i + 1, (tm_took.days* 24 * 3600.0 + tm_took.seconds)/60.0))
print('DONE')