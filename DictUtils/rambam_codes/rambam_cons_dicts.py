import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, read_onto_set_dict, xml_list_to_csv, map_rambam_codes, map_shorter_codes
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_cons_file = 'rambom_consultations_codes.csv'
rambam_cons_dict_file = RAMBAM_DIR + '\\dict.consultations'

rambam_med_index_start = 10000

if __name__ == '__main__':
    section_type_list = ['ev_consultations']
    attr_name_list = ['consultingdepartment', 'orderedconsulttype']
    if os.path.isfile(rambam_cons_file):
        diag_df = load_rambam_diag(rambam_cons_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, section_type_list, attr_name_list, rambam_cons_file)

    diag_df['desc'] = diag_df['desc'].where(~diag_df['desc'].str.contains('None'), ':' + diag_df['code'].astype('str'))

    dict_df = xml_list_to_csv(diag_df)
    rambam_def = build_def_dict('RAMBAM', dict_df, 'code0', 'desc0', rambam_med_index_start)
    rambam_def.to_csv(rambam_cons_dict_file, sep='\t', index=False, header=False)

    print('DONE')
