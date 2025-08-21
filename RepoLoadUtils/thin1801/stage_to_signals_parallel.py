import os
import re
import multiprocessing as mp
import pandas as pd
import numpy as np
import traceback
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, is_nan

special_sigs = ['ALCOHOL', 'SMOKING', 'BP']
alcohol_status_map = pd.Series({"N": 0, "D": 0, "Y": 1})
smoke_status_map = pd.Series({"N": 0, "D": 1, "Y": 2})

cfg = Configuration()
raw_path = fixOS(cfg.doc_source_path)
out_folder = fixOS(cfg.work_path)
code_folder = fixOS(cfg.code_folder)
ahd_path = os.path.join(out_folder, 'ahd_files')
medical_path = os.path.join(out_folder, 'medical_files')

if not (os.path.exists(raw_path)):
    raise NameError('config error - doc_apth don''t exists')
if not (os.path.exists(out_folder)):
    raise NameError('config error - out_path don''t exists')
if not (os.path.exists(code_folder)):
    raise NameError('config error - code_folder don''t exists')
if not (os.path.exists(ahd_path)):
    raise NameError('config error - Numeric don''t exists')

final_path = os.path.join(out_folder, 'FinalSignals')
# final_path ='C:\\\Temp\\\Labs\\'
existing_files = os.listdir(final_path)
ahd_staging_files = os.listdir(ahd_path)
med_staging_files = os.listdir(medical_path)

thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)
# convert all value_field to lists (even for length of one) for simpler code
thin_map['value_field'] = thin_map['value_field'].apply(lambda x: x if is_nan(x) else x.strip("][").replace("'", '').split(','))
thin_map = thin_map[(thin_map['source_file'] == 'ahd') | (thin_map['source_file'] == 'medical')]
#thin_map = thin_map[((thin_map['source_file'] == 'ahd') | (thin_map['source_file'] == 'medical')) & (thin_map['type'] == 'numeric')]
ahd_lookup_df = read_fwf('AHDlookups', raw_path)
units_map = ahd_lookup_df[ahd_lookup_df['datadesc'] == 'MEASURE_UNIT']
units_map = units_map.set_index('lookup')['lookupdesc']
know_fld = os.path.join(code_folder, '..\\common_knowledge')
if os.name == 'nt':
    know_fld = os.path.join(code_folder, '..\\common_knowledge')
else:
    know_fld = os.path.join(code_folder, '../common_knowledge')

unit_mult = read_tsv('unitTranslator.txt', code_folder, names=['signal', 'unit', 'mult', 'add'])
unit_know = read_tsv('signal_units.txt', know_fld, names=['Name', 'FinalUnit', 'Round', 'FinalRound'], header=0)

ahd_lookup_df['lookupdesc'] = ahd_lookup_df['lookupdesc'].str.replace(' ', '_')
ahd_lookup_df['lookupdesc'] = ahd_lookup_df['dataname'] + ':' + ahd_lookup_df['lookup']
ahd_lookup_map = ahd_lookup_df[['lookup', 'lookupdesc']].drop_duplicates(subset='lookup').set_index('lookup')[
    'lookupdesc']
missing_units = []


def describe_dict(sr, sig):
    desc_dict = sr.describe().to_dict()
    desc_dict['signal'] = sig
    return desc_dict


def get_cols(df_cols):
    cols = ['medialid', 'sig', 'eventdate']
    val_cols = [x for x in df_cols if 'value' in x]
    cols = cols + val_cols
    if 'filename' in df_cols:
        cols = cols + ['filename']
    if 'unit' in df_cols:
        cols = cols + ['unit']
    return cols


def read_for_signal_map(map_dict, source_files, source_path):
    ahdcode = '' if is_nan(map_dict['ahdcode']) else str(int(map_dict['ahdcode']))
    readcode = '' if is_nan(map_dict['readcode']) else map_dict['readcode']
    regex = map_dict['regex']
    value_field = map_dict['value_field']
    val_cols = []
    if is_nan(regex):
        files = [s for s in source_files if readcode in s and ahdcode in s]
    else:
        assert (ahdcode == '' and readcode == '')
        files = [s for s in source_files if bool(re.search(regex, s)) and ahdcode in s]
    # files = files[0:10]
    # sig_map_df = pd.DataFrame()
    if len(files) == 0:
        print("ERROR IN MAPPING FOR SIGANL " + map_dict['signal'])
        return pd.DataFrame(), None
    df_list = []
    stat_dict = {'signal': map_dict['signal'], 'files': len(files),
                 'map': readcode + '-' + ahdcode + '_ ' + str(value_field)}
    for file in files:
        try:
            print('  reading file ' + file)
            if map_dict['source_file'] == 'ahd':
                one_df = read_tsv(file, source_path,
                                  names=['medialid', 'eventdate', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'filename'],
                                  header=None)
            elif map_dict['source_file'] == 'medical':
                one_df = read_tsv(file, source_path,
                                  names=['medialid', 'eventdate', 'medcode', 'nhsspec', 'source'],
                                  header=None, dtype={'medialid': int, 'eventdate': int})
                one_df['filename'] = file
                one_df.rename(columns={'medcode': 'value1'}, inplace=True)
                val_cols = ['value1']
            #sig_map_df = sig_map_df.append(one_df, ignore_index=True)
            df_list.extend(one_df.to_dict(orient='recoreds'))
        except ValueError as ve:
            eprint('Error In reading file %s  for signal %s' % (file, map_dict['signal']))
            #traceback.print_exc()
            #raise
    sig_map_df = pd.DataFrame(df_list)
    sig_map_df = sig_map_df[(sig_map_df['eventdate'].notnull()) & (sig_map_df['medialid'].notnull())]
    sig_map_df['sig'] = map_dict['signal']
    if not is_nan(value_field):
        dict1 = {value_field[i].strip(): 'value'+str(i+1) for i in range(len(value_field))}
        sig_map_df.rename(columns=dict1, inplace=1)
    elif not is_nan(map_dict['value1']) and not is_nan(map_dict['value2']):
        assert ('quantity' in map_dict['signal'])
        sig_map_df['value1'] = map_dict['value1']
        sig_map_df['value2'] = map_dict['value2']
        if map_dict['value1'] == 100:
            assert(map_dict['source_file'] == 'ahd')
            sig_map_df.loc[sig_map_df['data1'] == 'Y', 'value1'] = 2
            sig_map_df.loc[sig_map_df['data1'] == 'D', 'value1'] = 1
            sig_map_df.loc[sig_map_df['data1'] == 'N', 'value1'] = 3
            sig_map_df['data2'] = pd.to_numeric(sig_map_df['data2'], errors='coerce')
            cond1 = (sig_map_df['data1'] == 'Y') | (sig_map_df['data1'] == 'D')  # Smoker
            cond2 = (sig_map_df['data2'].notnull() & (sig_map_df['data2'] > 0))  # quantity exists
            sig_map_df.loc[cond1 & cond2, 'value2'] = sig_map_df[(cond1 & cond2)]['data2']
        val_cols = ['value1', 'value2']

    elif map_dict['source_file'] == 'ahd':
        sig_map_df['filename_list'] = sig_map_df['filename'].str.split('-')
        sig_map_df['value1'] = sig_map_df['filename_list'].apply(lambda x: x[0])
        val_cols = ['value1']

    if map_dict['signal'] == 'ALCOHOL':
        sig_map_df['value1'] = sig_map_df['value1'].map(alcohol_status_map)
    elif map_dict['signal'] == 'SMOKING':
        sig_map_df['value1'] = sig_map_df['value1'].map(smoke_status_map)

    if not is_nan(value_field):
        for i in range(1, len(value_field)+1):
            val = 'value'+str(i)
            val_cols.append(val)
            if map_dict['type'] == 'numeric':
                sig_map_df[val] = pd.to_numeric(sig_map_df[val], errors='coerce')
        if map_dict['type'] == 'numeric':
            stat_dict['null_values'] = sig_map_df[sig_map_df[val_cols].isnull().all(axis=1)].shape[0]
            sig_map_df = sig_map_df[~sig_map_df[val_cols].isnull().all(axis=1)]
        elif map_dict['type'] == 'string':
            for v in val_cols:
                sig_map_df[v].fillna('EMPTY_THIN_FIELD', inplace=True)
    sig_map_df['eventdate'] = sig_map_df['eventdate'].astype(int)
    stat_dict['date_before_1900'] = sig_map_df[sig_map_df['eventdate'] < 19000101].shape[0]
    sig_map_df = sig_map_df[sig_map_df['eventdate'] >= 19000101]

    if map_dict['signal'] == 'BP':
        sig_map_df['value1'] = sig_map_df['value1'].where(sig_map_df['value1'].notnull(), -1).astype(int)
        sig_map_df['value2'] = sig_map_df['value2'].where(sig_map_df['value2'].notnull(), -2).astype(int)

    if is_nan(map_dict['unitcode_field']):
        sig_map_df['unitcode'] = 'MEA000'
    else:
        sig_map_df.rename(columns={map_dict['unitcode_field']: 'unitcode'}, inplace=1)
        sig_map_df['unitcode'].fillna('MEA000', inplace=True)
        sig_map_df['unitcode'] = sig_map_df['unitcode'].replace('<None>', 'MEA000')


    cols = ['medialid', 'sig', 'eventdate'] + val_cols + ['unitcode', 'filename']
    stat_dict['save_count'] = sig_map_df.shape[0]
    return sig_map_df[cols], stat_dict


def unit_convert(sig, signal_df, rnd, frnd, thin_unit_convert, ahd_lookup):
    try:
        signal_df['unit'] = signal_df['unitcode'].map(ahd_lookup)
        # special cases
        if sig == 'Cholesterol_over_HDL':
            signal_df['unit'] = signal_df['unit'].where(~((signal_df['unit'] == '%') & (signal_df['value1'] < 10)), 'ratio')
        if sig == 'eGFR' or sig == 'GFR':
            signal_df['value1'] = signal_df['value1'].where(signal_df['value1'] <= 60, 60)
        if sig == 'T4':
            signal_df['unit'] = signal_df['unit'].where(signal_df['value1'] < 60, 'ug/d')
        if sig == 'Hemoglobin':
            signal_df['unit'] = signal_df['unit'].where(signal_df['value1'] < 100, 'g/L')
        if sig == 'HbA1C':
            signal_df['unit'] = signal_df['unit'].where((signal_df['value1'] < 40), 'IFCC')
        signal_df = pd.merge(signal_df, thin_unit_convert, how='left', left_on=['sig', 'unit'], right_on=['signal', 'unit'])
        signal_df = signal_df[(signal_df['mult'].notnull()) | (signal_df['add'].notnull())]
        signal_df['mult'].fillna(1, inplace=True)
        signal_df['add'] = signal_df['add'].astype(float).fillna(0)
        signal_df['mult_float'] = pd.to_numeric(signal_df['mult'], errors='coerce')
        val_cols = [x for x in signal_df.columns if 'value' in x]
        for val in val_cols:
            signal_df[val] = signal_df[val].round(rnd)  # round first before multiply
            orig_val = 'orig_val' + val[-1]
            signal_df.rename(columns={val: orig_val}, inplace=True)
            signal_df[val] = signal_df[orig_val] * signal_df['mult_float'] + signal_df['add']
            if 'Formula1' in signal_df['mult'].values:
                signal_df[val] = signal_df[val].where(
                    signal_df['mult'].str.contains('Formula1') == False, 100 / signal_df[orig_val])
            signal_df[val] = signal_df[val].round(frnd)  # round second after multiply
    except BaseException:
        eprint('Error In unit conversion for signal %s' % sig)
        traceback.print_exc()
        raise
    return signal_df


def process_signal(sig):
    if sig in existing_files or 'RC' in sig:  #  or sig == 'BP':
        print('signal ' + sig + ' already loaded')
        return
    one_signal_counts = pd.DataFrame()
    signal_df = pd.DataFrame()
    sig_maps = thin_map[thin_map['signal'] == sig]
    sig_type = sig_maps['type'].unique()
    assert (len(sig_type) == 1)
    sig_type = sig_type[0]
    print(' reading files for signal ' + sig)
    try:
        for _, smap in sig_maps.iterrows():
            if smap['source_file'] == 'ahd':
                staging_files = ahd_staging_files
                path = ahd_path
            else:
                staging_files = med_staging_files
                path = medical_path
            sig_df, stat_dict = read_for_signal_map(smap, staging_files, path)
            if sig_df.shape[0] == 0:
                continue
            signal_df = signal_df.append(sig_df, ignore_index=True)
            one_signal_counts = one_signal_counts.append(stat_dict, ignore_index=True)
    except BaseException:
        eprint('Error In unit conversion for signal %s' % sig)
        traceback.print_exc()
        raise
    # units conversions
    if sig_type == 'numeric':
        if sig not in unit_know['Name'].values:
            missing_units.append(sig)
        else:
            rnd = int(unit_know[unit_know['Name'] == sig].iloc[0]['Round'])
            if np.isnan(unit_know[unit_know['Name'] == sig].iloc[0]['FinalRound']):
                frnd = rnd
            else:
                frnd = int(unit_know[unit_know['Name'] == sig].iloc[0]['FinalRound'])
            print(' rnd=' + str(rnd) + ' frnd=' + str(frnd))
            signal_df = unit_convert(sig, signal_df, rnd, frnd, unit_mult, units_map)
    elif sig_type == 'string':
        signal_df['value_map'] = signal_df['value1'].map(ahd_lookup_map)
        signal_df['value1'] = signal_df['value_map'].where(signal_df['value_map'].notnull(), signal_df['value1'])

    cols = get_cols(signal_df.columns)
    print('  going to sort and save signal ' + sig)
    signal_df = signal_df[signal_df['medialid'].notnull()]
    signal_df.sort_values(by=['medialid', 'eventdate'], inplace=True)
    write_tsv(signal_df[cols], final_path, sig)
    return one_signal_counts


def code_files_to_signals():
    signal_counts = pd.DataFrame()
    signals = thin_map['signal'].unique()
    #signals = [x for x in signals if x not in existing_files and 'RC' not in x]
    signals = ['Height']  # , 'Alcohol_quantity']
    pool = mp.Pool(processes=4)
    result_list = pool.map(process_signal, signals)
    for res in result_list:
        signal_counts.append(res, ignore_index=True)

    write_tsv(signal_counts, out_folder, 'labs_counts.csv', headers=True)
    print('Signal with no define units ' + str(missing_units))


if __name__ == '__main__':
    code_files_to_signals()
