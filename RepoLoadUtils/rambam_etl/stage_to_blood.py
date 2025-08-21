import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS
from generate_id2nr import get_id2nr_map
from rambam_utils import hier_field_to_dict, get_dict_item


def tables_to_blood_products(raw_df, final_path, id2nr):

    #  Chanels:  date, blood product , quantity
    time1 = time.time()
    sig = 'BLOOD_PRODUCT'
    if os.path.exists(os.path.join(final_path, sig)):
        print('signal ' + sig + ' already loaded')
        return
    bp_df = raw_df[['pid', 'dispanseddate', 'bloodproducttype', 'bloodproducttypeHier', 'quantitydispensed']]

    bp_df['bloodproduct_dict'] = bp_df['bloodproducttypeHier'].apply(lambda x: hier_field_to_dict(x))
    bp_df['bloodproduct'] = bp_df['bloodproduct_dict'].apply(lambda x: get_dict_item(x, '0'))

    bp_df.loc[bp_df['quantitydispensed'] == 'Null', 'quantitydispensed'] = 0
    bp_df['signal'] = sig
    bp_df['medialid'] = bp_df['pid'].astype(str).map(id2nr)
    print('Throwing ' + str(bp_df[bp_df['dispanseddate'] <= '1900-01-01 00:00:00'].shape[0]) + ' recordes with ilegal date')
    bp_df = bp_df[bp_df['dispanseddate'] > '1900-01-01 00:00:00']
    print('  going to sort and save signal ' + sig)
    cols = ['medialid', 'signal', 'dispanseddate', 'bloodproduct', 'quantitydispensed']
    bp_df.sort_values(by=['medialid', 'dispanseddate'], inplace=True)
    write_tsv(bp_df[cols], final_path, sig)
    print('   process signal ' + sig + ' in ' + str(time.time() - time1))


def tables_to_blood_type(raw_df, final_path, id2nr):
    #  Chanels:  date, blood product , quantity
    time1 = time.time()
    sig = 'BLOOD_TYPE'
    if os.path.exists(os.path.join(final_path, sig)):
        print('signal ' + sig + ' already loaded')
        return
    bp_df = raw_df[['pid', 'bloodtype']]
    bp_df = bp_df[bp_df['bloodtype'] != 'Null']

    bp_df['signal'] = sig
    bp_df['medialid'] = bp_df['pid'].astype(str).map(id2nr)
    print('  going to sort and save signal ' + sig)
    cols = ['medialid', 'signal', 'bloodtype']
    bp_df.drop_duplicates(subset=cols, inplace=True)
    bp_df.sort_values(by='medialid', inplace=True)
    write_tsv(bp_df[cols], final_path, sig)
    print('   process signal ' + sig + ' in ' + str(time.time() - time1))


def tables_to_blood_signals():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    table_path = os.path.join(out_folder, 'raw_tables')
    final_path = os.path.join(out_folder, 'FinalSignals')
    id2nr = get_id2nr_map()
    event_type = 'ev_blood_bank'

    print('Reading table for ' + event_type)
    raw_table = pd.read_csv(os.path.join(table_path, event_type), sep='\t')

    tables_to_blood_products(raw_table, final_path, id2nr)
    #tables_to_blood_type(raw_table, final_path, id2nr)


if __name__ == '__main__':
    tables_to_blood_signals()
