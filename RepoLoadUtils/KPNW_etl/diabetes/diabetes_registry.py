import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'Registries', 'diabetes_python'))
from Configuration import Configuration
from utils import fixOS, write_tsv, read_first_line, get_dict_set_df
from diabetes_reg import get_all_diabetes_reg, fix_start_end, prep_ranges
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


def get_diab_df(cfg, kp_rep, sig, reg_list_file):
    diab_df = pd.read_csv(reg_list_file,sep='\t', usecols=[0], names=['code'])
    diab_df = diab_df[~diab_df['code'].str.startswith('#')]
    sig_df = kp_rep.get_sig(sig, translate=False)
    full_dict = get_dict_set_df(fixOS(cfg.repo_folder), sig)
    diab_dict = full_dict[full_dict['desc'].isin(diab_df['code'].unique().tolist())]

    diab_codes = diab_dict['codeid'].astype(float).unique().tolist()
    sig_df = sig_df[sig_df['val'].isin(diab_codes)]
    return sig_df


if __name__ == '__main__':
    #diab_drugs = sys.argv[1]
    diab_drugs = '/nas1/UsersData/tamard/MR/Tools/Registries/Lists/diabetes_drug_codes.MHS.full'
    #diab_diag = sys.argv[2]
    diab_diag = '/nas1/UsersData/tamard/MR/Tools/Registries/Lists/diabetes_ICD.fulll'
    #res_path = sys.argv[3]
    res_path = '/nas1/Work/AlgoMarkers/Pre2D/kpnw'
    #res_file_name = sys.argv[4]
    res_file_name = 'diabetes.DM_Registry'

    cfg = Configuration()
    kp_rep = med.PidRepository()
    signals = ['Glucose', 'HbA1C', 'Drug', 'DIAGNOSIS', 'MEMBERSHIP']
    kp_rep.read_all(fixOS(cfg.repo), [], signals)

    all_events_file = os.path.join(fixOS(res_path), 'pre2d.allevents')
    final_file = os.path.join(fixOS(res_path), res_file_name)
    cols = ['pid', 'sig', 'start_date', 'end_date', 'level']
    if os.path.exists(all_events_file):
        print('reading events file')
        events_df = pd.read_csv(all_events_file, sep='\t', names=cols)
    else:
        glu_df = kp_rep.get_sig('Glucose')
        hba_df = kp_rep.get_sig('HbA1C')

        drug_df = get_diab_df(cfg, kp_rep, 'Drug', diab_drugs)
        diag_df = get_diab_df(cfg, kp_rep, 'DIAGNOSIS', diab_diag)
        events_df = get_all_diabetes_reg(glu_df, hba_df, drug_df, diag_df)

    ranges_df = prep_ranges(events_df)
    ranges_df['sig'] = 'DM_Registry'
    print('Writing to ' + all_events_file)
    ranges_df[cols].to_csv(all_events_file, sep='\t', index=False)

    mem_df = kp_rep.get_sig('MEMBERSHIP', translate=False)
    start_df = mem_df[['pid', 'date_start']].copy()
    start_df.sort_values(by=['pid', 'date_start'], inplace=True)
    start_df.drop_duplicates(subset='pid', keep='first', inplace=True)

    end_df = mem_df[['pid', 'date_end']].copy()
    end_df.sort_values(by=['pid', 'date_end'], inplace=True)
    end_df.drop_duplicates(subset='pid', keep='last', inplace=True)
    end_df.loc[end_df['date_end'] > 20200000, 'date_end'] = 20190601

    ranges_df = fix_start_end(ranges_df, start_df, 'date_start', end_df, 'date_end')
    print(ranges_df)
    ranges_df[cols].to_csv(final_file, sep='\t', index=False, header=False)
