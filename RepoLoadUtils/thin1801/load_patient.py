import os
import pandas as pd
from datetime import datetime
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS


def get_id2nr_map():
    cfg = Configuration()
    id2nr_file = os.path.join(fixOS(cfg.work_path), 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        pat_demo_file = fixOS(cfg.patient_demo)
        valid_pat_flags = ['A', 'C', 'D']
        demo_df = pd.read_csv(pat_demo_file)
        demo_df = demo_df[demo_df, demo_df['patflag'].isin(valid_pat_flags)]
        create_id2nr(fixOS(cfg.prev_id2ind))
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': int})
    #assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    #assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df['medialid'] = id2nr_df['medialid'].astype(int)
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']


# def create_id2nr(previous_id2nr=None, year = datetime.now().year, start_from_id=5000000):
#     cfg = Configuration()
#     out_folder = fixOS(cfg.work_path)
#     data_path = fixOS(cfg.raw_source_path)
#     id2nr_path = os.path.join(out_folder, 'ID2NR')
#
#     if not(os.path.exists(id2nr_path)):
#         in_file_names = list(filter(lambda f: f.startswith('patient.'), os.listdir(data_path)))
#         old_pracs = []
#         if previous_id2nr is not None:
#             old_id2nr = pd.read_csv(previous_id2nr, sep='\t', names=['patid', 'medialid'],
#                                     dtype={'patid': str, 'medialid': int})
#             old_id2nr['prac'] = old_id2nr['patid'].str.slice(0, 5)
#             old_pracs = old_id2nr['prac'].unique()
#             start_from_id = old_id2nr['medialid'].max() + 1
#
#         demo_path = os.path.join(out_folder, 'demo')
#
#         valid_pat_flags = ['A', 'C', 'D']
#         cnt = 1
#         stats_df = pd.DataFrame()
#         for pfile in in_file_names:
#             print(str(cnt) + ') ' + pfile)
#             cnt += 1
#             prac = pfile.split('.')[1]
#             pat_df = read_fwf('patient', data_path, pfile)
#             pat_df['patid'] = prac + pat_df['patid']
#             pat_df['yob'] = (pat_df['yob']/10000).astype(int)
#             pat_df['prac'] = prac
#             stats_df = stats_df.append({'stat': 'skipped_invalid_patflag', 'prac': prac,
#                                         'count': pat_df[~pat_df['patflag'].isin(valid_pat_flags)].shape[0]},
#                                        ignore_index=True)
#             pat_df = pat_df[pat_df['patflag'].isin(valid_pat_flags)]
#             pat_df['dup'] = pat_df.duplicated(subset=['patid'])
#             if pat_df[pat_df['dup'] == True].shape[0] > 0:
#                 eprint("error! ", str(pat_df[pat_df['dup'] == True]['patid']), "seen twice!")
#                 stats_df = stats_df.append({'stat': 'duplicated_patid', 'prac': prac,
#                                             'count': pat_df[pat_df['dup'] == True].shape[0]}, ignore_index=True)
#                 pat_df.drop_duplicates(subset=['patid'], inplace=True)
#
#             if prac in old_pracs:
#                 prac_pat = old_id2nr[old_id2nr['prac'] == prac][['patid','medialid']]
#                 pat_df = pat_df.merge(prac_pat, how='left', on='patid')
#                 new_pat_cnt = pat_df[pat_df['medialid'].isnull()].shape[0]
#                 print('patients not in old: ' + str(new_pat_cnt))
#                 stats_df = stats_df.append({'stat': 'new_patient_in_practice', 'prac': prac,
#                                             'count': new_pat_cnt}, ignore_index=True)
#                 sr = pd.Series(range(start_from_id, start_from_id+new_pat_cnt))
#                 pat_df.loc[pat_df['medialid'].isnull(), 'medialid'] = sr.values
#                 start_from_id = start_from_id + new_pat_cnt + 1
#                 pat_df['medialid'] = pat_df['medialid'].astype(int)
#             else:
#                 print('New practice ' + prac)
#                 stats_df = stats_df.append({'stat': 'new_practice', 'prac': prac,
#                                             'count': pat_df.shape[0]}, ignore_index=True)
#                 pat_df['medialid'] = pat_df.index + start_from_id
#                 start_from_id = pat_df['medialid'].max() + 1
#
#             ############
#             to_stack = pat_df[['medialid', 'yob', 'regdate', 'xferdate', 'sex', 'deathdate']].set_index('medialid', drop=True)
#             to_stack.rename(columns={'yob': 'BYEAR', 'regdate': 'STARTDATE', 'xferdate': 'ENDDATE',
#                                      'sex': 'GENDER', 'deathdate': 'DEATH'}, inplace=True)
#             stack_dict = to_stack.stack().to_frame()
#             stack_dict['medialid'] = stack_dict.index.get_level_values(0)
#             stack_dict['data'] = stack_dict.index.get_level_values(1)
#             stack_dict = stack_dict[stack_dict[0] != 0]
#             stack_dict.sort_values('medialid', inplace=True)
#             write_tsv(stack_dict[['medialid', 'data', 0]], demo_path, "thin_demographic")
#             ############
#             stats_df = stats_df.append({'stat': 'processed', 'prac': prac,
#                                         'count': pat_df.shape[0]}, ignore_index=True)
#
#             parc_df = pat_df[['medialid', 'prac']].copy()
#             parc_df['sig'] = 'PARC'
#             parc_df['parc'] == 'PARC_' + parc_df['parc']
#             write_tsv(parc_df[['medialid', 'sig', 'prac']], demo_path, 'PARC')
#             write_tsv(pat_df[['medialid', 'yob']], demo_path, 'byears')
#             write_tsv(pat_df[['medialid', 'yob', 'sex']], demo_path, 'Demographics')
#             write_tsv(pat_df[['patid', 'medialid']], out_folder, 'ID2NR')
#
#         write_tsv(stats_df[['stat', 'prac', 'count']], demo_path, 'thin_demo_stats')


def create_id2nr(demo_df, previous_id2nr=None, start_from_id=5000000):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.raw_source_path)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return

    prac_list = list(filter(lambda f: f.startswith('patient.'), os.listdir(data_path)))
    prac_list = [x[-5:] for x in prac_list]
    demo_df = demo_df[demo_df['pracid'].isin(prac_list)]
    demo_df = demo_df[['combid']]

    old_id2nr = pd.read_csv(previous_id2nr, sep='\t', names=['combid', 'medialid'],
                            dtype={'combid': str, 'medialid': int})
    old_id2nr['prac'] = old_id2nr['combid'].str.slice(0, 5)
    print(' patient in pracs  in old that not in not in new = ' + str(old_id2nr[~old_id2nr['prac'].isin(prac_list)].shape[0]))
    start_from_id = old_id2nr['medialid'].max() + 1

    demo_df['dup'] = demo_df.duplicated(subset=['combid'])
    if demo_df[demo_df['dup'] == True].shape[0] > 0:
        print("error! ", str(demo_df[demo_df['dup'] == True]['combid']), "seen twice!")
        demo_df.drop_duplicates(subset=['combid'], inplace=True)

    all_demo = demo_df.merge(old_id2nr, how='left', on='combid')

    new_pat_cnt = all_demo[all_demo['medialid'].isnull()].shape[0]
    print('patients not in old: ' + str(new_pat_cnt))
    sr = pd.Series(range(start_from_id, start_from_id + new_pat_cnt))
    all_demo.loc[all_demo['medialid'].isnull(), 'medialid'] = sr.values
    all_demo['medialid'] = all_demo['medialid'].astype(int)
    write_tsv(all_demo[['combid', 'medialid']], out_folder, inr_file)


def signals_from_patient_demography_file(demo_df):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.raw_source_path)
    demo_path = os.path.join(out_folder, 'demo')
    year = 2018
    id2nr = get_id2nr_map()
    gender_map = pd.Series({'M': 1, 'F': 2})

    prac_list = list(filter(lambda f: f.startswith('patient.'), os.listdir(data_path)))
    prac_list = [x[-5:] for x in prac_list]
    demo_df = demo_df[demo_df['pracid'].isin(prac_list)]
    demo_df['medialid'] = demo_df['combid'].map(id2nr)


    # Write PRAC signal
    prac_df = demo_df[['medialid', 'pracid']].copy()
    prac_df['signal'] = 'PRAC'
    prac_df['pracid'] = 'PRAC_' + prac_df['pracid']
    prac_df.sort_values(by=['medialid', 'pracid'], inplace=True)
    write_tsv(prac_df[['medialid', 'signal', 'pracid']], demo_path, 'PRAC')

    # Write GENDER signal
    gender_df = demo_df[demo_df['sex'].notnull()][['medialid', 'sex']].copy()
    gender_df['signal'] = 'GENDER'
    gender_df['gender'] = gender_df['sex'].map(gender_map)
    gender_df.sort_values(by='medialid', inplace=True)
    write_tsv(gender_df[['medialid', 'signal', 'gender']], demo_path, 'GENDER')

    # Write BYEAR signal
    byear_df = demo_df[demo_df['dob'].notnull()][['medialid', 'dob']].copy()
    byear_df['signal'] = 'BYEAR'
    byear_df['byear'] = byear_df['dob'].str[-4:]
    byear_df.sort_values(by='medialid', inplace=True)
    write_tsv(byear_df[['medialid', 'signal', 'byear']], demo_path, 'BYEAR')

    # Write BDATE signal
    byear_df = demo_df[demo_df['dob'].notnull()][['medialid', 'dob']].copy()
    byear_df['signal'] = 'BDATE'
    byear_df['bdate'] = byear_df['dob'].str[-4:] + byear_df['dob'].str[3:5] + byear_df['dob'].str[0:2]
    byear_df.sort_values(by='medialid', inplace=True)
    write_tsv(byear_df[['medialid', 'signal', 'bdate']], demo_path, 'BDATE')


    # Write STARTDATE signal
    sd_df = demo_df[demo_df['startdate'].notnull()][['medialid', 'startdate']].copy()
    sd_df['signal'] = 'STARTDATE'
    sd_df['startdate'] = sd_df['startdate'].str[-4:] + sd_df['startdate'].str[3:5] + sd_df['startdate'].str[0:2]
    sd_df.sort_values(by='medialid', inplace=True)
    write_tsv(sd_df[['medialid', 'signal', 'startdate']], demo_path, 'STARTDATE')

    # Write ENDDATE signal
    ed_df = demo_df[demo_df['enddate'].notnull()][['medialid', 'enddate']].copy()
    ed_df['signal'] = 'ENDDATE'
    ed_df['enddate'] = ed_df['enddate'].str[-4:] + ed_df['enddate'].str[3:5] + ed_df['enddate'].str[0:2]
    ed_df.sort_values(by='medialid', inplace=True)
    write_tsv(ed_df[['medialid', 'signal', 'enddate']], demo_path, 'ENDDATE')

    # Write  DEATH  signal
    ed_df = demo_df[demo_df['deathdte'].notnull()][['medialid', 'deathdte']].copy()
    ed_df['signal'] = 'DEATH'
    ed_df['deathdte'] = ed_df['deathdte'].str[-4:] + ed_df['deathdte'].str[3:5] + ed_df['deathdte'].str[0:2]
    ed_df.sort_values(by='medialid', inplace=True)
    write_tsv(ed_df[['medialid', 'signal', 'deathdte']], demo_path, 'DEATH')

    # Write  Censor  signal
    stst = {'regular': '1001', 'dead': '2008', 'transferred': '2002', 'unknown': '2009'}
    # we cant rely on the active flag, sometimes its Y and the patient left (e.g. a9937025J)
    censor_df = demo_df[['medialid', 'startdate', 'enddate', 'xferdate', 'deathdte']].copy()
    censor_df['signal'] = 'Censor'
    censor_df['censor'] = stst['unknown']
    censor_df['endyear'] = censor_df['enddate'].str[-4:].astype(int)
    censor_df['startdate'] = censor_df['startdate'].str[-4:] + censor_df['startdate'].str[3:5] + censor_df['startdate'].str[0:2]
    censor_df['eventdate'] = censor_df['enddate'].str[-4:] + censor_df['enddate'].str[3:5] + censor_df['enddate'].str[0:2]

    # When start year is now its regular
    censor_df.loc[censor_df['endyear'] >= year, 'censor'] = stst['regular']
    censor_df.loc[censor_df['endyear'] >= year, 'eventdate'] = censor_df[censor_df['endyear'] >= year]['startdate']

    censor_df.loc[(censor_df['censor'] == stst['unknown']) & (censor_df['deathdte'].notnull()), 'censor'] = stst['dead']
    censor_df.loc[(censor_df['censor'] == stst['unknown']) & (censor_df['xferdate'].notnull()), 'censor'] = stst['transferred']
    censor_df.sort_values(by='medialid', inplace=True)
    write_tsv(censor_df[['medialid', 'signal', 'eventdate', 'censor']], demo_path, 'Censor')


def load_demographic(create_id2nr_file=True, craete_demo_files=True):
    cfg = Configuration()
    prev_id2inr = fixOS(cfg.prev_id2ind)
    pat_demo_file = fixOS(cfg.patient_demo)
    valid_pat_flags = ['A', 'C', 'D']
    demo_df = pd.read_csv(pat_demo_file)
    demo_df = demo_df[demo_df['patflag'].isin(valid_pat_flags)]
    if create_id2nr_file:
        create_id2nr(demo_df, previous_id2nr=prev_id2inr)
    if craete_demo_files:
        signals_from_patient_demography_file(demo_df)


if __name__ == '__main__':
    load_demographic(create_id2nr_file=False, craete_demo_files=True)
