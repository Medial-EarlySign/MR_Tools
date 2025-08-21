import pandas as pd
import os
import sys
import time
#sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces, is_nan
from const_and_utils import read_fwf, read_fwf_cols
from staging_config import ThinDemographic, ThinLabs, ThinReadcodes, ThinLabsCat
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files, remove_errors, regex_to_file, handel_special_cases, unit_convert
from stage_to_cancer_location import codes_to_cancer_location
from load_therapy import load_therapy


def numeric_labs_to_files(cfg, th_def):
    special_cases = ['CHADS2', 'CHADS2_VASC']
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == th_def.TABLE)
    th_map_numeric = th_map[(th_map['type'] == 'numeric') & lab_chart_cond & ~(th_map['signal'].isin(special_cases))]
    th_map_numeric = th_map_numeric[th_map_numeric['signal'] != 'STOPPED_SMOKING']
    print(th_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    numeric_to_files(th_def, th_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder, suff='_'+th_def.TABLE+'_')
    for sc in special_cases:
        th_map_numeric = th_map[(th_map['type'] == 'numeric') & lab_chart_cond & (th_map['signal'] == sc)]
        numeric_to_files(th_def, th_map_numeric, unit_mult, None, id2nr, out_folder, suff='_' + th_def.TABLE + '_', main_cond='source')



def cat_labs_to_files(cfg, th_def):
    #th_def = ThinLabs()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == 'thinlabs')
    if th_def.TABLE == 'thinlabs':
        lab_chart_cond2 = (th_map['code'].str.contains('_data'))
    else:
        lab_chart_cond2 = (~(th_map['code'].str.contains('_data')))
    th_map_numeric = th_map[(th_map['type'] == 'string') & lab_chart_cond & lab_chart_cond2]
    print(th_map_numeric)
    id2nr = get_id2nr_map()
    categories_to_files(th_def, th_map_numeric, id2nr, out_folder)


def thin_regex_to_files(cfg, th_def):
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == th_def.TABLE)
    th_map_re = th_map[(th_map['type'] == 'regex') & lab_chart_cond & (th_map['signal'] == 'RC')]
    print(th_map_re)
    id2nr = get_id2nr_map()
    regex_to_file(th_def, th_map_re, id2nr, out_folder, suff='_'+th_def.TABLE+'_')


def thin_demographic_to_file(cfg):
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    th_def = ThinDemographic()
    id2nr = get_id2nr_map()
    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    #demo_cond = (th_map['source'] == 'thindemographic')
    demo_cond = (th_map['source'] == 'thindemographic') & (th_map['signal'] != 'Censor')
    th_map_demo = th_map[demo_cond]
    print(th_map_demo)
    demographic_to_files(th_def, th_map_demo, id2nr, out_folder)


def all_labs_to_files(cfg, th_def):
    raw_path = fixOS(cfg.doc_source_path)
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    mapped_code = th_map[['code']]
    mapped_code['only_code'] = th_map['code'].where(~th_map['code'].str.contains('data'), th_map['code'].str[0:10])

    read_codes = read_fwf('Readcodes', raw_path)
    read_codes = read_codes[~read_codes['medcode'].isin(mapped_code['only_code'])][['medcode']]
    read_codes.rename(columns={'medcode': 'code'}, inplace=True)

    ahd_codes = read_fwf('AHDCodes', raw_path)
    ahd_codes = ahd_codes[~ahd_codes['ahdcode'].astype(str).isin(mapped_code['only_code'])][['ahdcode']]
    ahd_codes.rename(columns={'ahdcode': 'code'}, inplace=True)
    ahd_codes['code'] = ahd_codes['code'].astype(str) + '_data2'

    not_mapped_codes = pd.concat([ahd_codes, read_codes])
    not_mapped_codes['signal'] = 'Labs'
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    numeric_to_files(th_def, not_mapped_codes, unit_mult, special_factors_signals, id2nr, out_folder)


def rc_to_files(cfg, ext):
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(fixOS(cfg.work_path), 'FinalSignals')
    id2nr = get_id2nr_map()
    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    if ext == 'ahd':
        lab_chart_cond = (th_map['source'] == 'thinlabs')
        th_map_re = th_map[(th_map['type'] == 'regex') & lab_chart_cond & (th_map['signal'] != 'RC')]
        print(th_map_re)
        load_ahd_rc(th_map_re, id2nr, out_folder)
    else:
        lab_chart_cond = (th_map['source'] == 'thinreadcodes')
        th_map_re = th_map[(th_map['type'] == 'regex') & lab_chart_cond & (th_map['signal'] != 'RC')]  #& (th_map['signal'].isin(['RC', 'RC_Diagnosis']))]
        print(th_map_re)
        load_medical_rc(th_map_re, id2nr, out_folder)


def load_ahd_rc(signal_map, id2nr_map, out_folder):
    cfg = Configuration()
    data_path = fixOS(cfg.raw_source_path)

    cnt = 0
    print(data_path)
    prefixs = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    prefixs = ['f', 'g', 'h', 'i', 'j']
    for prf in prefixs:
        prf_df = pd.DataFrame()
        in_file_names = list(filter(lambda f: f.startswith('ahd.'+prf), os.listdir(data_path)))
        start_parc = 'ahd.a6000'
        for in_file_name in in_file_names:
            cnt = cnt + 1
            if in_file_name < start_parc:
                print(str(cnt) + ") skiping file " + in_file_name)
                continue
            pracid = in_file_name[-5:]
            print(str(cnt) + ") reading from " + in_file_name)
            time1 = time.time()
            ahd_df = read_fwf_cols('ahd', data_path, ['patid','eventdate', 'medcode', 'ahdflag'], in_file_name)
            time2 = time.time()
            print('    load ahd file ' + str(ahd_df.shape[0]) + ' records in ' + str(time2 - time1))
            # Setting for all ahd
            ahd_df = ahd_df[(ahd_df['ahdflag'] == 'Y')]

            ahd_df.loc[:, 'combid'] = pracid + ahd_df['patid'].astype(str)
            ahd_df.loc[:, 'medialid'] = ahd_df['combid'].astype(str).map(id2nr_map)
            cond = (ahd_df['medialid'].isnull())
            print('Removing due to null id ' + str(ahd_df[cond].shape[0]))
            ahd_df = ahd_df[~cond]

            # Fix cases where month and/or day = 00
            if in_file_name == 'ahd.g9974':
                ahd_df = ahd_df[ahd_df['eventdate'].str.isdigit()]
                ahd_df['eventdate'] = ahd_df['eventdate'].astype(int)
            ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 10000) > 0 else x + 100)
            ahd_df['eventdate'] = ahd_df['eventdate'].apply(lambda x: x if (x % 100) > 0 else x + 1)

            cond = (ahd_df['eventdate'] < 19000000)
            print('Removing due to illigal date ' + str(ahd_df[cond].shape[0]))
            ahd_df = ahd_df[~cond]

            ahd_df['source'] = in_file_name
            prf_df = prf_df.append(ahd_df, ignore_index=True, sort=False)
        prf_df.sort_values(['medialid', 'eventdate'], inplace=True)
        prf_df = prf_df[(prf_df['medcode'].notnull()) & (prf_df['medcode'].str.strip != '')]
        for sig, sig_grp in signal_map.groupby('signal'):
            codes_list = [str(x) for x in sig_grp['code'].values]
            print(sig, codes_list)
            for rx in codes_list:
                print(rx)
                prf_df.loc[prf_df['medcode'].str.contains(rx), sig] = 1
            sig_df = prf_df[prf_df[sig] == 1].copy()
            if sig_df.empty:
                continue
            sig_df.loc[:, 'signal'] = sig
            filename = sig + '_' + prf
            write_tsv(sig_df[['medialid','signal', 'eventdate', 'medcode', 'source']], out_folder, filename, mode='w')


def load_medical_rc(signal_map, id2nr_map, out_folder):
    cfg = Configuration()
    data_path = fixOS(cfg.raw_source_path)

    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')

    cnt = 0
    prefixs = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    #prefixs = ['f', 'g', 'h', 'i', 'j']
    for prf in prefixs:
        prf_df = pd.DataFrame()
        in_file_names = list(filter(lambda f: f.startswith('medical.'+prf), os.listdir(data_path)))
        for in_file_name in in_file_names:
            cnt = cnt + 1
            pracid = in_file_name[-5:]

            print(str(cnt) + ") reading from " + in_file_name)
            time1 = time.time()
            medical_df = read_fwf_cols('medical', data_path, ['patid', 'eventdate', 'medcode', 'medflag'], in_file_name)
            time2 = time.time()
            print('    load ahd file ' + str(medical_df.shape[0]) + ' records in ' + str(time2 - time1))
            medical_df = medical_df[medical_df['medflag'].isin(['R', 'S'])]
            medical_df.loc[:, 'combid'] = pracid + medical_df['patid'].astype(str)
            medical_df.loc[:, 'medialid'] = medical_df['combid'].astype(str).map(id2nr_map)
            cond = (medical_df['medialid'].isnull())
            print('Removing due to null id ' + str(medical_df[cond].shape[0]))
            medical_df = medical_df[~cond]

            medical_df['eventdate'] = medical_df['eventdate'].apply(lambda x: x if ((x % 10000) > 0) | (x == 0) else x + 100)
            medical_df['eventdate'] = medical_df['eventdate'].apply(lambda x: x if ((x % 100) > 0) | (x == 0) else x + 1)
            cond = (medical_df['eventdate'] < 19000000)
            print('Removing due to illigal date ' + str(medical_df[cond].shape[0]))
            medical_df = medical_df[~cond]

            medical_df['source'] = in_file_name
            prf_df = prf_df.append(medical_df[['medialid', 'eventdate', 'medcode', 'source']], ignore_index=True, sort=False)
        prf_df.sort_values(['medialid', 'eventdate'], inplace=True)

        for sig, sig_grp in signal_map.groupby('signal'):
            codes_list = [str(x) for x in sig_grp['code'].values]
            print(sig, codes_list)
            for rx in codes_list:
                prf_df.loc[prf_df['medcode'].str.contains(rx), 'sig'] = 1

            sig_df = prf_df[prf_df['sig'] == 1].copy()
            sig_df.loc[:, 'signal'] = sig
            filename = sig + '_' + prf + '_' + 'medical'
            write_tsv(sig_df[['medialid', 'signal', 'eventdate', 'medcode', 'source']], out_folder, filename, mode='w')


if __name__ == '__main__':
    cfg = Configuration()
    numeric_labs_to_files(cfg, ThinLabs())
    numeric_labs_to_files(cfg, ThinReadcodes())
    thin_regex_to_files(cfg, ThinLabs())
    thin_regex_to_files(cfg, ThinReadcodes())
    thin_demographic_to_file(cfg) # - failed on Censor
    cat_labs_to_files(cfg, ThinLabsCat())
    cat_labs_to_files(cfg, ThinLabs())
    ##all_labs_to_files(cfg, ThinLabs())
    codes_to_cancer_location(ThinReadcodes())
    rc_to_files(cfg, 'ahd')
    rc_to_files(cfg, 'medical')
    load_therapy()


