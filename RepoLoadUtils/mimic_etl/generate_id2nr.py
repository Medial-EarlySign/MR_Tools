import pandas as pd
import os
from utils import fixOS, write_tsv
from staging_config import MimicDemographic
from sql_utils import get_sql_engine
from get_from_stage import get_all_pids


def get_id2nr_map(out_folder):
    id2nr_file = os.path.join(out_folder, 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        create_id2nr(out_folder)
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': str})
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']


def create_id2nr(out_folder):
    mimic_def = MimicDemographic()
    db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username, mimic_def.password)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return
    ids = get_all_pids(db_engine, mimic_def.TABLE)
    ids = list(set(ids))
    ids.sort()
    outme = pd.DataFrame({'id': ids, 'nr': ids})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)


if __name__ == '__main__':
    create_id2nr(fixOS('W:\\Users\\Tamar\\mimic_load\\'))
