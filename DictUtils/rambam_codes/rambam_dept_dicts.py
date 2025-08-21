import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, read_onto_set_dict, xml_list_to_csv, map_rambam_codes, map_shorter_codes
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_dept_file = 'rambom_dept_codes.csv'
rambam_dept_dict_file = RAMBAM_DIR + '\\dict.department'
rambam_dept_dict_set_file = RAMBAM_DIR + '\\dict.set_department'
rambam_dept_translate = 'dept_heb_to_eng.csv'

rambam_med_index_start = 10000

if __name__ == '__main__':
    section_type_list = ['ev_transfers']
    attr_name_list = ['departmentcode']
    if os.path.isfile(rambam_dept_file):
        diag_df = load_rambam_diag(rambam_dept_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, section_type_list, attr_name_list, rambam_dept_file)

    diag_df['desc'] = diag_df['desc'].where(~diag_df['desc'].str.contains('None'), ':' + diag_df['code'].astype('str'))
    dict_df = xml_list_to_csv(diag_df)
    #dict_df = dict_df[dict_df['code0'].notnull()]

    trans_map = pd.read_csv(rambam_dept_translate, sep='\t', names=['heb', 'eng'])
    trans_map.drop_duplicates('heb', inplace=True)
    trans_map = trans_map.set_index('heb', drop=True)['eng']

    #dict_df['num_code'] = dict_df['code0'].where(dict_df['code0'].str.isdigit(), dict_df['index_col'])
    #heb_code_to_num_map = dict_df[['code0', 'num_code']].set_index('code0')['num_code']
    #dict_df['new_code'] = dict_df['code0'].map(heb_code_to_num_map)

    #dict_df.to_csv('rambam_dept_hier.csv', sep='\t')

    #translate names to english
    dict_df['desc0eng'] = dict_df['desc0'].map(trans_map)
    dict_df['code1eng'] = dict_df['code1'].map(trans_map)
    # create def dict file with no codes (no numeric codes for depts in rambam)
    rambam_def = build_def_dict('RAMBAM', dict_df, 'code0','desc0eng' , rambam_med_index_start)
    last_index = rambam_def['mediald'].max() + 1
    rambam_def1 = build_def_dict('RAMBAM', dict_df, 'code1eng', None, last_index)
    rambam_def1 = rambam_def1[~rambam_def1['desc'].isin(rambam_def['desc'].values)]
    rambam_def_all = pd.concat([rambam_def, rambam_def1])
    rambam_def_all.to_csv(rambam_dept_dict_file, sep='\t', index=False, header=False)

    to_set_df = dict_df[dict_df['code1'].notnull()]
    to_set_df['outer'] = 'RAMBAM_CODE:' + to_set_df['code1eng']
    to_set_df['inner'] = 'RAMBAM_CODE:' + to_set_df['code0']
    to_set_df['typ'] = 'SET'
    to_set_df[['typ', 'outer', 'inner']].to_csv(rambam_dept_dict_set_file, sep='\t', index=False, header=False)


    #get_code_decs_map(to_set_df)

    first_line = 'SECTION' + '\t' + 'STAY\n'
    add_fisrt_line(first_line, rambam_dept_dict_file)
    add_fisrt_line(first_line, rambam_dept_dict_set_file)

    print('DONE')
