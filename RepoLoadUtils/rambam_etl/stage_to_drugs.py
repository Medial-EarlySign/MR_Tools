import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS
from generate_id2nr import get_id2nr_map
from rambam_utils import hier_field_to_dict, get_dict_item


med_maps = {'ev_medications_administered': 'DRUG_ADMINISTERED',
            'ev_medications_adm': 'DRUG_BACKGROUND',
            'ev_medications_orders': 'DRUG_PRESCRIBED',
            'ev_medications_recom': 'DRUG_RECOMMENDED'}


def get_route_form_map(map_file_name):
    map_df = pd.read_csv(map_file_name, sep='\t')
    map_df['index_field'] = map_df['routecode'].astype(str) + '_' + map_df['formcode'].astype(str)
    map1 = map_df.set_index('index_field')['Route|FORM']
    return map1


def get_frequency_map(map_file_name):
    map_df = pd.read_csv(map_file_name, sep='\t')
    map1 = map_df.set_index('frequencycode')['per day']
    return map1


def drug_administered(table_path, out_path, id2nr, route_form_map):
    #  Chanels:  date, drug code, dosage, ROUTE|FORM
    event_type = 'ev_medications_administered'
    sig = med_maps[event_type]
    time1 = time.time()
    print('Reading table for ' + event_type)
    raw_table = pd.read_csv(os.path.join(table_path, event_type), sep='\t', dtype=str)
    drug_df = raw_table[['pid', 'startdate', 'medicationcode', 'quantity_value', 'quantitiy_unitcodeHier', 'routecode', 'formcode']]
    #raw_table.fillna('_', inplace=True)
    drug_df['route_form'] = drug_df['routecode'].astype(str) + '_' + drug_df['formcode'].astype(str)
    drug_df['route_form'] = drug_df['route_form'].map(route_form_map)
    print(drug_df[drug_df['route_form'].isnull()].shape[0])
    print(drug_df[drug_df['route_form'].isnull()][['routecode', 'formcode']].drop_duplicates())

    drug_df['unit_dict'] = drug_df['quantitiy_unitcodeHier'].apply(lambda x: hier_field_to_dict(x))
    drug_df['dose'] = drug_df['unit_dict'].apply(lambda x: get_dict_item(x, '1'))
    drug_df['dose'] = drug_df['quantity_value'].astype(str) + '|' + drug_df['dose']
    drug_df['medialid'] = drug_df['pid'].astype(str).map(id2nr)
    drug_df = drug_df[drug_df['medialid'].notnull()]

    drug_df['signal'] = sig
    drug_df['empty_chanel'] = -1
    print('Throwing ' + str(drug_df[(drug_df['startdate'] <= '1900-01-01 00:00:00')].shape[0]) + ' recordes with ilegal date')
    drug_df = drug_df[drug_df['startdate'] > '1900-01-01 00:00:00']
    print('  going to sort and save signal ' + sig)
    cols = ['medialid', 'signal', 'startdate', 'medicationcode', 'dose', 'route_form', 'empty_chanel']
    drug_df.sort_values(by=['medialid', 'startdate'], inplace=True)
    # write_tsv(drug_df[cols], out_path, sig)
    print(os.path.join(out_path, sig))
    print(drug_df.shape[0])
    drug_df[cols].to_csv(os.path.join(out_path, sig), sep='\t', index=False, header=False, mode='w',
                         line_terminator='\n')

    print('   process signal ' + sig + ' in ' + str(time.time() - time1))


def drug_prescription(event_type, table_path, out_path, id2nr, route_form_map, freq_map):
    #  Chanels:  date, drug code, dosage, ROUTE|FORM, frequency
    time1 = time.time()
    sig = med_maps[event_type]
    print('Reading table for ' + event_type)
    raw_table = pd.read_csv(os.path.join(table_path, event_type), sep='\t', dtype=str)
    drug_df = raw_table[['pid', 'startdate', 'medicationcode', 'quantity_value', 'quantitiy_unitcodeHier',
                         'routecode', 'formcode', 'frequencycode']]
    #raw_table.fillna('_', inplace=True)

    drug_df['route_form'] = drug_df['routecode'].astype(str) + '_' + drug_df['formcode'].astype(str)
    drug_df['route_form'] = drug_df['route_form'].map(route_form_map)
    print(drug_df[drug_df['route_form'].isnull()].shape[0])
    print(drug_df[drug_df['route_form'].isnull()][['routecode', 'formcode']].drop_duplicates())

    drug_df['unit_dict'] = drug_df['quantitiy_unitcodeHier'].apply(lambda x: hier_field_to_dict(x))
    drug_df['dose'] = drug_df['unit_dict'].apply(lambda x: get_dict_item(x, '1'))
    drug_df['dose'] = drug_df['quantity_value'].astype(str) + '|' + drug_df['dose']

    drug_df['frequency'] = drug_df['frequencycode'].map(freq_map)
    print('Unmapped frequencies: ' + str(drug_df[drug_df['frequency'].isnull()]['frequency']))
    drug_df['frequency'].fillna(999, inplace=True)
    drug_df['medialid'] = drug_df['pid'].astype(str).map(id2nr)
    drug_df = drug_df[drug_df['medialid'].notnull()]
    print('Throwing ' + str(drug_df[(drug_df['startdate'] <= '1900-01-01 00:00:00')].shape[0]) + ' recordes with ilegal date')
    drug_df = drug_df[drug_df['startdate'] > '1900-01-01 00:00:00']
    drug_df['signal'] = sig
    print('  going to sort and save signal ' + sig)
    cols = ['medialid', 'signal', 'startdate', 'medicationcode', 'dose', 'route_form', 'frequency']
    drug_df.sort_values(by=['medialid', 'startdate'], inplace=True)
    write_tsv(drug_df[cols], out_path, sig)
    print('   process signal ' + sig + ' in ' + str(time.time() - time1))


def tables_to_drugs_signals():
    cfg = Configuration()
    raw_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    table_path = os.path.join(out_folder, 'raw_tables')
    final_path = os.path.join(out_folder, 'FinalSignals')
    route_form_map = get_route_form_map(os.path.join(code_path, 'route_form_mapping.txt'))
    freqmap = get_frequency_map(os.path.join(code_path, 'frequency_map.txt'))

    id2nr = get_id2nr_map()

    drug_administered(table_path, final_path, id2nr, route_form_map)
    #drug_prescription('ev_medications_recom', table_path, final_path, id2nr, route_form_map, freqmap)
    #drug_prescription('ev_medications_adm', table_path, final_path, id2nr, route_form_map, freqmap)
    #drug_prescription('ev_medications_orders', table_path, final_path, id2nr, route_form_map, freqmap)


if __name__ == '__main__':
    tables_to_drugs_signals()
