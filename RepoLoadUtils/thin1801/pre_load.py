from split_ahd import load_ahd_files
from split_medical import load_medical
from load_patient import load_demographic
from load_therapy import load_therapy
from stage_to_signals_parallel import code_files_to_signals
from create_dicts import create_drug_dicts, create_ahdlookup_dict, create_readcode_dict, create_prac_dict,\
    craate_rc_icd10_map


if __name__ == '__main__':
    load_demographic()  # reads demographic file and create ID2IND and demo folder
    load_ahd_files('.')  # reads ahd.* files save files no Numeric, NonNumeric, imms, Readcode
    load_medical()  # read medical.* files create REG file in medical and RC* files in Readcodes
    load_therapy()  # create drugs files in therapy

    code_files_to_signals()

    create_drug_dicts()
    create_ahdlookup_dict()
    create_readcode_dict()
    create_prac_dict()
    craate_rc_icd10_map()

