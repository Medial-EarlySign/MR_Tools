import sys
import os
import re
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name


def lines_in_file(file_name):
    print(file_name)
    with open(file_name) as f:
        sm = sum(1 for _ in f)
    return sm


def count_lines(files_df, path):
    files_df['lines'] = files_df.apply(lambda x: lines_in_file(os.path.join(path, x['folder_file'])), axis=1)


def fix_unit_translator():
    unit_file = 'unitTranslator.txt'
    thin_code_to_signal = 'W:\\CancerData\\Repositories\\THIN\\thin_jun2017\\codes_to_signals'
    code_to_signal = pd.read_csv(thin_code_to_signal, sep='\t', names=['from', 'to'])
    code_to_signal_map = code_to_signal.set_index('from')['to']

    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    unit_df = read_tsv(unit_file, code_folder, names=['signal', 'unit', 'mult'])

    unit_df['mmapped'] = unit_df['signal'].map(code_to_signal_map)
    unit_df['signal'] = unit_df['signal'].where(unit_df['mmapped'].isnull(), unit_df['mmapped'])
    full_file = os.path.join(code_folder, unit_file)
    unit_df[['signal', 'unit', 'mult']].to_csv(full_file, sep='\t', index=False, header=False, mode='w')


def fix_numeric_mapping():
    map_file = 'numeric_mapping.txt'
    thin_code_to_signal = 'W:\\CancerData\\Repositories\\THIN\\thin_jun2017\\codes_to_signals'
    code_to_signal = pd.read_csv(thin_code_to_signal, sep='\t', names=['from', 'to'])
    code_to_signal_map = code_to_signal.set_index('from')['to']

    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    file_to_sig = read_tsv(map_file, code_folder, names=['InFile', 'OutFile'])

    file_to_sig['mapped'] = file_to_sig['OutFile'].map(code_to_signal_map)
    file_to_sig['OutFile'] = file_to_sig['OutFile'].where(file_to_sig['mapped'].isnull(), file_to_sig['mapped'])
    full_file = os.path.join(code_folder, map_file)
    file_to_sig[['InFile', 'OutFile']].to_csv(full_file, sep='\t', index=False, header=True, mode='w')

def build_this_trans_and_signal_knowladge():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    unit_file = 'unitTranslator.txt'
    thin_signals_info = 'Instructions.txt'
    know_fld = os.path.join(code_folder, '..\common_knowledge')

    thin_code_to_signal = 'W:\\CancerData\\Repositories\\THIN\\thin_jun2017\\codes_to_signals'
    code_to_signal = pd.read_csv(thin_code_to_signal, sep='\t', names=['from', 'to'])
    code_to_signal_map = code_to_signal.set_index('from')['to']
    thin_labs_df = read_tsv(thin_signals_info, code_folder,
                            names=['Name', 'Unit', 'Resolution', 'Ignore', 'Factors', 'FinalFactor', 'SupposeMean',
                                   'TrimMax', 'FinalUnit'], header=0)

    thin_labs_df['mapped'] = thin_labs_df['Name'].map(code_to_signal_map)
    thin_labs_df['Name'] = thin_labs_df['Name'].where(thin_labs_df['mapped'].isnull(), thin_labs_df['mapped'])

    unit_df = read_tsv(unit_file, code_folder, names=['signal', 'unit', 'mult', 'add'])

    numeric_signal_knowladge = thin_labs_df[['Name', 'FinalUnit', 'Resolution']]
    merged = unit_df.merge(numeric_signal_knowladge, how='left', right_on='Name', left_on='signal')
    merged2 = unit_df.merge(numeric_signal_knowladge, how='right', right_on='Name', left_on='signal')
    write_tsv(numeric_signal_knowladge, know_fld, 'signall_units.txt', headers=True)
    print(merged2[merged2['signal'].isnull()]['Name'])

def fix_null_in_numeric_mapping():
    map_file = 'numeric_mapping.txt'
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    file_to_sig = read_tsv(map_file, code_folder, names=['InFile', 'OutFile'])
    file_to_sig.fillna('NULL', inplace=True)

    full_file = os.path.join(code_folder, map_file)
    file_to_sig[['InFile', 'OutFile']].to_csv(full_file, sep='\t', index=False, header=True, mode='w')


def lab_signal_table():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    out_folder = 'C:\\\Temp\\'
    thin_signal_file = 'W:\\CancerData\\Repositories\\THIN\\thin_jun2017\\thin.signals'

    file_to_sig = read_tsv('numeric_mapping.txt', code_folder, names=['InFile', 'Signal'])
    thin_signal_df = pd.read_csv(thin_signal_file, sep='\t', names=['sig', 'Signal', 'code', 'type'],
                                 error_bad_lines=False)
    thin_signal_df = thin_signal_df[thin_signal_df['sig'] == 'SIGNAL']
    thin_signal_df['code'] = thin_signal_df['code'].astype(int)
    thin_signal_df['type'] = thin_signal_df['type'].astype(int)


    file_to_sig['LIST'] = file_to_sig['InFile'].str.split('-')
    file_to_sig['ahdcode'] = file_to_sig.apply(lambda row: row['LIST'][-1], axis=1)
    file_to_sig['readcode'] = file_to_sig.apply(lambda row: row['LIST'][-2][0:7], axis=1)
    file_to_sig['readcode1'] = file_to_sig.apply(lambda row: row['LIST'][-3][0:7], axis=1)
    file_to_sig['readcode'] = file_to_sig['readcode'].where(~file_to_sig['readcode'].str.startswith('_'), file_to_sig['readcode1'])
    file_to_sig['readcode'] = file_to_sig['readcode'].where(~file_to_sig['readcode'].str.startswith('i'),
                                                            file_to_sig['readcode1'])
    out_df = file_to_sig[(file_to_sig['Signal'] != 'TBD') & file_to_sig['Signal'].notnull()][['Signal', 'ahdcode', 'readcode']]
    out_df = out_df.groupby('Signal').agg(lambda x: list(set(x.tolist())))
    out_df['source'] = 'AHD/TEST'
    out_df.reset_index(inplace=True)
    out_df['Signal'] = out_df['Signal'].str.replace('/', '_over_')

    out_df = out_df.merge(thin_signal_df, how='left', on='Signal')

    cols = ['Signal', 'code', 'type', 'source', 'ahdcode', 'readcode']
    write_tsv(out_df[cols], out_folder, 'labs_signal_list.csv', headers=True)
    print(out_df)


def create_count_file(folder):
    print(folder)
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    numeric_path = os.path.join(out_folder, folder)
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - code_folder don''t exists')
    if not (os.path.exists(numeric_path)):
        raise NameError('config error - Numeric don''t exists')

    staging_files = os.listdir(numeric_path)
    files_df = pd.DataFrame(data=staging_files, columns=['folder_file'])
    count_lines(files_df, numeric_path)
    files_df['nonzero'] = files_df['lines']
    write_tsv(files_df[['folder_file', 'lines', 'nonzero']], out_folder, folder+'line_count.csv')



def compare_signal_table():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    out_folder = fixOS(cfg.work_path)
    thin_signal_file = 'W:\\CancerData\\Repositories\\THIN\\thin_jun2017\\thin.signals'
    sig_folders = ['NumericSignals', 'NonNumericSignals', 'SpecialSignals', 'therapy', 'Readcode', 'imms', 'medical']
    thin_signal_df = pd.read_csv(thin_signal_file, sep='\t', names=['sig', 'Signal', 'code', 'type', 'comments'],
                                 error_bad_lines=False)
    thin_signal_df = thin_signal_df[thin_signal_df['sig'] == 'SIGNAL']
    thin_signal_df['code'] = thin_signal_df['code'].astype(int)
    thin_signal_df['type'] = thin_signal_df['type'].astype(int)

    signals_files = []
    for fld in sig_folders:
        raedcodes_path = os.path.join(out_folder, fld)
        signals_files += os.listdir(raedcodes_path)

    new_signals = pd.DataFrame(columns=['new_sig'], data=signals_files)

    sig_comp = thin_signal_df.merge(new_signals, how='outer', left_on='Signal', right_on='new_sig')
    print(sig_comp)

    write_tsv(sig_comp, 'c:\\Temp\\', 'signal_comp.csv', headers=True)


def check_signal_units(signal):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    numeric_fld = os.path.join(out_folder, 'NumericSignals')

    sig_df = read_tsv(signal, numeric_fld,names=['medialid', 'sig', 'eventdate', 'val', 'file', 'units'], header=0)
    units = sig_df['units'].unique()
    for un in units:
        un_df = sig_df[sig_df['units'] == un]
        print(un)
        print('count=' + str(un_df.shape[0]) + ' mean=' + str(un_df['val'].mean()) + ' median=' +
              str(un_df['val'].median()) + ' max=' + str(un_df['val'].max()), ' min=' + str(un_df['val'].min()))
    #print(sig_df['units'].value_counts())


def check_signal_units_raw(signal):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    raw_path = fixOS(cfg.doc_source_path)
    numeric_path = os.path.join(out_folder, 'Numeric')
    file_to_sig = read_tsv('numeric_mapping.txt', code_folder, names=['InFile', 'OutFile'])
    ahd_lookup_df = read_fwf('AHDlookups', raw_path)
    units_map = ahd_lookup_df[ahd_lookup_df['datadesc'] == 'MEASURE_UNIT']
    units_map = units_map.set_index('lookup')['lookupdesc']

    staging_files = os.listdir(numeric_path)
    files_df = pd.DataFrame(data=staging_files, columns=['folder_file'])
    files_df = files_df.merge(file_to_sig, how='left', left_on='folder_file', right_on='InFile')
    files_df = files_df[(files_df['OutFile'] != 'TBD') & (files_df['OutFile'].notnull())]
    sig_files = files_df[files_df['OutFile'] == signal]
    signal_df = pd.DataFrame()
    for file in sig_files['InFile'].unique():
        print('  reading file ' + file)
        one_df = read_tsv(file, numeric_path, names=['medialid', 'eventdate', 'value', 'unitcode', 'filename'],
                          header=0)
        signal_df = signal_df.append(one_df, ignore_index=True)
    signal_df['unit'] = signal_df['unitcode'].map(units_map)

    #sig_df = read_tsv(signal, numeric_fld,names=['medialid', 'sig', 'eventdate', 'val', 'file', 'units'], header=0)
    units = signal_df['unit'].unique()
    for un in units:
        un_df = signal_df[signal_df['unit'] == un]
        print(un)
        print('count=' + str(un_df.shape[0]) + ' mean=' + str(un_df['value'].mean()) + ' median=' +
              str(un_df['value'].median()) + ' max=' + str(un_df['value'].max()), ' min=' + str(un_df['value'].min()))
    #print(sig_df['units'].value_counts())


if __name__ == '__main__':
    #fix_numeric_mapping()
    #lab_signal_table()
    #create_count_file()
    #compare_signal_table()
    #fix_unit_translator()
    #check_signal_units_raw('Fev1')
    #check_signal_units('TEMP')
    #build_this_trans_and_signal_knowladge()
    #create_count_file('ahd_files')



    #######################
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)

    #sig = 'Proteinuria_State'
    #df1 = pd.read_csv('W:\\Users\\Coby\\CKD_present\\v_Proteinuria', sep='\t', names=['pid', 'sig', 'rem1', 'date', 'rem2', 'val'], header=1)
    #df1.sort_values(by=['pid', 'date'], inplace=True)
    #df1['sig'] = sig
    #write_tsv(df1[['pid', 'sig', 'date', 'val']], os.path.join(out_folder, 'FinalSignals'), sig)

    sig = 'eGFR_CKD_EPI'
    df1 = pd.read_csv('W:\\Users\\Coby\\CKD_present\\eGFR', sep='\t',
                      names=['pid', 'sig', 'rem1', 'date', 'rem2', 'val'], header=1)
    df1.sort_values(by=['pid', 'date'], inplace=True)
    df1['sig'] = sig
    write_tsv(df1[['pid', 'sig', 'date', 'val']], os.path.join(out_folder, 'FinalSignals'), sig)


    thin_signal_file = os.path.join(out_folder, 'rep_configs', 'thin.signals')
    config_file = os.path.join(out_folder, 'rep_configs', 'thin18.convert_config')

    thin_signal_df = pd.read_csv(thin_signal_file, sep='\t',usecols=[1, 2], names=['signal', 'num'], error_bad_lines=False, comment='#')
    config_df = pd.read_csv(config_file, sep='\t', names=['key', 'value'])
    config_df = config_df[config_df['key'] == 'DATA']
    config_df['split'] = config_df['value'].str.split('/')
    config_df['signal'] = config_df['split'].apply(lambda x: x[-1])
    mrg = thin_signal_df.merge(config_df, how='left', on='signal')
    print(mrg[mrg['key'].isnull()])





