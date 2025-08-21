import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, read_onto_set_dict, xml_list_to_csv, map_rambam_codes, map_shorter_codes
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_clinic_file = 'rambam_clinic_codes.csv'
rambam_clinic_dict_file = RAMBAM_DIR + '\\dict.clinic'
rambam_dept_translate = 'dept_heb_to_eng.csv'

rambam_med_index_start = 10000

if __name__ == '__main__':
    section_type_list = ['ev_outpatient_visits']
    attr_name_list = ['departmentcode']
    if os.path.isfile(rambam_clinic_file):
        diag_df = load_rambam_diag(rambam_clinic_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, section_type_list, attr_name_list, rambam_clinic_file)

    dict_df = xml_list_to_csv(diag_df)
    dict_df = dict_df[dict_df['code0'].notnull()]

    trans_map = pd.read_csv(rambam_dept_translate, sep='\t', names=['heb', 'eng'])
    trans_map.drop_duplicates('heb', inplace=True)
    trans_map = trans_map.set_index('heb', drop=True)['eng']
    #dict_df['new_code'] = dict_df.index + 100000
    #dict_df['new_code'] = dict_df['new_code'].astype('str')
    #dict_df['num_code'] = dict_df['code0'].where(dict_df['code0'].str.isdigit(), dict_df['index_col'])
    #heb_code_to_num_map = dict_df[['code0', 'num_code']].set_index('code0')['num_code']
    #dict_df['new_code'] = dict_df['code0'].map(heb_code_to_num_map)

    #dict_df.to_csv('rambam_dept_hier.csv', sep='\t')

    #translate names to english
    dict_df['desc0eng'] = dict_df['desc0'].map(trans_map)
    #dict_df['code1eng'] = dict_df['code1'].map(trans_map)
    # create def dict file with no codes (no numeric codes for depts in rambam)
    rambam_def = build_def_dict('RAMBAM', dict_df,'desc0eng',None, rambam_med_index_start)

    rambam_def.to_csv(rambam_clinic_dict_file, sep='\t', index=False, header=False)

    first_line = 'SECTION' + '\t' + 'VISIT\n'
    add_fisrt_line(first_line, rambam_clinic_dict_file)

    print('DONE')
