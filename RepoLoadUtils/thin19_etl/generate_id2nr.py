import os
import pandas as pd
from Configuration import Configuration
from utils import write_tsv, fixOS


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
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df['medialid'] = id2nr_df['medialid'].astype(int)
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']


def create_id2nr(previous_id2nr=None, start_from_id=5000000):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.raw_source_path)
    patients_path = fixOS(cfg.patient_source_path)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return
    demo_df = pd.read_csv(os.path.join(patients_path, 'patient_demography.csv'))
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


def comp_with_old(previous_id2nr):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.raw_source_path)
    patients_path = fixOS(cfg.patient_source_path)

    demo_df = pd.read_csv(os.path.join(patients_path, 'patient_demography.csv'))
    prac_list = list(filter(lambda f: f.startswith('patient.'), os.listdir(data_path)))
    prac_list = [x[-5:] for x in prac_list]

    #demo_df = demo_df[demo_df['pracid'].isin(prac_list)]
    demo_df = demo_df[['combid', 'pracid']].copy()

    old_id2nr = pd.read_csv(previous_id2nr, sep='\t', names=['combid', 'medialid'],
                            dtype={'combid': str, 'medialid': int})
    old_id2nr['prac'] = old_id2nr['combid'].str.slice(0, 5)
    old_prac_list = old_id2nr['prac'].unique().tolist()

    new_pracs = set(prac_list) - set(old_prac_list)
    removed_pacs = set(old_prac_list) - set(prac_list)
    same_pracs = set(old_prac_list) & set(prac_list)
    print('Prac added in 19: ' + str(len(new_pracs)))
    print('Prac removed in 19: ' + str(len(removed_pacs)))
    print('Common parcs: ' + str(len(same_pracs)))

    pids_in_new = demo_df[demo_df['pracid'].isin(new_pracs)]
    print('pids in new pracs: ' + str(pids_in_new.shape[0]))

    pid_removed = old_id2nr[old_id2nr['prac'].isin(removed_pacs)]
    print('pids in removed pracs: ' + str(pid_removed.shape[0]))

    pids_same = demo_df[demo_df['pracid'].isin(same_pracs)]
    old_smae = old_id2nr[old_id2nr['prac'].isin(same_pracs)]
    mrg = pids_same.merge(old_smae, how='outer', on='combid')
    print('New pids in existing pracs : ' + str(mrg[mrg['medialid'].isnull()].shape[0]))
    print('removed pids in existing pracs : ' + str(mrg[mrg['pracid'].isnull()].shape[0]))
    #print(mrg)

if __name__ == '__main__':
    cfg = Configuration()
    old_rep = fixOS(cfg.prev_id2ind)
    #create_id2nr(old_rep)
    comp_with_old(old_rep)