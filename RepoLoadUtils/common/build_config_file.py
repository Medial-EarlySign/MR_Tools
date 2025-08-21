import os
import re
from utils import unix_path
import pandas as pd


def get_folder_data_list(fld_name, work_folder, files_regex=None, to_remove=None):
    signals_path = os.path.join(work_folder, fld_name)
    files = os.listdir(signals_path)
    files.sort()
    if files_regex:
        files = [s for s in files if bool(re.search(files_regex, s))]
    data_list = []

    for file in files:
        if 'error' in file.lower():
            continue
        if os.path.isdir(os.path.join(signals_path, file)):
            continue
        st = 'DATA\t../' + fld_name + '/' + file
        if to_remove and file in to_remove:
            st = '# ' + st
        data_list.append(st)
    return data_list


def get_dict_list(dict_fld, config_folder):
    signals_path = os.path.join(config_folder, dict_fld)
    dict_files = [f for f in os.listdir(signals_path) if f.startswith('dict')]
    def_files = [x for x in dict_files if 'set' not in x]
    set_file = [x for x in dict_files if 'set' in x]
    data_list = []
    for file in def_files:
        st = 'DICTIONARY\t' + dict_fld + '/' + file
        data_list.append(st)
    for file in set_file:
        st = 'DICTIONARY\t' + dict_fld + '/' + file
        data_list.append(st)
    return data_list


def add_const_lines(dest_rep, config_folder, dest_folder):
    cons_list = ['#', '# convert config file', '#', 'DESCRIPTION\t'+dest_rep.upper() + ' data - full version',
                 'RELATIVE \t1', 'SAFE_MODE\t1', 'MODE\t3', 'PREFIX\t'+dest_rep+'_rep', 'CONFIG\t'+dest_rep+'.repository',
                 'SIGNAL\t'+dest_rep+'.signals', 'FORCE_SIGNAL\tGENDER,BYEAR',
                 'DIR\t'+unix_path(config_folder),
                 'OUTDIR\t'+unix_path(dest_folder)
                 ]
    return cons_list


def create_config_file(dest_rep, work_folder, dest_folder, to_remove):
    config_folder = os.path.join(work_folder, 'rep_configs')
    out_file = os.path.join(config_folder, dest_rep+'.convert_config')

    fld_list = ['FinalSignals']
    dict_fld_name = 'dicts'

    final_list = add_const_lines(dest_rep,config_folder, dest_folder)
    dict_list = get_dict_list(dict_fld_name, config_folder)
    final_list.extend(dict_list)

    for fld in fld_list:
        dat_files_list = get_folder_data_list(fld, work_folder, to_remove=to_remove)
        final_list.extend(dat_files_list)
        final_list.extend(['\n'])

    with open(out_file, 'w', newline='\n') as f:
        for item in final_list:
            f.write("%s\n" % item)

def create_additional_config_file(dest_rep, work_folder, dest_folder, to_load):
    config_folder = os.path.join(work_folder, 'rep_configs')
    out_file = os.path.join(config_folder, dest_rep + '.additional'+'.convert_config')

    fld_list = ['FinalSignals']
    dict_fld_name = 'dicts'

    final_list = add_const_lines(dest_rep,config_folder, dest_folder)
    dict_list = get_dict_list(dict_fld_name, config_folder)
    final_list.extend(dict_list)

    to_load_s=set(to_load)
    to_load_s.add('GENDER')
    to_load_s.add('BYEAR')
    #to_load_s.add('BDATE')
    p_regex_files='|'.join(list(map(lambda x: '^' + x,list(to_load_s))))
    for fld in fld_list:
        dat_files_list = get_folder_data_list(fld, work_folder, files_regex=p_regex_files)
        final_list.extend(dat_files_list)
        final_list.extend(['\n'])

    with open(out_file, 'w', newline='\n') as f:
        for item in final_list:
            f.write("%s\n" % item)
        f.write('LOAD_ONLY\t%s\n'%(','.join(to_load)))


def create_signal_file(dest_rep, work_folder, code_folder, start_id=200):
    config_folder = os.path.join(work_folder, 'rep_configs')
    out_file = os.path.join(config_folder, dest_rep+'.signals')

    if (os.path.exists(out_file)):
        ans=input('You are about to override %s, Are you sure? Y/N:'%(dest_rep+'.signals')).upper()
        if ans!='Y':
            print('Stoped')
            return
    sig_map=pd.read_csv(os.path.join(code_folder, 'configs', 'map.tsv'), sep='\t')
    lab_sigs=list(sig_map['Map_to'].copy().drop_duplicates())
    #Also add BYEAR, BDATE, GENDER, (TRAIN, DEATH, MEMBERSHIP)
    #User need to added categorical signals, smoking, etc...
    fr=open(os.path.join(code_folder, 'configs', 'rep.signals'), 'r') #TEMPLATE
    sig_lines=fr.readlines()
    fr.close()
    #Manipulate and add lines:
    for lab in lab_sigs:
        sig_lines.append('SIGNAL\t%s\t%d\t%s\t%s\t0\n'%(lab, start_id, '16:my_SDateVal', 'Lab_Test'))
        start_id+=1

    fw=open(out_file, 'w')
    fw.writelines(sig_lines)
    fw.close()

