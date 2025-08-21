import os
import sys
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import write_tsv, fixOS
from unit_converts import round_ser
from Configuration import Configuration
import medpython as med


def get_eGFR_CKD_EPI(rep, out_folder):
    by_df = rep.get_sig('BYEAR')
    by_df.rename(columns={'val0': 'byear'}, inplace=True)

    gender_df = rep.get_sig('GENDER')
    gender_df.rename(columns={'val0': 'gender'}, inplace=True)

    creat_df = rep.get_sig('Creatinine')
    creat_df.rename(columns={'val0': 'creatinine'}, inplace=True)

    sig_df = gender_df.merge(by_df, on='pid')
    sig_df = creat_df.merge(sig_df, on='pid', how='left')

    sig_df.loc[:, 'age'] = (sig_df['time0'] / 10000).astype(int) - sig_df['byear']

    sig_df.loc[:, 'eGFR_CKD_EPI'] = sig_df['age'].apply(lambda x: pow(0.993, x))

    sig_df.loc[sig_df['gender'] == 'M', 'base_mult'] = 141
    sig_df.loc[sig_df['gender'] == 'F', 'base_mult'] = 144
    sig_df.loc[(sig_df['gender'] == 'M') &
               (sig_df['creatinine'] <= 0.9) &
               (sig_df['creatinine'] != 0), 'pow'] = (sig_df['creatinine'] / 0.9).pow(-0.441)
    sig_df.loc[(sig_df['gender'] == 'M') &
               (sig_df['creatinine'] > 0.9), 'pow'] = (sig_df['creatinine'] / 0.9).pow(-1.209)

    sig_df.loc[(sig_df['gender'] == 'F') &
               (sig_df['creatinine'] <= 0.7) &
               (sig_df['creatinine'] != 0), 'pow'] = (sig_df['creatinine'] / 0.7).pow(-0.329)
    sig_df.loc[(sig_df['gender'] == 'F') &
               (sig_df['creatinine'] > 0.7), 'pow'] = (sig_df['creatinine'] / 0.7).pow(-1.209)
    sig_df.loc[:, 'eGFR_CKD_EPI'] = sig_df['eGFR_CKD_EPI'] * sig_df['base_mult'] * sig_df['pow']
    sig_df = sig_df[sig_df['eGFR_CKD_EPI'].notnull()]
    sig_df['rnd'] = 0.1
    sig_df['eGFR_CKD_EPI'] = round_ser(sig_df['eGFR_CKD_EPI'], sig_df['rnd'])
    sig_df['sig'] = 'eGFR_CKD_EPI'
    sig_df.sort_values(['pid', 'time0'], inplace=True)
    write_tsv(sig_df[['pid', 'sig', 'time0', 'eGFR_CKD_EPI']], out_folder,  'eGFR_CKD_EPI', mode='w')


def get_eGFR_MDRD(rep, out_folder):
    by_df = rep.get_sig('BYEAR')
    by_df.rename(columns={'val0': 'byear'}, inplace=True)

    gender_df = rep.get_sig('GENDER')
    gender_df.rename(columns={'val0': 'gender'}, inplace=True)

    creat_df = rep.get_sig('Creatinine')
    creat_df.rename(columns={'val0': 'creatinine'}, inplace=True)

    sig_df = gender_df.merge(by_df, on='pid')
    sig_df = creat_df.merge(sig_df, on='pid', how='left')
    sig_df.loc[:, 'age'] = (sig_df['time0'] / 10000).astype(int) - sig_df['byear']

    sig_df.loc[:,  'eGFR_MDRD'] = sig_df['creatinine'].pow(-1.154) * sig_df['age'].pow(-0.203)
    sig_df.loc[sig_df['gender'] == 'F', 'eGFR_MDRD'] = sig_df['eGFR_MDRD'] * 0.742
    sig_df.loc[(sig_df['age'] <= 1) | (sig_df['creatinine'] <= 0.1), 'eGFR_MDRD'] = -1
    sig_df['rnd'] = 0.01
    sig_df['eGFR_MDRD'] = round_ser(sig_df['eGFR_MDRD'], sig_df['rnd'])
    sig_df['sig'] = 'eGFR_MDRD'
    sig_df.sort_values(['pid', 'time0'], inplace=True)
    write_tsv(sig_df[['pid', 'sig', 'time0', 'eGFR_MDRD']], out_folder, 'eGFR_MDRD', mode='w')


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    rep.read_all(cfg.repo, [], ['GENDER'])
    out_folder = os.path.join(fixOS(cfg.work_path), 'FinalSignals')

    get_eGFR_CKD_EPI(rep, out_folder)
    #get_eGFR_MDRD(rep, out_folder)
