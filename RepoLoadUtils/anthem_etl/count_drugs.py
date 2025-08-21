import pandas as pd
import os
from Configuration import Configuration


def get_vc(cfg):
    out_folder = os.path.join(cfg.work_path, 'FinalSignals')
    all_vc = pd.Series()
    for i in range(0, 39):
        file1 = os.path.join(out_folder, 'Drug'+str(i))
        print('Reading file ' + file1)
        df1 = pd.read_csv(file1, sep='\t', names=['pid', 'v1'], usecols=[0, 3])
        vc = df1['v1'].value_counts()
        all_vc = all_vc.add(vc, fill_value=0)
    all_vc.sort_values(ascending=False, inplace=True)
    all_vc.to_csv('/home/LinuxDswUser/work/anthem_load/temp/drug_counts.csv')


if __name__ == '__main__':
    cfg = Configuration()
    out_folder = os.path.join(cfg.work_path, 'FinalSignals')
    temp_folder = os.path.join(cfg.work_path, 'temp')
    vc_file = os.path.join(temp_folder, 'drug_counts.csv')
    if os.path.exists(vc_file):
        vc = pd.read_csv(vc_file, names=['ndc', 'count'])
    else:
        vc = get_vc(cfg)
        vc.to_csv(vc_file)
    dict_path = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    ndc_map = pd.read_csv(os.path.join(dict_path, 'dict.ndc_set'), sep='\t', skiprows=1, names=['ndc_code', 'ndc'], usecols=[1, 2])
    mrg = vc.merge(ndc_map, on='ndc', how='left')
    match = mrg[mrg['ndc_code'].notnull()]
    not_math = mrg[mrg['ndc_code'].isnull()]

    print('Number of Drugs : ' + str(mrg['count'].sum()))
    print('Number of unique codes: ' + str(vc.shape[0]))
    print('merge shape: ' + str(mrg.shape[0]))
    print('Matched  unique codes: ' + str(match.shape[0]))
    print('Matched  total drugs: ' + str(match['count'].sum()))
    print('not Matched  unique codes: ' + str(not_math.shape[0]))
    print('not Matched  total drugs: ' + str(not_math['count'].sum()))
    print(not_math[0:20])

    atc_map = pd.read_csv(os.path.join(dict_path, 'dict.atc_ndc_set'), sep='\t', skiprows=1, names=['atc', 'ndc_code'], usecols=[1, 2])
    atc_mrg = match.merge(atc_map, on='ndc_code', how='left')
    atc_mrg.drop_duplicates('ndc', inplace=True)
    atc_match = atc_mrg[atc_mrg['atc'].notnull()]
    atc_not_math = atc_mrg[atc_mrg['atc'].isnull()]
    print(' ATC match')
    print('Number of unique codes: ' + str(match.shape[0]))
    print('merge shape: ' + str(atc_mrg.shape[0]))
    print('Matched  unique codes: ' + str(atc_match.shape[0]))
    print('Matched  total drugs: ' + str(atc_match['count'].sum()))
    print('not Matched  unique codes: ' + str(atc_not_math.shape[0]))
    print('not Matched  total drugs: ' + str(atc_not_math['count'].sum()))
    print(atc_not_math[0:20])


