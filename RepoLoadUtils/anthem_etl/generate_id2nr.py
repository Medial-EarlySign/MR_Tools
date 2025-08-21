import os
import sys
import pandas as pd
from Configuration import Configuration
#sys.path.append('/mnt/project/Tools/RepoLoadUtils/common')
from sql_utils import create_postgres_engine_generic
from utils import write_tsv
from DB import DB


def get_id2nr_map():
    cfg = Configuration()
    id2nr_file = os.path.join(cfg.work_path, 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        create_id2nr()
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': str})
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']


def create_id2nr():
    cfg = Configuration()
    out_folder = cfg.work_path
    db = DB()
    dbname = '5e7cff5094fe29000a4e40eb'
    db_engine = create_postgres_engine_generic(db.host, db.port, dbname, db.user, db.password)
    print(db_engine)
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    print(id2nr_path)
    #if os.path.exists(id2nr_path):
    #    return
    ids = []
    #sql_query = 'SELECT distinct(membernumberhci) FROM pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_eligibility_sample_3years'
    sql_query = "SELECT distinct(labs.membernumberhci) from pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_labs_sample_3years labs join map_signals ms on labs.testname=ms.testname  join pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_eligibility_sample_3years el on el.membernumberhci = labs.membernumberhci where ms.targetname in ('HbA1C', 'Glucose')"
    cnt = 0
    for demo_df in pd.read_sql_query(sql_query, db_engine, chunksize=db.default_batch_size):
        ids = ids + demo_df['membernumberhci'].tolist()
        cnt += 1
        print(' read chunk ' + str(cnt) + ' ids size ' + str(len(ids)))

    ids = list(set(ids))
    ids.sort()
    outme = pd.DataFrame({'id': ids, 'nr': range(1000000, 1000000 + len(ids))})
    #outme = pd.DataFrame({'id': ids, 'nr': ids})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)


if __name__ == '__main__':
    create_id2nr()
