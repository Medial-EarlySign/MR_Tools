import os
import sys
import pandas as pd
from Configuration import Configuration
from const_and_utils import fixOS
med_path = fixOS('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
sys.path.insert(0, med_path)
import medpython as med


def get_signals_from_sig_file(rep_path, source, sig_map):
    numeric_sigs = []
    cat_sigs = []
    sig_file = os.path.join(rep_path, source+'.signals')
    with open(sig_file) as f:
        lines = f.readlines()
    lines = [l for l in lines if not (l.strip().startswith('#') or len(l.strip()) == 0)]
    # print(lines)
    signals = [sig.split('\t')[1] for sig in lines]
    signals = [x for x in signals if x in sig_map.index]
    for s in signals:
        # print(thin_map.loc[s]['type'])
        if sig_map.loc[s]['type'] == 'numeric':
            numeric_sigs.append(s)
        elif sig_map.loc[s]['type'] == 'string':
            cat_sigs.append(s)

    return numeric_sigs, cat_sigs


def get_common_patients(new_rep_path, old_rep_path):
    new_id2nr_file = os.path.join(new_rep_path, 'ID2NR')
    new_id2nr_df = pd.read_csv(new_id2nr_file, sep='\t', names=['combid', 'medialid'],
                               dtype={'combid': str, 'medialid': int})

    old_id2nr_file = os.path.join(old_rep_path, 'ID2NR')
    old_id2nr_df = pd.read_csv(old_id2nr_file, sep='\t', names=['combid', 'medialid'],
                               dtype={'combid': str, 'medialid': int})

    new_pids = new_id2nr_df['medialid'].unique()
    old_pids = old_id2nr_df['medialid'].unique()

    common_ids = list(set(new_pids) & set(old_pids))
    return common_ids


def get_new_patients():
    cfg = Configuration()
    new_rep_path = fixOS(cfg.curr_repo)
    old_rep_path = fixOS(cfg.prev_repo)
    new_id2nr_file = os.path.join(new_rep_path, 'ID2NR')
    new_id2nr_df = pd.read_csv(new_id2nr_file, sep='\t', names=['combid', 'medialid'],
                               dtype={'combid': str, 'medialid': int})

    old_id2nr_file = os.path.join(old_rep_path, 'ID2NR')
    old_id2nr_df = pd.read_csv(old_id2nr_file, sep='\t', names=['combid', 'medialid'],
                               dtype={'combid': str, 'medialid': int})

    new_pids = new_id2nr_df['medialid'].unique()
    old_pids = old_id2nr_df['medialid'].unique()

    new_ids = list(set(new_pids) - set(old_pids))
    return new_ids


def common_pids_sigs(sig_type):
    if sig_type == 'numeric':
        ind = 0
    elif sig_type == 'string':
        ind = 1
    else:
        print('Unsuported sig type')
        return None, None

    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    old_rep = fixOS(cfg.prev_repo)
    code_folder = fixOS(cfg.code_folder)
    full_file = os.path.join(code_folder, 'thin_signal_mapping.csv')

    thin_map = pd.read_csv(full_file, sep='\t')
    thin_map.drop_duplicates(subset='signal', inplace=True)
    thin_map.set_index('signal', inplace=True)

    old_signals = get_signals_from_sig_file(old_rep, 'thin', thin_map)[ind]
    new_signals = get_signals_from_sig_file(new_rep, 'thin', thin_map)[ind]

    print('New signals: ' + str(set(new_signals) - set(old_signals)))
    print('Missing signals: ' + str(set(old_signals) - set(new_signals)))

    common_sigs = list(set(new_signals) & set(old_signals))
    common_pids = get_common_patients(new_rep, old_rep)

    print('Common ids=' + str(len(common_pids)))
    print('Common signals=' + str(len(common_sigs)))
    return common_pids, common_sigs


def read_repositories(common_pids, common_sigs):
    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    old_rep = fixOS(cfg.prev_repo)
    rep_old = med.PidRepository()
    rep_old.read_all(os.path.join(old_rep, 'thin.repository'), common_pids, common_sigs)
    print(med.cerr())

    rep_new = med.PidRepository()
    rep_new.read_all(os.path.join(new_rep, 'thin.repository'), common_pids, common_sigs)
    print(med.cerr())

    return rep_new, rep_old


def get_pids_in_years(byear_start, byear_end):
    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    rep_new = med.PidRepository()
    rep_new.read_all(os.path.join(new_rep, 'thin.repository'), [], ['BYEAR'])
    print(med.cerr())
    byear_df = rep_new.get_sig('BYEAR')
    byear_df = byear_df[(byear_df['val'] >= byear_start) & (byear_df['val'] < byear_end)]
    return list(byear_df['pid'].unique())
