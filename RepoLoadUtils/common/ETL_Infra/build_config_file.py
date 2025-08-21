import os
import re
import pandas as pd
from .env import *

def get_folder_data_list(work_folder, files_regex=None, to_remove=None):
    signals_path = os.path.join(work_folder, 'FinalSignals')
    files = os.listdir(signals_path)
    files.sort()
    if files_regex:
        files = [s for s in files if bool(re.search(files_regex, s))]
    data_list = []

    for file in files:
        if 'error' in file.lower():
            continue
        if file == 'ID2NR':
            continue
        if os.path.isdir(os.path.join(signals_path, file)):
            continue
        st = 'DATA\t../' + os.path.join('FinalSignals', file)
        if to_remove and file in to_remove:
            st = '# ' + st
        data_list.append(st)
    return data_list


def get_dict_list(config_folder):
    dicts_path = os.path.join(config_folder, 'dicts')
    dict_files = [f for f in os.listdir(dicts_path) if f.startswith('dict')]
    def_files = [x for x in dict_files if 'set' not in x]
    set_file = [x for x in dict_files if 'set' in x]
    data_list = []
    for file in def_files:
        st = 'DICTIONARY\t' + os.path.join('dicts', file)
        data_list.append(st)
    for file in set_file:
        st = 'DICTIONARY\t' + os.path.join('dicts', file)
        data_list.append(st)
    return data_list


def add_const_lines(dest_rep, config_folder, dest_folder):
    forced_line = 'FORCE_SIGNAL\tGENDER,BDATE'
    if 'SEX' in FORCED_SIGNALS:
        forced_line='FORCE_SIGNAL\tSEX,BDATE'
    cons_list = ['#', '# convert config file', '#', 'DESCRIPTION\t'+dest_rep.upper() + ' data - full version',
                 'RELATIVE \t1', 'SAFE_MODE\t1', 'MODE\t3', 'PREFIX\t'+os.path.join('data', dest_rep+'_rep'), 'CONFIG\t'+dest_rep+'.repository',
                 'SIGNAL\t'+dest_rep+'.signals', forced_line,
                 'DIR\t'+config_folder,
                 'OUTDIR\t'+dest_folder
                 ]
    return cons_list


def create_convert_config_file(work_folder, dest_folder, dest_rep, to_remove=[], to_load=[]):
    config_folder = os.path.join(work_folder, 'rep_configs')
    out_file = os.path.join(config_folder, dest_rep+'.convert_config')
    os.makedirs(os.path.join(dest_folder, 'data'), exist_ok=True)

    final_list = add_const_lines(dest_rep,config_folder, dest_folder)
    dict_list = get_dict_list(config_folder)
    final_list.extend(dict_list)
    
    if len(to_load) == 0:
        dat_files_list = get_folder_data_list(work_folder, to_remove=to_remove)
    else:
        to_load_s=set(to_load)
        if 'SEX' in FORCED_SIGNALS:
            to_load_s.add('SEX')
        else:
            to_load_s.add('GENDER')
        to_load_s.add('BDATE')
        p_regex_files='|'.join(list(map(lambda x: '^' + x,list(to_load_s))))
        dat_files_list = get_folder_data_list(work_folder, files_regex=p_regex_files)
    
    final_list.extend(dat_files_list)
    final_list.extend(['\n'])

    with open(out_file, 'w', newline='\n') as f:
        for item in final_list:
            f.write("%s\n" % item)
        if len(to_load)>0:
            f.write('LOAD_ONLY\t%s\n'%(','.join(to_load)))