import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS, read_tsv, is_nan, eprint

if __name__ == '__main__':
    cfg = Configuration()
    raw_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    table_path = os.path.join(out_folder, 'raw_tables')

    unit_sum_file = os.path.join(out_folder, 'med_unit_summary.csv')
    if not os.path.exists(unit_sum_file):
        event_type = 'ev_medications_administered'
        print('Reading table for ' + event_type)
        raw_table = pd.read_csv(os.path.join(table_path, event_type), sep='\t')
        units_comp_df = pd.DataFrame()
        for med_un, df1 in raw_table.groupby(['medicationcode', 'quantitiy_unitcodeHier']):
            #if df1.shape[0] <= 5:
            #    continue
            dict1 = {'medication_code': med_un[0], 'medication': df1.iloc[0]['medicationcodeHier'], 'unit': med_un[1]}
            ser1 = pd.to_numeric(df1['quantity_value'], errors='coerce')
            desc = ser1.describe()
            desc = desc.append(pd.Series(dict1))
            units_comp_df = units_comp_df.append(desc, ignore_index=True)
        units_comp_df = units_comp_df[units_comp_df['medication'].duplicated(keep=False)]
        cols = ['medication_code', 'medication', 'unit', 'count', '25%', '50%', '75%', 'max', 'mean', 'min', 'std']
        units_comp_df[cols].to_csv(unit_sum_file)
    else:
        units_comp_df = pd.read_csv(unit_sum_file)

    prob_df = pd.DataFrame()
    for med, units_df in units_comp_df.groupby('medication_code'):
        if units_df.shape[0] == 1:
            print(units_df.iloc[0]['medication'] + ' has only one unit')
            continue
        units_df.sort_values(by='count', ascending=False, inplace=True)
        to_comp = units_df.iloc[0]
        prob_df = prob_df.append(to_comp)
        for i, r in units_df.iterrows():
            if r['50%'] != to_comp['50%']:
                prob_df = prob_df.append(r)
    cols = ['medication_code', 'medication','unit', '25%','50%','75%','count','max','mean','min','std']

    prob_df[cols].to_csv(os.path.join(out_folder, 'unit_diffs.csv'))
