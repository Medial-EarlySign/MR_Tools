import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS, read_tsv, is_nan, eprint, append_sort_write_tsv
from generate_id2nr import get_id2nr_map

special_cases = ['BYEAR']


def get_cols(df_cols):
    cols = ['medialid', 'signal']
    val_cols = [x for x in df_cols if 'chanel' in x]
    val_cols.sort()
    cols = cols + val_cols
    if 'source' in df_cols:
        cols = cols + ['source']
    if 'unit' in df_cols:
        cols = cols + ['unit']
    return cols


def special_cases_fixes(sig_df, sig):
    if sig == 'BYEAR':
        sig_df['chanel1'] = sig_df['chanel1'].str[:4]
    return sig_df


def unit_convert(sig, signal_df, rnd, frnd, rambam_unit_convert):
    try:
        signal_df['unit'] = signal_df['unit'].str.lower().str.strip()
        signal_df = pd.merge(signal_df, rambam_unit_convert, how='left', left_on=['signal', 'unit'], right_on=['signal', 'unit'])
        signal_df = signal_df[(signal_df['mult'].notnull()) | (signal_df['add'].notnull())]
        signal_df['mult'].fillna(1, inplace=True)
        signal_df['add'] = signal_df['add'].astype(float).fillna(0)
        signal_df['mult_float'] = pd.to_numeric(signal_df['mult'], errors='coerce')
        val_cols = [x for x in signal_df.columns if 'chanel' in x]
        for val in val_cols:
            if all(pd.to_numeric(signal_df[val], errors='coerce').isnull()):
                continue
            signal_df[val] = pd.to_numeric(signal_df[val], errors='coerce')
            signal_df[val] = signal_df[val].round(rnd)  # round first before multiply
            orig_val = 'orig_val' + val[-1]
            signal_df.rename(columns={val: orig_val}, inplace=True)
            signal_df[val] = signal_df[orig_val] * signal_df['mult_float'] + signal_df['add']
            if 'Formula1' in signal_df['mult'].values:
                signal_df[val] = signal_df[val].where(
                    signal_df['mult'].str.contains('Formula1')==False, 100 / signal_df[orig_val])
            signal_df[val] = signal_df[val].round(frnd)  # round second after multiply
        signal_df['unit'] = signal_df['unit'].where(signal_df['unit'] != 'null', 'null_value')
    except BaseException:
        eprint('Error In unit conversion for signal %s' % sig)
        traceback.print_exc()
        raise
    return signal_df


def read_one_signal(signal, type_map, raw_table):
    signal_df = pd.DataFrame()
    sig_maps = type_map[type_map['signal'] == signal]
    for _, map_dict in sig_maps.iterrows():
        #print(map_dict)
        chanels = [map_dict[x] for x in map_dict.keys() if 'chanel' in x and not is_nan(map_dict[x])]
        chanels_dict = {map_dict[x]: x for x in map_dict.keys() if 'chanel' in x and not is_nan(map_dict[x])}
        if not is_nan(map_dict['filter_field']):
            sig_map_df = raw_table[raw_table[map_dict['filter_field']].astype(str) == str(map_dict['filter_value'])]
        else:
            chanels.insert(0, 'pid')
            sig_map_df = raw_table[chanels]
        sig_map_df.rename(columns=chanels_dict, inplace=True)
        if map_dict['event_type'] != 'demographics':
            sig_map_df['source'] = map_dict['event_type']
        if not is_nan(map_dict['unit_field']):
            sig_map_df.rename(columns={map_dict['unit_field']: 'unit'}, inplace=True)
        signal_df = signal_df.append(sig_map_df, ignore_index=True)
    signal_df['signal'] = signal
    if signal in special_cases:
        signal_df = special_cases_fixes(signal_df, signal)
    return signal_df


def tables_to_signal_files():
    cfg = Configuration()
    raw_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    table_path = os.path.join(out_folder, 'raw_tables')

    print(code_folder)
    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - code_folder don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - Numeric don''t exists')

    final_path = os.path.join(out_folder, 'FinalSignals')
    existing_files = os.listdir(final_path)
    rambam_map = read_tsv('rambam_signal_map.csv', code_folder, header=0)

    know_fld = fixOS(os.path.join(code_folder, '..\\common_knowledge'))
    unit_mult = read_tsv('unitTranslator.txt', code_folder, names=['signal', 'unit', 'mult', 'add'], header=0)
    unit_mult['unit'] = unit_mult['unit'].str.lower().str.strip()
    unit_know = read_tsv('signal_units.txt', know_fld, names=['Name', 'FinalUnit', 'Round', 'FinalRound'], header=0)
    id2nr = get_id2nr_map()
    signal_counts = pd.DataFrame()
    missing_units = []
    raw_files = os.listdir(table_path)
    for event_type, type_grp in rambam_map.groupby('event_type'):
        signals = type_grp['signal'].unique()
        if set(signals).issubset(set(existing_files)): #and 'Glucose' not in signals and 'PROCEDURE' not in signals:
            print('signals ' + str(signals) + ' already loaded')
            continue
        files = [f for f in raw_files if f.startswith(event_type)]
        loop_num = 0
        for file in files:
            print('Reading table for ' + file)
            raw_table = pd.read_csv(os.path.join(table_path, file), sep='\t', dtype=str)
            signals = type_grp['signal'].unique()
            print(signals)
            for sig in signals:
                time1 = time.time()
                print('processing signal ' + sig)
                if loop_num == 0:
                    if sig in existing_files and sig != 'Glucose' and sig != 'PROCEDURE':
                        print('signal ' + sig + ' already loaded')
                        continue
                signal_df = read_one_signal(sig, type_grp, raw_table)
                signal_df['medialid'] = signal_df['pid'].astype(str).map(id2nr)
                print('medialid not found to ' + str(signal_df[signal_df['medialid'].isnull()].shape[0]) + ' pids')
                # units conversions
                if event_type in ['ev_measurements_numeric', 'ev_lab_results_numeric']:
                    if sig not in unit_know['Name'].values:
                        missing_units.append(sig)
                    else:
                        rnd = int(unit_know[unit_know['Name'] == sig].iloc[0]['Round'])
                        if np.isnan(unit_know[unit_know['Name'] == sig].iloc[0]['FinalRound']):
                            frnd = rnd
                        else:
                            frnd = int(unit_know[unit_know['Name'] == sig].iloc[0]['FinalRound'])
                        print(' rnd=' + str(rnd) + ' frnd=' + str(frnd))
                        signal_df = unit_convert(sig, signal_df, rnd, frnd, unit_mult)
                    signal_df = signal_df[signal_df['chanel2'] > '1840-01-01 00:00:00']
                else:
                    val_cols = [x for x in signal_df.columns if 'chanel' in x]
                    for val in val_cols:
                        signal_df[val] = signal_df[val].where(signal_df[val].astype(str).str.lower() != 'none', 'EMPTY_VALUE')
                cnl_cols = [x for x in signal_df.columns if 'chanel' in x]
                signal_df = signal_df.replace('Null', np.nan)
                signal_df.dropna(subset=cnl_cols, inplace=True)
                cols = get_cols(signal_df.columns)
                print('  going to sort and save signal ' + sig)
                signal_df = signal_df[signal_df['medialid'].notnull()]
                #signal_df.sort_values(by=['medialid', 'chanel1'], inplace=True)
                append_sort_write_tsv(signal_df[cols], final_path, sig, cols, ['medialid', 'chanel1'])
                print('   process signal ' + sig + ' from file ' + file + ' in ' + str(time.time() - time1))
                loop_num += 1
            del raw_table
        print('Signals with no Units defined : ' + str(missing_units))
        print('DONE ' + event_type)


if __name__ == '__main__':
    tables_to_signal_files()