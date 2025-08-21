import os
import pandas as pd
from Configuration import Configuration
from utils import write_tsv, fixOS


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


def create_id2nr():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_paths = [fixOS(cfg.raw_source_path), fixOS(cfg.raw_source_path_add)]
    inr_file = 'ID2NR'
    id2nr_path = os.path.join(out_folder, inr_file)
    if os.path.exists(id2nr_path):
        return
    ids = []
    for data_path in data_paths:
        xml_file = os.listdir(data_path)
        xml_file = [f for f in xml_file if f.endswith('.xml')]
        ids = ids + [int(x[:-4]) for x in xml_file]
    ids = list(set(ids))
    ids.sort()
    outme = pd.DataFrame({'id': ids, 'nr': range(101000000, 101000000 + len(ids))})
    write_tsv(outme[['id', 'nr']], out_folder, inr_file)


if __name__ == '__main__':
    create_id2nr()