import os
import pandas as pd


def get_ids_map(outfolder):
    id2nr_file = os.path.join(outfolder, 'ID2NR')
    if not (os.path.exists(id2nr_file)):
        pd.Series()
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': str})
    assert len(id2nr_df['combid'].unique()) == id2nr_df.shape[0], "Duplicate combid in ID2NR"
    assert len(id2nr_df['medialid'].unique()) == id2nr_df.shape[0], "Duplicate medialid in ID2NR"
    id2nr_df.set_index('combid', drop=True, inplace=True)
    return id2nr_df['medialid']
