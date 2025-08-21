import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS
from generate_id2nr import get_id2nr_map
from rambam_utils import hier_field_to_dict, get_dict_item


def get_specimen_map(map_file_name):
    map_df = pd.read_csv(map_file_name, sep='\t', names=['orig', 'specimen'], header=None)
    map_df['orig'] = map_df['orig'].str.strip().str.replace(' ', '_')
    map1 = map_df.set_index('orig')['specimen']
    return map1


def tables_to_microbiology():
    cfg = Configuration()
    raw_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    table_path = os.path.join(out_folder, 'raw_tables')
    final_path = os.path.join(out_folder, 'FinalSignals')
    specimen_map = get_specimen_map(os.path.join(code_path, 'specimen_map.txt'))

    id2nr = get_id2nr_map()

    #  Chanels:  collection date, result date, specimen|microorganism, antibiotic|susceptability
    time1 = time.time()
    event_type = 'ev_lab_results_microbiology'
    sig = 'MICROBIOLOGY'
    if os.path.exists(os.path.join(final_path, sig)):
        print('signal ' + sig + ' already loaded')
        return
    print('Reading table for ' + event_type)
    raw_table = pd.read_csv(os.path.join(table_path, event_type), sep='\t')
    mb_df = raw_table[['pid', 'collectiondate', 'resultdate', 'specimenmaterialcodeHier', 'microorganism_codeHier',
                       'antibioticcodeHier', 'susceptibilityinterpretationHier']]

    mb_df['specimen_dict'] = mb_df['specimenmaterialcodeHier'].apply(lambda x: hier_field_to_dict(x))
    mb_df['specimen'] = mb_df['specimen_dict'].apply(lambda x: get_dict_item(x, '1'))
    mb_df['specimen'] = mb_df['specimen'].map(specimen_map)
    mb_df['specimen'].fillna('NoSpec', inplace=True)

    mb_df['organism_dict'] = mb_df['microorganism_codeHier'].apply(lambda x: hier_field_to_dict(x))
    mb_df['organism'] = mb_df['organism_dict'].apply(lambda x: get_dict_item(x, '2'))
    mb_df.loc[mb_df['organism'] == '_', 'organism'] = 'NoOrganism'
    mb_df['specimen_organism'] = mb_df['specimen'] + '|' + mb_df['organism']

    mb_df['antibiotic_dict'] = mb_df['antibioticcodeHier'].apply(lambda x: hier_field_to_dict(x))
    mb_df['antibiotic_name'] = mb_df['antibiotic_dict'].apply(lambda x: get_dict_item(x, '1'))
    mb_df['antibiotic_atc'] = mb_df['antibiotic_dict'].apply(lambda x: get_dict_item(x, '2'))
    mb_df.loc[mb_df['antibiotic_name'] == '_', 'antibiotic_name'] = 'NoAntiBiotics'
    mb_df.loc[mb_df['antibiotic_atc'] == '_', 'antibiotic_atc'] = 'NA'

    mb_df['susceptibility_dict'] = mb_df['susceptibilityinterpretationHier'].apply(lambda x: hier_field_to_dict(x))
    mb_df['susceptibility'] = mb_df['susceptibility_dict'].apply(lambda x: get_dict_item(x, '1'))
    mb_df.loc[mb_df['susceptibility'] == '_', 'susceptibility'] = 'NA'
    mb_df['antibiotic_susceptibility'] = mb_df['antibiotic_name'] + '|' + mb_df['antibiotic_atc'] + '|' + mb_df['susceptibility']

    mb_df['signal'] = sig
    mb_df['medialid'] = mb_df['pid'].astype(str).map(id2nr)
    print('Throwing ' + str(mb_df[(mb_df['collectiondate'] <= '1900-01-01 00:00:00') | (mb_df['resultdate'] <= '1900-01-01 00:00:00')].shape[0]) + ' recordes with ilegal date')
    mb_df = mb_df[(mb_df['collectiondate'] > '1900-01-01 00:00:00') & (mb_df['resultdate'] > '1900-01-01 00:00:00')]
    print('  going to sort and save signal ' + sig)
    cols = ['medialid', 'signal', 'collectiondate', 'resultdate', 'specimen_organism', 'antibiotic_susceptibility']
    mb_df.sort_values(by=['medialid', 'collectiondate'], inplace=True)
    write_tsv(mb_df[cols], final_path, sig)
    print('   process signal ' + sig + ' in ' + str(time.time() - time1))


if __name__ == '__main__':
    tables_to_microbiology()
