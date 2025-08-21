import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, read_onto_set_dict, xml_list_to_csv, map_rambam_codes, map_shorter_codes
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_med_form_file = 'rambom_med_form_codes.csv'
rambam_med_freq_file = 'rambom_med_freq_codes.csv'
rambam_med_routs_file = 'rambom_med_routs_codes.csv'
rambam_med_units_file = 'rambom_med_units_codes.csv'
rambam_med_form_dict_file = RAMBAM_DIR + '\\dict.med_form'
rambam_med_freq_dict_file = RAMBAM_DIR + '\\dict.med_freq'
rambam_med_rout_dict_file = RAMBAM_DIR + '\\dict.med_routes'
rambam_med_units_dict_file = RAMBAM_DIR + '\\dict.med_units'


def med_dict(section_list, attr_list, codes_file, dict_file, index_start):

    if os.path.isfile(codes_file):
        diag_df = load_rambam_diag(codes_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, section_list, attr_list, codes_file)

    #diag_df['desc'] = diag_df['desc'].where(~diag_df['desc'].str.contains('None'), ':' + diag_df['code'].astype('str'))

    dict_df = xml_list_to_csv(diag_df)
    rambam_def = build_def_dict('RAMBAM', dict_df, 'code0', 'desc0', index_start)
    rambam_def.to_csv(dict_file, sep='\t', index=False, header=False)

    print('DONE')


if __name__ == '__main__':
    section_type_list = ['ev_medications_administered', 'ev_medications_adm', 'ev_medications_orders', 'ev_medications_recom']

    medial_index_start = 11000
    attr_name_list = ['formcode']
    med_dict(section_type_list, attr_name_list, rambam_med_form_file, rambam_med_form_dict_file, medial_index_start)

    medial_index_start = 12000
    attr_name_list = ['frequencycode']
    med_dict(section_type_list, attr_name_list, rambam_med_freq_file, rambam_med_freq_dict_file, medial_index_start)

    medial_index_start = 13000
    attr_name_list = ['routecode']
    med_dict(section_type_list, attr_name_list, rambam_med_routs_file, rambam_med_rout_dict_file, medial_index_start)

    medial_index_start = 14000
    attr_name_list = ['quantitiy_unitcode']
    med_dict(section_type_list, attr_name_list, rambam_med_units_file, rambam_med_units_dict_file, medial_index_start)

    print('Done')