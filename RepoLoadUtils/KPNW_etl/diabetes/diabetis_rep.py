import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv, read_first_line
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


def filter_adm(adm_df, sig_df):
    cols = sig_df.columns.tolist()
    filtered_df = sig_df.merge(adm_df, how='left', on='pid', suffixes=["", "_adm"])
    to_filter = filtered_df.loc[(filtered_df['date'] >= filtered_df['date_start']) &
                                (filtered_df['date'] <= filtered_df['date_end'])]

    filtered_df = pd.merge(sig_df, to_filter, how='left', on=cols)

    filtered_df = filtered_df[filtered_df['date_start'].isnull()]
    print(' Total ' + str(sig_df.shape[0]) + ', to filter = ' + str(to_filter.shape[0]) + ', After filtering =' + str(filtered_df.shape[0]))
    return filtered_df[cols]


def save_filttered(sig, filtered_df, out_folder):
    cols = sig_df.columns.tolist()
    if str(filtered_df['val'].dtype) == 'category':
        print('"val" is category signal')
        filtered_df['val'] = filtered_df['val'].apply(lambda x: x.split('|')[0])
    if 'val2' in filtered_df.columns:
        if str(filtered_df['val2'].dtype) == 'category':
            print('"val2" is category signal')
            filtered_df['val2'] = filtered_df['val2'].apply(lambda x: x.split('|')[0])

    cols.insert(1, 'signal')
    filtered_df['signal'] = sig
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    print('Saving laoding file for ' + sig)
    write_tsv(filtered_df[cols], out_folder, sig)


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    #signals = ['DIAGNOSIS', 'GENDER', 'HDL', 'BYEAR', 'ALT', 'Triglycerides', 'Weight', 'MEMBERSHIP',
    #           'WBC', 'HbA1C', 'BMI', 'Drug', 'Glucose', 'ADMISSION', 'STARTDATE', 'ENDDATE', 'TRAIN', 'DEATH']

    to_filter = ['HDL',  'ALT', 'Triglycerides', 'WBC', 'HbA1C', 'BMI', 'Drug', 'Glucose', 'Weight']
    to_copy = ['DIAGNOSIS', 'GENDER', 'BYEAR', 'ADMISSION', 'STARTDATE', 'ENDDATE', 'TRAIN', 'BDATE', 'DEATH', 'RACE', 'MEMBERSHIP']
    to_filter = []
    to_copy = ['RACE']
    signals = to_filter + to_copy
    work_folder = '/nas1/Work/Users/Tamar/kpnw_diabetes_load'
    out_folder = os.path.join(work_folder, 'FinalSignals')
    kp_rep = fixOS(cfg.repo)
    rep.read_all(kp_rep, [], signals)

    adm_sig = rep.get_sig('ADMISSION')
    for signal in to_filter:
        sig_df = rep.get_sig(signal)
        print(signal)
        print(sig_df.head(10))
        filtered = filter_adm(adm_sig, sig_df)
        #print(filtered)
        save_filttered(signal, filtered, out_folder)

    for signal in to_copy:
        sig_df = rep.get_sig(signal)
        print(signal)
        save_filttered(signal, sig_df, out_folder)
