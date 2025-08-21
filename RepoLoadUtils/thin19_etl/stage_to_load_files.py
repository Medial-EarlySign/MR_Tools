import pandas as pd
import os
import sys
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))

from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces, is_nan
from const_and_utils import read_fwf
from staging_config import ThinDemographic, ThinLabs, ThinReadcodes
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files, remove_errors, regex_to_file
from stage_to_cancer_location import codes_to_cancer_location
from load_therapy import load_therapy


def numeric_labs_to_files(th_def):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == th_def.TABLE)  # & (th_map['signal'] == 'Smoking_quantity')
    th_map_numeric = th_map[(th_map['type'] == 'numeric') & lab_chart_cond]
    print(th_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    numeric_to_files(th_def, th_map_numeric, unit_mult, id2nr, out_folder, suff='_'+th_def.TABLE+'_')


def cat_labs_to_files():
    th_def = ThinLabs()
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == 'thinlabs')
    th_map_numeric = th_map[(th_map['type'] == 'string') & lab_chart_cond]
    print(th_map_numeric)
    id2nr = get_id2nr_map()
    categories_to_files(th_def, th_map_numeric, id2nr, out_folder)


def thin_regex_to_files(th_def):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == th_def.TABLE)
    th_map_re = th_map[(th_map['type'] == 'regex') & lab_chart_cond]
    print(th_map_re)
    id2nr = get_id2nr_map()
    regex_to_file(th_def, th_map_re, id2nr, out_folder, suff='_'+th_def.TABLE+'_')


def thin_demographic_to_file():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    th_def = ThinDemographic()
    id2nr = get_id2nr_map()
    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    demo_cond = (th_map['source'] == 'thindemographic')
    demo_cond = (th_map['source'] == 'thindemographic') & (th_map['signal'] == 'Censor')
    th_map_demo = th_map[demo_cond]
    print(th_map_demo)
    demographic_to_files(th_def, th_map_demo, id2nr, out_folder)


def all_labs_to_files(th_def):
    cfg = Configuration()
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
    numeric_to_files(th_def, not_mapped_codes, unit_mult, id2nr, out_folder)



if __name__ == '__main__':
    #numeric_labs_to_files(ThinLabs())
    #numeric_labs_to_files(ThinReadcodes())
    #thin_regex_to_files(ThinLabs())
    #thin_regex_to_files(ThinReadcodes())
    #thin_demographic_to_file()
    #cat_labs_to_files()
    all_labs_to_files(ThinLabs())
    #codes_to_cancer_location(ThinReadcodes())
    #load_therapy()


