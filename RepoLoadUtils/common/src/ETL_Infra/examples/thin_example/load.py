#!/usr/bin/env python
import sys, os
import pandas as pd
from ETL_Infra.etl_process import *
from thin_parser import thin_ahd_data_fetcher, thin_demographic_data_fetcher, thin_patient_data_fetcher, thin_medical_data_fetcher, thin_therapy_data_fetcher, parse_readcodes, get_icd_to_readcodes
#END of imports
 
#WORK_DIR='/nas1/Work/Users/Alon/ETL/demo_thin' # where we are going to work
WORK_DIR='/nas1/Work/Users/Eitan/thin_2021_loading' # where we are going to work

txt_editor='gedit'
py_editor='/home/apps/thonny/bin/thonny'
#py_editor=None
interactive_shell=False #When False no debug shell will be opened. no txt_editor or py_editor.. If you want to cancel only py_editor, pass None in py_editor

#Load Demographic
sig_name_or_group_name='demographic'
batch_size=0
prepare_final_signals(thin_patient_data_fetcher, WORK_DIR, sig_name_or_group_name, batch_size, editor = py_editor, map_editor=txt_editor, override='n', interactive=interactive_shell)
sig_name_or_group_name='MEMBERSHIP'
prepare_final_signals(thin_demographic_data_fetcher, WORK_DIR, sig_name_or_group_name, batch_size, editor = py_editor, map_editor=txt_editor, override='n', interactive=interactive_shell)

#Load Smoking 'smoking,measurements'
batch_size=25
prepare_final_signals(thin_ahd_data_fetcher, WORK_DIR, 'smoking,measurements', batch_size, editor = py_editor, map_editor=txt_editor, override='n', interactive=interactive_shell)
#prepare_final_signals(thin_ahd_data_fetcher, WORK_DIR, 'measurements', batch_size, editor = py_editor, map_editor=txt_editor, override='n', interactive=interactive_shell)

#Load Readcodes:
batch_size=40
prepare_final_signals(thin_medical_data_fetcher, WORK_DIR, 'DIAGNOSIS', batch_size, editor = py_editor, map_editor=txt_editor, override='n', interactive=interactive_shell)

#lab
batch_size=10
#prepare_final_signals(thin_ahd_data_fetcher, WORK_DIR, 'labs', batch_size, editor = py_editor, map_editor=txt_editor, override='n', skip_batch_tests = True)

#Load blood pressure:
batch_size=10
prepare_final_signals(thin_ahd_data_fetcher, WORK_DIR, 'BP', batch_size, editor = py_editor, map_editor=txt_editor, override='n', skip_batch_tests = True)

#Load drugs:
batch_size=10
prepare_final_signals(thin_therapy_data_fetcher, WORK_DIR, 'Drug', batch_size, editor = py_editor, map_editor=txt_editor, override='n', skip_batch_tests = True)

#Prepare dicts for Readcodes:
rc_dict=parse_readcodes()
icd_to_rc_dict=get_icd_to_readcodes()
prepare_dicts(WORK_DIR, 'DIAGNOSIS', rc_dict, icd_to_rc_dict)
prepare_dicts(WORK_DIR, 'Ethnicity', rc_dict)

#Finalize:
finish_prepare_load(WORK_DIR, '/nas1/Work/CancerData/Repositories/THIN/thin_2021.lung2', 'thin')