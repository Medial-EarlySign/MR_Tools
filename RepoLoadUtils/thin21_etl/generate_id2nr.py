import os
import sys
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import write_tsv, fixOS
from staging_config import ThinDemographic
from sql_utils import get_sql_engine


def get_id2nr_map():
    cfg = Configuration()
    id2nr_file = os.path.join(fixOS(cfg.work_path), 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        create_id2nr(cfg, fixOS(cfg.prev_id2ind))
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': int})
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df['medialid'] = id2nr_df['medialid'].astype(int)
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']


def create_id2nr(cfg, previous_id2nr=None, start_from_id=5000000):
    thin_demo_def = ThinDemographic()
    db_engine = get_sql_engine(thin_demo_def.DBTYPE, thin_demo_def.DBNAME, thin_demo_def.username,
                               thin_demo_def.password)
    id2nr_file = os.path.join(fixOS(cfg.work_path), 'ID2NR')
    #if os.path.exists(id2nr_file):
    #    return
    sql_query = "SELECT orig_pid FROM " + thin_demo_def.TABLE + " WHERE code='patid' "
    all_ids = pd.DataFrame()
    for demo_df in pd.read_sql_query(sql_query, db_engine, chunksize=5000000):
        all_ids = all_ids.append(demo_df)
    print('before drop ' + str(all_ids.shape[0]))
    all_ids.drop_duplicates(inplace=True)
    print('after drop ' + str(all_ids.shape[0]))
    old_id2nr = pd.read_csv(previous_id2nr, sep='\t', names=['orig_pid', 'medialid'],
                            dtype={'orig_pid': str, 'medialid': int})

    new_ids = all_ids[~all_ids['orig_pid'].isin(old_id2nr['orig_pid'])].copy()
    removed_ids = old_id2nr[~old_id2nr['orig_pid'].isin(all_ids['orig_pid'])].copy()

    print('added patients: ' + str(new_ids.shape[0]))
    print('Removed patients: ' + str(removed_ids.shape[0]))

    all_demo = old_id2nr[~old_id2nr['orig_pid'].isin(removed_ids['orig_pid'])]

    start_from_id = old_id2nr['medialid'].max() + 1
    sr = pd.Series(range(start_from_id, start_from_id + new_ids.shape[0]))
    new_ids.loc[:, 'medialid'] = sr.values
    all_demo = pd.concat([all_demo, new_ids])
    all_demo['medialid'] = all_demo['medialid'].astype(int)
    all_demo[['orig_pid', 'medialid']].to_csv(id2nr_file, sep='\t', index=False, header=False)


def comp_with_old(cfg, previous_id2nr):
    id2nr_file = os.path.join(fixOS(cfg.work_path), 'ID2NR')

    old_id2nr = pd.read_csv(previous_id2nr, sep='\t', names=['orig_pid', 'medialid'], dtype={'orig_pid': str, 'medialid': int})
    curr_id2nr = pd.read_csv(id2nr_file, sep='\t', names=['orig_pid', 'medialid'], dtype={'orig_pid': str, 'medialid': int})

    old_id2nr['prac'] = old_id2nr['orig_pid'].str[0:5]
    curr_id2nr['prac'] = curr_id2nr['orig_pid'].str[0:5]

    old_parcs = old_id2nr['prac'].unique().tolist()
    curr_pracs = curr_id2nr['prac'].unique().tolist()

    new_pracs = set(curr_pracs) - set(old_parcs)
    removed_pacs = set(old_parcs) - set(curr_pracs)

    print('Prac added in 20: ' + str(len(new_pracs)))
    print('Prac removed in 20: ' + str(len(removed_pacs)))
    print(removed_pacs)
    print('Removed id from removed pracs: ' + str(old_id2nr[old_id2nr['prac'].isin(list(removed_pacs))].shape[0]))
    print('new ids from new pracs: ' + str(curr_id2nr[curr_id2nr['prac'].isin(list(new_pracs))].shape[0]))

    overlap = curr_id2nr[~curr_id2nr['prac'].isin(list(new_pracs))]
    mrg = overlap.merge(old_id2nr, on='orig_pid', how='left')
    print('New ids in existing pracs: ' + str(mrg[mrg['medialid_y'].isnull()].shape[0]))


if __name__ == '__main__':
    cfg = Configuration()
    old_rep = fixOS(cfg.prev_id2ind)
    create_id2nr(cfg, old_rep)
    comp_with_old(cfg, old_rep)
