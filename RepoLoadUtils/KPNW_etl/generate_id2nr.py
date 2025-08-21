import os
import pandas as pd
from Configuration import Configuration
from utils import write_tsv, fixOS
from staging_config import KPNWDemographic
from sql_utils import get_sql_engine
from get_from_stage import get_all_pids


def get_id2nr_map():
    cfg = Configuration()
    id2nr_file = os.path.join(fixOS(cfg.work_path), 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        create_id2nr()
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': str})
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']

'''
def create_id2nr():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.data_folder)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return
    ids = []
    pat_demo_file = 'medial_flu_pat.sas7bdat'
    full_file = os.path.join(data_path, pat_demo_file)
    for demo_df in pd.read_sas(full_file, chunksize=500000, encoding='utf-8'):
        print('read chunk')
        demo_df['PAT_ID_GEN'] = demo_df['PAT_ID_GEN'].astype(int)
        ids = ids + demo_df['PAT_ID_GEN'].tolist()
    full_file = os.path.join('T:\\NWP\\', pat_demo_file)
    for demo_df in pd.read_sas(full_file, chunksize=500000, encoding='utf-8'):
        print('read chunk delta')
        demo_df['PAT_ID_GEN'] = demo_df['PAT_ID_GEN'].astype(int)
        ids = ids + demo_df['PAT_ID_GEN'].tolist()
    ids = list(set(ids))
    ids.sort()
    #outme = pd.DataFrame({'id': ids, 'nr': range(6000000, 6000000 + len(ids))})
    outme = pd.DataFrame({'id': ids, 'nr': ids})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)
'''


def create_id2nr():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(fixOS(cfg.work_path), inr_file)
    if os.path.exists(id2nr_path):
        return
    stage_def = KPNWDemographic()
    db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)
    sql_query = 'SELECT DISTINCT(orig_pid) from ' + stage_def.TABLE
    df = pd.read_sql(sql_query, db_engine)

    ids = df['orig_pid'].unique().tolist()
    ids.sort()
    outme = pd.DataFrame({'id': ids, 'nr': ids})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)


if __name__ == '__main__':
    create_id2nr()
