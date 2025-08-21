import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces
from train_signal import create_train_signal
from staging_config import MimicLabs, MimicDemographic, StageConfig
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files
from elixhauser_defines import elixhauser_drg, elixhauser_icd9
from sql_utils import get_sql_engine


def prescriptions_to_file(cfg):
    sig = 'DRUG_PRESCRIPTION'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    drug_df = pd.read_csv(os.path.join(raw_path, 'PRESCRIPTIONS.csv'), encoding='utf-8', na_filter=False)
    drug_df['medialid'] = drug_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    drug_df = drug_df[(drug_df['DRUG'].notnull()) & (drug_df['DRUG'].str.strip() != '')]
    drug_df = drug_df[(drug_df['STARTDATE'].str.strip() != '') & (drug_df['ENDDATE'].str.strip() != '')]
    # cases where strat<end replace start and end
    cond = drug_df['STARTDATE'] > drug_df['ENDDATE']
    drug_df.loc[cond, 'temp'] = drug_df[cond]['STARTDATE']
    drug_df.loc[cond, 'STARTDATE'] = drug_df[cond]['ENDDATE']
    drug_df.loc[cond, 'ENDDATE'] = drug_df[cond]['temp']
    ####
    drug_df.loc[drug_df['ROUTE'].str.strip() == '', 'ROUTE'] = 'UNKNOWN'
    drug_df.loc[:, 'ROUTE'] = 'ROUTE:' + replace_spaces(drug_df['ROUTE'])
    drug_df.loc[:, 'DRUG_NAME'] = 'DRUG:' + replace_spaces(drug_df['DRUG'].str.upper())
    drug_df['signal'] = sig
    cols = ['medialid', 'signal', 'STARTDATE', 'ENDDATE', 'DRUG_NAME', 'ROUTE']
    drug_df.sort_values(by=['medialid', 'STARTDATE'], inplace=True)
    write_tsv(drug_df[cols], out_folder, sig, mode='w')


def administration_mv_to_file(cfg):
    sig = 'DRUG_ADMINISTERED'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    drug_df = pd.read_csv(os.path.join(raw_path, 'INPUTEVENTS_MV.csv'), encoding='utf-8', na_filter=False)
    drug_df['medialid'] = drug_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    # cases where strat<end replace start and end
    cond = drug_df['STARTTIME'] > drug_df['ENDTIME']
    drug_df.loc[cond, 'temp'] = drug_df[cond]['STARTTIME']
    drug_df.loc[cond, 'STARTTIME'] = drug_df[cond]['ENDTIME']
    drug_df.loc[cond, 'ENDTIME'] = drug_df[cond]['temp']
    ####

    drug_df.sort_values(['HADM_ID', 'ITEMID', 'STARTTIME', 'ENDTIME'], inplace=True)
    drug_df = drug_df.drop_duplicates(['HADM_ID', 'ITEMID', 'STARTTIME'], keep='last')
    print('CATEGORY_UNKNOWN: ' + str(drug_df[(drug_df['ORDERCATEGORYNAME'].isnull()) | (drug_df['ORDERCATEGORYNAME'].str.strip() == '')].shape[0]))
    drug_df.loc[(drug_df['ORDERCATEGORYNAME'].isnull()) | (drug_df['ORDERCATEGORYNAME'].str.strip() == ''), 'ORDERCATEGORYNAME'] = 'CATEGORY_UNKNOWN'
    drug_df['ORDERCATEGORYNAME'] = replace_spaces(drug_df['ORDERCATEGORYNAME'].str[3:])
    grpcnt = drug_df.groupby(['HADM_ID', 'ITEMID'])['ROW_ID'].count().reset_index()
    mv_df = pd.merge(drug_df, grpcnt, how='left', on=['HADM_ID', 'ITEMID'])
    one_give = mv_df[mv_df['ROW_ID_y'] == 1][['medialid', 'STARTTIME', 'ENDTIME', 'ITEMID', 'ORDERCATEGORYNAME']].copy()


    cols = ['medialid','HADM_ID', 'ITEMID', 'STARTTIME', 'ENDTIME', 'STATUSDESCRIPTION', 'ORDERCATEGORYNAME']
    more_gives = mv_df[mv_df['ROW_ID_y'] > 1][cols]

    more_gives.loc[:, 'cont'] = 0
    # Find all continues command
    more_gives.loc[(more_gives['STARTTIME'] <= more_gives['ENDTIME'].shift(1)) &
                   (more_gives['HADM_ID'] == more_gives['HADM_ID'].shift(1)) &
                   (more_gives['ITEMID'] == more_gives['ITEMID'].shift(1)), 'cont'] = 1
    # remove all continues commands
    remove_cond = (more_gives['cont'] == 1) & (more_gives['cont'].shift(-1) == 1) & (
                   more_gives['HADM_ID'] == more_gives['HADM_ID'].shift(1)) & (
                   more_gives['ITEMID'] == more_gives['ITEMID'].shift(1))
    more_gives = more_gives[~remove_cond].copy()

    # Set the correct end date and remove the end rows
    change_cond = ((more_gives['HADM_ID'] == more_gives['HADM_ID'].shift(-1)) & (
                    more_gives['ITEMID'] == more_gives['ITEMID'].shift(-1)) & (
                    more_gives['cont'].shift(-1) == 1))

    more_gives.loc[change_cond, 'ENDTIME'] = more_gives.shift(-1)['ENDTIME']
    more_gives = more_gives[more_gives['cont']==0][['medialid', 'STARTTIME', 'ENDTIME', 'ITEMID', 'ORDERCATEGORYNAME']]

    all_gives = pd.concat([one_give, more_gives], sort=False).sort_values(['medialid', 'STARTTIME'])
    all_gives['ITEMID'] = 'ITEMID:' + all_gives['ITEMID'].astype(int).astype(str)
    all_gives['signal'] = sig
    write_tsv(all_gives[['medialid', 'signal', 'STARTTIME', 'ENDTIME', 'ITEMID', 'ORDERCATEGORYNAME']], out_folder, sig+'_MV', mode='w')


def dministration_cv_to_file(cfg):
    sig = 'DRUG_ADMINISTERED'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    drug_df = pd.read_csv(os.path.join(raw_path, 'INPUTEVENTS_CV.csv'), encoding='utf-8', na_filter=False, usecols=['SUBJECT_ID', 'HADM_ID', 'ITEMID', 'CHARTTIME', 'RATE','AMOUNT',  'LINKORDERID', 'ORIGINALROUTE','ORIGINALRATE','ORIGINALRATEUOM'])
    drug_df['medialid'] = drug_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    drug_df['ORIGINALROUTE'] = replace_spaces(drug_df['ORIGINALROUTE'])
    print('ROUTE_UNKNOWN: ' + str(drug_df[(drug_df['ORIGINALROUTE'].isnull()) | (drug_df['ORIGINALROUTE'].str.strip() == '')].shape[0]))
    drug_df.loc[(drug_df['ORIGINALROUTE'].isnull()) | (drug_df['ORIGINALROUTE'].str.strip() == ''), 'ORIGINALROUTE'] = 'ROUTE_UNKNOWN'
    #rate_df = drug_df[(drug_df['RATE'].notnull()) & (drug_df['RATE'] != '')]
    #amt_df = drug_df[(drug_df['AMOUNT'] != '') | (drug_df['ORIGINALRATE'] != '')]
    grp = drug_df.groupby(['HADM_ID', 'medialid', 'ITEMID', 'LINKORDERID', 'ORIGINALROUTE'])
    final_rate = pd.concat([grp['CHARTTIME'].min().rename('starttime'), grp['CHARTTIME'].max().rename('endtime')], axis=1).reset_index()
    final_rate.sort_values(['medialid', 'starttime'], inplace=True)
    final_rate['ITEMID'] = 'ITEMID:' + final_rate['ITEMID'].astype(int).astype(str)
    final_rate['signal'] = sig
    write_tsv(final_rate[['medialid', 'signal', 'starttime', 'endtime', 'ITEMID', 'ORIGINALROUTE']], out_folder,
              sig + '_CV', mode='w')


if __name__ == '__main__':
    cfg = Configuration()
    #prescriptions_to_file(cfg)
    administration_mv_to_file(cfg)
    #dministration_cv_to_file(cfg)
