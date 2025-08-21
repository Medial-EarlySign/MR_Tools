import os
import re
import traceback
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv
from load_patient import get_id2nr_map


if __name__ == '__main__':
    pid = 5541221
    date = 19870000
    id2nr = get_id2nr_map()
    comb_id = id2nr[id2nr == pid].index[0]
    prac = comb_id[:5]
    pid = comb_id[-4:]
    # medcodes = ['451E.00', '451G.00', '451N.00']
    # ahdcodes = [1005010100]

    raw_source_path_old = 'T:\\THIN1801\\THINDB1801\\'
    raw_source_path_new ='T:\\THIN1701\\THINDB1701\\'

    file_name = 'ahd.' + prac

    ahd_df_old = read_fwf('ahd', raw_source_path_old, file_name)
    ahd_df_new = read_fwf('ahd', raw_source_path_new, file_name)

    pid_old = ahd_df_old[(ahd_df_old['patid'] == pid) & (ahd_df_old['eventdate'] == date)]  # & (ahd_df_old['ahdcode'].isin(ahdcodes))]
    pid_new = ahd_df_new[(ahd_df_new['patid'] == pid) & (ahd_df_new['eventdate'] == date)]  # & (ahd_df_new['ahdcode'].isin(ahdcodes))]

    print(pid + ' old data points = ' + str(pid_old.shape[0]))
    print(pid + ' new data points = ' + str(pid_new.shape[0]))

    cols = ['patid', 'ahdcode', 'medcode', 'eventdate', 'data1']  # , 'data2', 'data3']
    print(pid_old[cols].sort_values(by='medcode'))
    print(pid_new[cols].sort_values(by='medcode'))
