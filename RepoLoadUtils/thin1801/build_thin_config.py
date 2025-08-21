import sys
import os
import re
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name

# missing = [
#            # 'Fev1',
#            # 'Fev1_over_Fvc',
#            # 'PT',
#            # 'PEFR',
#            # 'Albmin_over_Creatinine',
#            # 'Fvc',
#            # 'Cortisol',
#            # 'PTH',
#            # 'UrineSodium',
#            # 'C3',
#            # 'C4',
#            # 'HCG',
#            # 'CEA',
#            # 'Teophylline',
#            # 'PTT',
#            # 'RandomTriglyceride',
#            # 'RandomLDL',
#            'Microscopy_culture_and_sensitivities',
#            'CHS_Vision_8_Months_And_18_Months_LEFT',
#            'CHS_Vision_3_Years_And_4_Years_LEFT',
#            'CHS_Hips_LEFT',
#            'CHS_Squint_LEFT',
#            'Scoring_test_result',
#            'Family_History',
#            'Cervical_READ_CODE',
#            'Cervical_ADEQUATE',
#            'CHS_Hernia_LEFT',
#            'CHS_Hernia_UMBILICAL',
#            'Allergy_over_intolerance_READ_CODE',
#            'Allergy_over_intolerance_CERTAINTY',
#            'Allergy_over_intolerance_SEVERITY',
#            'Allergy_over_intolerance_REACTION_TYPE',
#            'Ante_natel_fetal_examination_FETAL_PRESENTATION',
#            'Ante_natel_fetal_examination_FETAL_MOVEMENT',
#            'Ante_natel_fetal_examination_FETAL_HEART',
#            'Epilepsy_Fit_details_ASLEEP_AWAKE',
#            'Peripheral_oedema_LATERALITY',
#            'Peripheral_oedema_SITE_IN_LEG',
#            'Elderly_vision_VISUAL_AIDS',
#            'Elderly_hygiene_EXAMINATION_TYPE_HOME',
#            'CHS_Hearing_Over_6_Weeks_RIGHT_EAR',
#            'CHS_Hearing_Over_6_Weeks_LEFT_EAR',
#            'CHS_Muscle_tone_for_8_months_SITTING',
#            'CHS_delivery_details_MODE',
#            'Tactile_sensation',
#            'Allergy_and_Intolerance_non_drug_SEVERITY',
#            'Allergy_and_Intolerance_non_drug_REACTION_TYPE',
#            'Visual_Acuity_Left_Eye_VISUAL_ACUITY',
#            'CHS_Vision_6_Weeks_RIGHT_RED_REFLEX',
#            'CHS_Vision_6_Weeks_LEFT_RED_REFLEX',
#            'CHS_Vision_6_Weeks_FIX',
#            'CHS_Muscle_tone_for_6_weeks_MUSCLE',
#            'Exercise',
#            'CHS_Sphincters_CLEAN_DAY',
#            'CHS_Sphincters_DRY_NIGHT',
#            'CHS_Sphincters_DRY_DAY',
#            'Foot_pulse_right_leg_PRESENCE_DORSALIS_PEDIS',
#            'Maternity_feeding',
#            'CHS_mother_and_baby_SLEEP',
#            'CHS_mother_and_baby_FEEDING',
#            'Diabetes_annual_check_PROGTYPE',
#            'Maternity_perineum_EPISIOTOMY',
#            'Asthma_last_attack_date_NEBULISED',
#            'Asthma_last_attack_date_ORAL_STEROID',
#            'Visual_Acuity_Right_Eye_VISUAL_ACUITY',
#            'Heart_examination_SIZE',
#            'Heart_examination_RHYTHMN',
#            'CHS_cardio_examination_LEFT',
#            'CHS_cardio_examination_HEART_SOUND',
#            'Ankle_neuropathy_PRESENCE_RIGHT_VIB',
#            'Ankle_neuropathy_PRESENCE_LEFT_JERK',
#            'Ankle_neuropathy_PRESENCE_RIGHT_JERK',
#            'Foot_pulse_left_leg_PRESENCE_DORSALIS_PEDIS',
#            'Residence_RESIDENCE_TYPE',
#             'Full_blood_count']
missing = ['VitaminD2', 'VitaminLevel', 'CA199', 'CA153', 'PTT', "APTT",
            'Fructosamine', 'GtanNum', 'PlasmaVolume', 'T3', 'UrineUrate','VLDL', 'VitaminD2', 'VitaminLevel', 'Zinc']


def get_folder_data_list(fld_name, thin_map, files_regex=None):
    signals_path = os.path.join(work_folder, fld_name)
    files = os.listdir(signals_path)
    if files_regex:
        files = [s for s in files if bool(re.search(files_regex, s))]
    data_list = []

    for file in files:
        if 'therapy' in file:
            pref = 'DATA_S'
        else:
            if file in thin_map.index and thin_map[file] == 'numeric':
                pref = 'DATA'
            else:
                pref = 'DATA_S'

        st = pref + '\t../' + fld_name + '/' + file
        if file in missing:
            st = '# ' + st
        data_list.append(st)
    return data_list


def get_dict_list(dict_fld):
    signals_path = os.path.join(work_folder, dict_fld)
    def_files = [x for x in os.listdir(signals_path) if 'set' not in x]
    set_file = [x for x in os.listdir(signals_path) if 'set' in x]
    data_list = []
    for file in def_files:
        st = 'DICTIONARY\t' + file
        data_list.append(st)
    for file in set_file:
        st = 'DICTIONARY\t' + file
        data_list.append(st)
    return data_list


def add_const_lines():
    cons_list = ['#', '# convert config file', '#', 'DESCRIPTION\tTHIN1801 data - full version',
                 'RELATIVE \t1', 'SAFE_MODE\t1', 'MODE\t3', 'PREFIX\tthin_rep', 'CONFIG\tthin.repository',
                 'SIGNAL\tthin.signals', 'FORCE_SIGNAL\tGENDER, BYEAR',
                 'DIR\t/server/Temp/Thin_2018_Loading/rep_configs',
                 'OUTDIR\t/server/Work/CancerData/Repositories/THIN/thin_2018'
                 ]
    return cons_list


if __name__ == '__main__':
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_file = os.path.join(work_folder, 'rep_configs', 'thin18.convert_config_fixes')

    #fld_list = ['NumericSignals', 'NonNumericSignals', 'SpecialSignals', 'therapy', 'Readcode', 'imms', 'medical']

    thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)

    sig_type_map = thin_map[['signal', 'type']].drop_duplicates().set_index('signal')['type']
    #fld_list = ['demo2', 'FinalSignals2', 'therapy']
    fld_list = ['demo', 'FinalSignals']
    #demo_fld_name = 'demo'
    dict_fld_name = 'dicts'

    final_list = add_const_lines()
    dict_list = get_dict_list(dict_fld_name)
    final_list.extend(dict_list)
    #final_list.extend(['DATA\t../demo/thin_demographic', 'DATA_S\t../demo/PRAC\n'])

    for fld in fld_list:
        dat_files_list = get_folder_data_list(fld, sig_type_map)
        final_list.extend(dat_files_list)
        final_list.extend(['\n'])


    #print(dat_files_list)
    with open(out_file, 'w', newline='\n') as f:
        for item in final_list:
            f.write("%s\n" % item)
