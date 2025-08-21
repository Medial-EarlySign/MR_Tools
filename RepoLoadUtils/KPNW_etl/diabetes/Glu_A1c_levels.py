import sys
import os
import numpy as np
import pandas as pd
from utils import fixOS, read_first_line, get_dict_set_df
# sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from get_funcs import get_sig_df, find_sickle_cell


SOURCE = 'files'
#SOURCE = 'rep'

if SOURCE == 'rep':
    import medpython as med


if __name__ == '__main__':
    kp_rep = fixOS('/home/Repositories/KPNW/kpnw_jun19/kpnw.repository')
    kp_diab_rep = fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/kpnw.repository')
    sigs_files_path = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\temp\\')

    if SOURCE == 'rep':
        rep = med.PidRepository()
        rep.read_all(kp_rep, [], [])
        print(med.cerr())
    else:
        rep = None

    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    glu_df = get_sig_df('Glucose', rep, sigs_files_path)
    tests_df = glu_df.merge(a1c_df, on='pid')
    #tests_df['diff_days'] = pd.to_datetime(tests_df['date_x'], format='%Y%m%d') - pd.to_datetime(tests_df['date_y'], format='%Y%m%d')
    #tests_df['diff_days'] = tests_df['diff_days'].dt.days.abs()
    #grp = tests_df.sort_values(by=['pid', 'diff_days']).drop_duplicates(subset=['pid', 'date_x'], keep='first')
    #grp = grp[grp['diff_days'] < 10]
    grp = tests_df[tests_df['date_x']==tests_df['date_y']]
    race_df = get_sig_df('RACE', rep, sigs_files_path)
    grp = grp.merge(race_df, on='pid', how='left')
    grp.to_csv(os.path.join(sigs_files_path, 'glu_vs_a1c.csv'), index=False)
    scl_df = find_sickle_cell(rep, sigs_files_path)
    grp1 = grp.merge(scl_df, on='pid')
    grp1.to_csv(os.path.join(sigs_files_path, 'glu_vs_a1c_scl.csv'), index=False)
