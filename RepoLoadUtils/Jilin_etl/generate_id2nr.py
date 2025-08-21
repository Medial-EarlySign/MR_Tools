import os
import pandas as pd
from Configuration import Configuration
from utils import write_tsv, fixOS
from staging_config import JilinDemographic
from sql_utils import get_sql_engine
from get_id2nr import get_ids_map


def get_id2nr_map():
    cfg = Configuration()
    ids_map = get_ids_map(fixOS(cfg.work_path))
    if ids_map.empty:
        create_id2nr()
    ids_map = get_ids_map(fixOS(cfg.work_path))
    return ids_map


def create_id2nr():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    jilin_demo_df = JilinDemographic()
    db_engine = get_sql_engine(jilin_demo_df.DBTYPE, jilin_demo_df.DBNAME, jilin_demo_df.username, jilin_demo_df.password)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return
    sql_query = "SELECT DISTINCT(orig_pid) FROM " + jilin_demo_df.TABLE
    df = pd.read_sql(sql_query, db_engine)
    ids = list(df['orig_pid'].values)
    ids.sort()
    outme = pd.DataFrame({'id': ids, 'nr': range(501000000, 501000000 + len(ids))})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)


if __name__ == '__main__':
    create_id2nr()
