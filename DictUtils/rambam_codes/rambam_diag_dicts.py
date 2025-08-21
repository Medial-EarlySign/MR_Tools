import pandas as pd
from shutil import copy
import os
import sys
from rambam_codes_utils import read_rambam_xmls, load_rambam_diag, map_rambam_codes, map_shorter_codes, xml_list_to_csv
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import build_def_dict, add_fisrt_line, get_code_decs_map


RAMBAM_DIR = 'dicts'
rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_diags_file = 'rambom_diag_codes.csv'
rambam_diag_dict_file = RAMBAM_DIR + '\\dict.diagnoses'
rambam_diag_dict_set_file = RAMBAM_DIR + '\\dict.set_diagnoses'

ICD9_DIR = '..\\Ontologies\\ICD9\\dicts\\'
ICD10_DIR = '..\\Ontologies\\ICD10\\dicts\\'
SNMI_DIR = '..\\Ontologies\\SNMI\\dicts\\'

ICD9_set_dict = ICD9_DIR + 'dict.set_icd9dx'
ICD9_dict = ICD9_DIR + 'dict.icd9dx'
ICD10_set_dict = ICD10_DIR + 'dict.set_icd10'
ICD10_dict = ICD10_DIR + 'dict.icd10'
SNMI_set_dict = SNMI_DIR + 'dict.set_snmi'
SNMI_dict = SNMI_DIR + 'dict.snmi'

rambam_med_index_start = 110000


if __name__ == '__main__':
    if os.path.isfile(rambam_diags_file):
        diag_df = load_rambam_diag(rambam_diags_file)
    else:
        diag_df = read_rambam_xmls(rambam_xml_dir, ['ev_diagnoses'], ['conditioncode'], rambam_diags_file)
    dict_df = xml_list_to_csv(diag_df)

    rambam_def = build_def_dict('RAMBAM', dict_df, 'code0', 'desc0', rambam_med_index_start)
    rambam_def.to_csv(rambam_diag_dict_file, sep='\t', index=False, header=False)

    rambam_diag_dict_icd9 = map_rambam_codes('ICD9', dict_df, ICD9_dict, ICD9_set_dict)
    rambam_diag_dict_icd10 = map_rambam_codes('ICD10', dict_df, ICD10_dict, ICD10_set_dict)
    rambam_diag_dict_snmi = map_rambam_codes('SNMI', dict_df, SNMI_dict, SNMI_set_dict)
    rambam_set = pd.concat([rambam_diag_dict_icd9, rambam_diag_dict_icd10, rambam_diag_dict_snmi])

    #  Check for non mapped Rambam codes and check if they are IDC9 deeper codes

    def_map = get_code_decs_map(rambam_def)
    in_set = rambam_set['inner'].unique()
    def_map = def_map.reset_index()
    def_map['found'] = def_map['desc'].isin(in_set)
    def_map = def_map[~def_map['found']]

    shorter_maps = map_shorter_codes('ICD9', def_map, ICD9_dict, ICD9_set_dict)
    rambam_set = pd.concat([rambam_set, shorter_maps])

    rambam_set[['typ', 'outer', 'inner']].to_csv(rambam_diag_dict_set_file, sep='\t', index=False, header=False)
    #add_fisrt_line('SECTION' + '\t' + 'DIAGNOSIS\n', rambam_diag_dict_set_file)

    # Copy all ontology dits to Rambam and add SECTION line
    #dict_list = [ICD9_dict, ICD9_set_dict, ICD10_dict, ICD10_set_dict, SNMI_dict, SNMI_set_dict]
    copy(ICD9_dict, RAMBAM_DIR)
    copy(ICD9_set_dict, RAMBAM_DIR)
    copy(ICD10_dict, RAMBAM_DIR)
    copy(ICD10_set_dict, RAMBAM_DIR)
    copy(SNMI_dict, RAMBAM_DIR)
    copy(SNMI_set_dict, RAMBAM_DIR)
    first_line = 'SECTION' + '\t' + 'DIAGNOSIS,DIAGNOSIS_PRIMARY,DIAGNOSIS_SECONDARY,DIAGNOSIS_PAST\n'
    dict_list = ['dict.set_icd9dx', 'dict.icd9dx', 'dict.set_icd10', 'dict.icd10', 'dict.set_snmi', 'dict.snmi',
                 'dict.diagnoses', 'dict.set_diagnoses']
    for file in dict_list:
        add_fisrt_line(first_line, RAMBAM_DIR+'//'+file)

    print(rambam_set)
