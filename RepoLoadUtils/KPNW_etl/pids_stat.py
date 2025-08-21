import pandas as pd
import os
import sys
from Configuration import Configuration
from utils import fixOS

if __name__ == '__main__':
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    counts_file = 'kp_pids_counts.csv'
    counts_df = pd.read_csv(os.path.join(work_folder, counts_file))
    counts_df.set_index('pid', inplace=True)

    kpnw_map = pd.read_csv(os.path.join(code_folder, 'kp_signal_map.csv'), sep='\t')
    demog = ['active', 'days', 'TRAIN', 'GENDER', 'BYEAR', 'BDATE', 'DEATH', 'ETHNICITY', 'RACE', 'ZIP3', 'OCCUPATION', 'DEAD', 'MEMBERSHIP']
    demo_sigs = kpnw_map[kpnw_map['source'] == 'medial_flu_pat']['signal'].unique().tolist()
    behav_sigs = kpnw_map[kpnw_map['source'] == 'medial_flu_behav_char']['signal'].unique().tolist()
    labs_sigs = kpnw_map[kpnw_map['source'].str.contains('kpnwlabs')]['signal'].unique().tolist()
    vit_sigs = kpnw_map[kpnw_map['source'].str.contains('kpnwvitals')]['signal'].unique().tolist()
    cat_sigs = ['DIAGNOSIS', 'Vaccination', 'ADMISSION', 'VISIT', 'Drug']
    counts_df = counts_df[counts_df['active'].notnull()]
    tot_df = counts_df[['active', 'days', 'DIAGNOSIS', 'Vaccination', 'ADMISSION', 'VISIT', 'Drug']].copy()
    tot_df['total_demo'] = counts_df[demo_sigs].sum(axis=1)
    tot_df['total_behav'] = counts_df[behav_sigs].sum(axis=1)
    tot_df['total_labs'] = counts_df[labs_sigs].sum(axis=1)
    tot_df['total_vit'] = counts_df[vit_sigs].sum(axis=1)
    all_cols = counts_df.columns.tolist()
    cols = [x for x in all_cols if x not in demog]
    tot_df['total'] = counts_df[cols].sum(axis=1)
    tot_df.to_csv(os.path.join(work_folder, 'totals_by_pid.csv'))
    print(tot_df)
