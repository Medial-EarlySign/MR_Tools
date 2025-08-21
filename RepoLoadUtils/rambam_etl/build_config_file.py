import sys
import os
import re
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name


def get_folder_data_list(fld_name, files_regex=None):
    signals_path = os.path.join(work_folder, fld_name)
    files = os.listdir(signals_path)
    if files_regex:
        files = [s for s in files if bool(re.search(files_regex, s))]
    data_list = []

    for file in files:
        st = 'DATA\t../' + fld_name + '/' + file
        data_list.append(st)
    return data_list


def get_dict_list(dict_fld):
    signals_path = os.path.join(config_folder, dict_fld)
    def_files = [x for x in os.listdir(signals_path) if 'set' not in x]
    set_file = [x for x in os.listdir(signals_path) if 'set' in x]
    data_list = []
    for file in def_files:
        st = 'DICTIONARY\t' + dict_fld + '/' + file
        data_list.append(st)
    for file in set_file:
        st = 'DICTIONARY\t' + dict_fld + '/' + file
        data_list.append(st)
    return data_list


def add_const_lines():
    cons_list = ['#', '# convert config file', '#', 'DESCRIPTION\tRAMBAM data - full version',
                 'RELATIVE \t1', 'SAFE_MODE\t1', 'MODE\t3', 'PREFIX\trambam_rep', 'CONFIG\trambam.repository',
                 'SIGNAL\trambam.signals', 'FORCE_SIGNAL\tGENDER, BYEAR',
                 'DIR\t/server/Work/Users/Tamar/rambam_load/rep_configs',
                 'TIME_UNIT\tMinutes',
                 'OUTDIR\t/server/Work/CancerData/Repositories/Rambam/rambam_feb2019'
                 ]
    return cons_list


if __name__ == '__main__':
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    config_folder = os.path.join(work_folder, 'rep_configs')
    out_file = os.path.join(config_folder, 'rambam.convert_config')

    fld_list = ['FinalSignals']
    dict_fld_name = 'dicts'

    final_list = add_const_lines()
    dict_list = get_dict_list(dict_fld_name)
    final_list.extend(dict_list)

    for fld in fld_list:
        dat_files_list = get_folder_data_list(fld)
        final_list.extend(dat_files_list)
        final_list.extend(['\n'])

    with open(out_file, 'w', newline='\n') as f:
        for item in final_list:
            f.write("%s\n" % item)
