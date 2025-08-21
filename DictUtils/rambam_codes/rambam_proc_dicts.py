import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, xml_list_to_csv, map_rambam_codes, map_shorter_codes, read_onto_set_dict, map_rmabam_level
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_proc_file = 'rambom_proc_codes.csv'
rambam_proc_dict_file = RAMBAM_DIR + '\\dict.procedures'
rambam_proc_dict_set_file = RAMBAM_DIR + '\\dict.set_procedures'

ICD9_DIR = '..\\Ontologies\\ICD9\\ICD9\\'
ICD10_DIR = '..\\Ontologies\\ICD10\\dicts\\'
SNMI_DIR = '..\\Ontologies\\SNMI\\dicts\\'

ICD9_set_dict = ICD9_DIR + 'dict.set_icd9sg'
ICD9_dict = ICD9_DIR + 'dict.icd9sg'

rambam_med_index_start = 110000


def map_shorter_proc(onto, rambam_codes, onto_def_file, onto_set_file):
    onto_set = read_onto_set_dict(onto_set_file)
    onto_def = pd.read_csv(onto_def_file, sep='\t', names=['typ', 'medialid', 'desc'])
    onto_def = get_code_decs_map(onto_def)
    rb_sets_df = pd.DataFrame()
    rambam_codes.rename(columns={'code': 'code0', 'desc': 'CODE'}, inplace=True)

    #remove last and check if ICD9
    rambam_codes['code2'] = rambam_codes['code0'].str[:-1]
    map_rambam = map_rmabam_level(onto, rambam_codes, onto_def, onto_set, 2)
    rb_sets_df = rb_sets_df.append(map_rambam)
    rambam_codes = rambam_codes[~rambam_codes['CODE'].isin(map_rambam['inner'])]

    #Remove the first R and check if ICD9
    rambam_codes['code2'] = rambam_codes['code0'].where(rambam_codes['code0'].str[0] != 'R', rambam_codes['code0'].str[1:])
    map_rambam = map_rmabam_level(onto, rambam_codes, onto_def, onto_set, 2)
    rb_sets_df = rb_sets_df.append(map_rambam)
    rambam_codes = rambam_codes[~rambam_codes['CODE'].isin(map_rambam['inner'])]

    #remove the R and the last
    rambam_codes['code2'] = rambam_codes['code0'].where(rambam_codes['code0'].str[0] != 'R',
                                                        rambam_codes['code0'].str[1:-1])
    map_rambam = map_rmabam_level(onto, rambam_codes, onto_def, onto_set, 2)
    rb_sets_df = rb_sets_df.append(map_rambam)

    return rb_sets_df


if __name__ == '__main__':
    section_type_list = ['ev_procedures', 'ev_institutes', 'ev_surgeries']
    attr_name_list = ['servicecode', 'servicecode', 'performedprocedurecode']

    if os.path.isfile(rambam_proc_file):
        diag_df = load_rambam_diag(rambam_proc_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, section_type_list, attr_name_list, rambam_proc_file)
    #diag_df.to_csv(rambam_proc_file, sep='\t')

    dict_df = xml_list_to_csv(diag_df)
    #dict_df.to_csv('rambam_proc_hier.csv', sep='\t')

    rambam_def = build_def_dict('RAMBAM', dict_df, 'code0', 'desc0', rambam_med_index_start)
    rambam_def.to_csv(rambam_proc_dict_file, sep='\t', index=False, header=False)

    rambam_set = map_rambam_codes('ICD9', dict_df, ICD9_dict, ICD9_set_dict)

    def_map = get_code_decs_map(rambam_def)
    in_set = rambam_set['inner'].unique()
    def_map = def_map.reset_index()
    def_map['found'] = def_map['desc'].isin(in_set)
    def_map = def_map[~def_map['found']]

    
    shorter_maps = map_shorter_proc('ICD9', def_map, ICD9_dict, ICD9_set_dict)
    rambam_set = pd.concat([rambam_set, shorter_maps])
    rambam_set[['typ', 'outer', 'inner']].to_csv(rambam_proc_dict_set_file, sep='\t', index=False, header=False)

    copy(ICD9_dict, RAMBAM_DIR)
    copy(ICD9_set_dict, RAMBAM_DIR)

    first_line = 'SECTION' + '\t' + 'PROCEDURE\n'
    dict_list = ['dict.set_icd9sg', 'dict.icd9sg', 'dict.procedures', 'dict.set_procedures']
    for file in dict_list:
        add_fisrt_line(first_line, RAMBAM_DIR+'//'+file)
    #
    # print(rambam_set)