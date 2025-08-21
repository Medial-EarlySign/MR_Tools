from Configuration import Configuration
import os,sys
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.join(os.environ['MR_ROOT'],'Tools', 'RepoLoadUtils', 'common'))
from dicts_utils import create_dict_generic

def create_drugs_dict(cfg):
    def_dicts=['dict.defs_rx', 'dict.atc_defs']
    set_dicts=['dict.atc_sets', 'dict.set_atc_rx']
    header=['pid', 'signal', 'start_date', 'end_date', 'rx_cui', 'std_ordering_mode', 'std_order_status', 'std_quantity']
    to_use_list=['rx_cui', 'std_ordering_mode', 'std_order_status']
    create_dict_generic(cfg, def_dicts, set_dicts, 'Drug', 'Drug', header, to_use_list)

def create_diagnosis_dict(cfg):
    def_dicts=['dict.icd9dx', 'dict.icd10']
    set_dicts=['dict.set_icd9dx', 'dict.set_icd10', 'dict.set_icd10_2_icd9']
    header=['pid', 'signal', 'start_date', 'diagnosis', 'f1', 'f2', 'f3', 'f4']
    to_use_list=['diagnosis']
    create_dict_generic(cfg, def_dicts, set_dicts, 'Diagnosis', 'Diagnosis', header, to_use_list)

if __name__ == '__main__':
    cfg=Configuration()
    create_diagnosis_dict(cfg)
    #create_drugs_dict(cfg)
