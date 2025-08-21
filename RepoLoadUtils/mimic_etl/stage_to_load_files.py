import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces
from train_signal import create_train_signal
from staging_config import MimicLabs, MimicDemographic, StageConfig
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files
from elixhauser_defines import elixhauser_drg, elixhauser_icd9
from sql_utils import get_sql_engine


elixhauser_diag = ['CONGESTIVE_HEART_FAILURE',
                   'CARDIAC_ARRHYTHMIAS',
                   'VALVULAR_DISEASE',
                   'PULMONARY_CIRCULATION',
                   'PERIPHERAL_VASCULAR',
                   'HYPERTENSION',
                   'PARALYSIS',
                   'OTHER_NEUROLOGICAL',
                   'CHRONIC_PULMONARY',
                   'DIABETES_UNCOMPLICATED',
                   'DIABETES_COMPLICATED',
                   'HYPOTHYROIDISM',
                   'RENAL_FAILURE',
                   'LIVER_DISEASE',
                   'PEPTIC_ULCER',
                   'AIDS',
                   'LYMPHOMA',
                   'METASTATIC_CANCER',
                   'SOLID_TUMOR',
                   'RHEUMATOID_ARTHRITIS',
                   'COAGULOPATHY',
                   'OBESITY',
                   'WEIGHT_LOSS',
                   'FLUID_ELECTROLYTE',
                   'BLOOD_LOSS_ANEMIA',
                   'DEFICIENCY_ANEMIAS',
                   'ALCOHOL_ABUSE',
                   'DRUG_ABUSE',
                   'PSYCHOSES',
                   'DEPRESSION'
                   ]


class RawMimicElixhauser(StageConfig):
    DBNAME = 'RawMimic'
    TABLE = 'elixhauser_ahrq'


def mimic_labs_chart_to_files(cfg):
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    mimic_def = MimicLabs()

    mimic_map = pd.read_csv(os.path.join(code_folder, 'mimic_signal_map.csv'), sep='\t')
    lab_chart_cond = ((mimic_map['source'] == 'labevents') |
                      (mimic_map['source'] == 'chartevents') |
                      (mimic_map['source'] == 'outputevents'))
    mimic_map_numeric = mimic_map[(mimic_map['type'] == 'numeric') & lab_chart_cond]
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map(work_folder)
    if os.path.exists(os.path.join(code_folder, 'mixture_units_cfg.txt')):
        special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    else:
        special_factors_signals = None
    numeric_to_files(mimic_def, mimic_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder)
    mimic_map_cats = mimic_map[(mimic_map['type'] == 'string') & lab_chart_cond]
    categories_to_files(mimic_def, mimic_map_cats, id2nr, out_folder)


def mimic_demographic_to_files(cfg):
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    mimic_def = MimicDemographic()
    id2nr = get_id2nr_map(work_folder)
    mimic_map = pd.read_csv(os.path.join(code_folder, 'mimic_signal_map.csv'), sep='\t')
    demo_cond = ((mimic_map['source'] == 'patients') | (mimic_map['source'] == 'admissions'))
    mimic_map_demo = mimic_map[demo_cond]
    demographic_to_files(mimic_def, mimic_map_demo, id2nr, out_folder)


def mimic_admission_to_files(cfg):
    sig = 'ADMISSION'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8')
    id2nr = get_id2nr_map(work_folder)
    admissions_df['medialid'] = admissions_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    admissions_df['ADMISSION_TYPE'] = replace_spaces(admissions_df['ADMISSION_TYPE'])
    admissions_df['ADMISSION_LOCATION'] = replace_spaces(admissions_df['ADMISSION_LOCATION'])
    admissions_df['status'] = 1 - admissions_df["HOSPITAL_EXPIRE_FLAG"]
    admissions_df['signal'] = sig
    admissions_df.sort_values(by=['medialid', 'ADMITTIME'], inplace=True)
    cols = ['medialid', 'signal', 'ADMITTIME', 'DISCHTIME', 'ADMISSION_TYPE', 'ADMISSION_LOCATION', 'status', 'HADM_ID']
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(admissions_df[cols], out_folder, sig)

    # sig = 'DISCHARGE_STATUS'
    # admissions_df['signal'] = sig
    # admissions_df['status'] = 1 - admissions_df["HOSPITAL_EXPIRE_FLAG"]
    # cols = ['medialid', 'signal', 'status']
    # if os.path.exists(os.path.join(out_folder, sig)):
    #     os.remove(os.path.join(out_folder, sig))
    # write_tsv(admissions_df[cols], out_folder, sig)

    sig = 'ADMISSION_DIAGNOSIS'
    admissions_df = admissions_df[admissions_df['DIAGNOSIS'].notnull()]
    admissions_df['DIAGNOSIS'] = admissions_df['DIAGNOSIS'].str.replace('\\', ';')
    admissions_df['DIAGNOSIS'] = admissions_df['DIAGNOSIS'].str.replace(',', ';')
    admissions_df['diag_list'] = admissions_df['DIAGNOSIS'].str.split(';', expand=False)
    single_diags = []
    for i, row in admissions_df.iterrows():
        for d in row['diag_list']:
            single_diags.append({'medialid': row['medialid'], 'time': row['ADMITTIME'], 'diag': d.strip(), 'hadm_id': row['HADM_ID']})
    diag_df = pd.DataFrame(single_diags)
    diag_df['signal'] = sig
    diag_df['diag'] = replace_spaces(diag_df['diag'])
    diag_df = diag_df[diag_df['diag'].str.strip() != '']
    cols = ['medialid', 'signal', 'time', 'diag', 'hadm_id']
    diag_df.sort_values(by=['medialid', 'time'], inplace=True)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(diag_df[cols], out_folder, sig)


def icd9_diagnosis_to_file(cfg):
    sig = 'DIAGNOSIS'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    diag_df = pd.read_csv(os.path.join(raw_path, 'DIAGNOSES_ICD.csv'), encoding='utf-8', na_filter=False, dtype={'ICD9_CODE': str})
    # Read ADMISSIONS.csv to find discharged date
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8')
    diag_df = diag_df.merge(admissions_df[['HADM_ID', 'DISCHTIME']], how='left', on='HADM_ID')
    diag_df['medialid'] = diag_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    diag_df = diag_df[diag_df['ICD9_CODE'].str.strip() != '']
    diag_df['ICD9_CODE'] = 'ICD9_CODE:' + diag_df['ICD9_CODE']
    diag_df['signal'] = sig
    cols = ['medialid', 'signal', 'DISCHTIME', 'ICD9_CODE']
    diag_df.sort_values(by=['medialid', 'DISCHTIME'], inplace=True)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(diag_df[cols], out_folder, sig)


def cpt_procedures_to_file(cfg):
    sig = 'PROCEDURES_CPT'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    # FROM PROCEDURES_ICD
    cpt_df = pd.read_csv(os.path.join(raw_path, 'CPTEVENTS.csv'), encoding='utf-8', na_filter=False, dtype=str)
    cpt_df['medialid'] = cpt_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    cpt_df['CPT_CD'] = 'CPT_CODE:' + cpt_df['CPT_CD']
    icu_df = cpt_df[cpt_df['COSTCENTER'] == 'ICU'].copy()
    resp_df = cpt_df[cpt_df['COSTCENTER'] == 'Resp'].copy()
    resp_df.rename(columns={'CHARTDATE': 'proc_time'}, inplace=True)

    # Read ADMISSIONS.csv to find discharged date
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8', dtype=str)
    icu_df = icu_df.merge(admissions_df[['HADM_ID', 'DISCHTIME']], how='left', on='HADM_ID')
    icu_df.rename(columns={'DISCHTIME': 'proc_time'}, inplace=True)
    cols = ['medialid', 'proc_time', 'CPT_CD']
    final_df = pd.concat([resp_df[cols], icu_df[cols]])
    final_df['signal'] = sig
    final_df.sort_values(by=['medialid', 'proc_time'], inplace=True)
    write_tsv(final_df[['medialid', 'signal', 'proc_time', 'CPT_CD']], out_folder, sig)


def procedures_to_file(cfg):
    sig = 'PROCEDURES'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)
    # FROM PROCEDURES_ICD
    proc_df = pd.read_csv(os.path.join(raw_path, 'PROCEDURES_ICD.csv'), encoding='utf-8', na_filter=False, dtype=str)
    # Read ADMISSIONS.csv to find discharged date
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8', dtype=str)
    proc_df = proc_df.merge(admissions_df[['HADM_ID', 'DISCHTIME']], how='left', on='HADM_ID')
    proc_df['medialid'] = proc_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    proc_df['PROC'] = 'ICD9_CODE:' + proc_df['ICD9_CODE']
    proc_df.rename(columns={'DISCHTIME': 'proc_time'}, inplace=True)

    # FROM PROCEDUREEVENTS_MV.csv
    proc_mv_df = pd.read_csv(os.path.join(raw_path, 'PROCEDUREEVENTS_MV.csv'), encoding='utf-8', na_filter=False, dtype=str, usecols=['SUBJECT_ID', 'STARTTIME', 'ITEMID'])
    print(proc_mv_df.shape)
    proc_mv_df.drop_duplicates(inplace=True)
    print(proc_mv_df.shape)
    proc_mv_df['medialid'] = proc_mv_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    proc_mv_df['PROC'] = 'ITEMID:' + proc_mv_df['ITEMID']
    proc_mv_df.rename(columns={'STARTTIME': 'proc_time'}, inplace=True)
    proc_df = pd.concat([proc_df[['medialid', 'proc_time', 'PROC']], proc_mv_df], sort=False)

    proc_df['signal'] = sig
    cols = ['medialid', 'signal', 'proc_time', 'PROC']
    proc_df.sort_values(by=['medialid', 'proc_time'], inplace=True)
    write_tsv(proc_df[cols], out_folder, sig, mode='w')


def diag_to_elixhauser():
    sig = 'DIAGNOSIS_Elixhauser'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    drg_df = pd.read_csv(os.path.join(raw_path, 'DRGCODES.csv'), encoding='utf-8')
    drg_df = drg_df[~drg_df['DRG_TYPE'].str.contains('APR')]
    drg_df.drop_duplicates(subset=['SUBJECT_ID', 'HADM_ID', 'DRG_TYPE', 'DRG_CODE'])
    drg_df['str_drg'] = drg_df['DRG_CODE'].astype(str).str.zfill(3)
    drg_df['str_drg'] = drg_df['str_drg'].where(drg_df['DRG_TYPE'] == 'HCFA', 'MS'+drg_df['str_drg'])
    for cond in elixhauser_drg.keys():
        drg_df[cond] = drg_df['str_drg'].isin(elixhauser_drg[cond])
    drg_grp = drg_df.groupby('HADM_ID').sum().reset_index()

    icd_df = pd.read_csv(os.path.join(raw_path, 'DIAGNOSES_ICD.csv'), encoding='utf-8')
    icd_d = pd.read_csv(os.path.join(raw_path, 'D_ICD_DIAGNOSES.csv'), encoding='utf-8')
    icd_df = icd_df.merge(icd_d, how='left', on='ICD9_CODE')
    for cond in elixhauser_icd9.keys():
        icd_df[cond] = icd_df['ICD9_CODE'].isin(elixhauser_icd9[cond])
    icd_grp = icd_df.groupby('HADM_ID').sum().reset_index()
    all_flags = drg_grp.merge(icd_grp, on='HADM_ID')

    all_flags['CONGESTIVE_HEART_FAILURE'] = (all_flags['Cardiac'] == 0) & (all_flags[['CHF', 'HTNWCHF', 'HHRWCHF', 'HHRWHRF']].any(axis=1))
    all_flags['CARDIAC_ARRHYTHMIAS'] = (all_flags['Cardiac'] == 0) & (all_flags['ARYTHM'] == 1)
    all_flags['VALVULAR_DISEASE'] = (all_flags['Cardiac'] == 0) & (all_flags['VALVE'] == 1)
    all_flags['PULMONARY_CIRCULATION'] = (~((all_flags['Cardiac'] == 0) | (all_flags['Copd'] == 0))) & (all_flags['PULMCIRC'] == 1)
    all_flags['PERIPHERAL_VASCULAR'] = (all_flags['PeripherialVascular'] == 0) & (all_flags['PERIVASC'] == 1)
    # all_flags['HYPERTENSION'] = (all_flags["HyperTension"] == 0) & (all_flags["Cardiac"]==0) & all_flags["Renal"]==0 &
    all_flags['PARALYSIS'] = (all_flags['CerebroVascular'] == 0) & (all_flags['PARA'] == 1)
    all_flags['OTHER_NEUROLOGICAL'] = (all_flags['NervousSystem'] == 0) & (all_flags['NEURO'] == 1)
    all_flags['CHRONIC_PULMONARY'] = (all_flags['Copd'] == 0) & (all_flags['CHRNLUNG'] == 1)
    all_flags['DIABETES_UNCOMPLICATED'] = (all_flags['Diabetes'] == 0) & (all_flags['DMCX'] == 0) & (all_flags['DM'] == 1)
    all_flags['DIABETES_COMPLICATED'] = (all_flags['Diabetes'] == 0) & (all_flags['DMCX'] == 1)
    all_flags['HYPOTHYROIDISM'] = (all_flags['ThyroidEndocrine'] == 0) & (all_flags['HYPOTHY'] == 1)
    all_flags['RENAL_FAILURE'] = (all_flags['Renal'] == 0) & (all_flags[['RENLFAIL', 'HRENWRF', 'HHRWRF', 'HHRWHRF']].any(axis=1))
    all_flags['LIVER_DISEASE'] = (all_flags['Liver'] == 0) & (all_flags['LIVER'] == 1)
    all_flags['PEPTIC_ULCER'] = (all_flags['GiHemorrhageUlcer'] == 0) & (all_flags['ULCER'] == 1)
    all_flags['AIDS'] = (all_flags['HIV'] == 0) & (all_flags['AIDS'] == 1)
    all_flags['LYMPHOMA'] = (all_flags['LeukemiaLymphoma'] == 0) & (all_flags['LYMPH'] == 1)
    all_flags['METASTATIC_CANCER'] = (all_flags['Cancer'] == 0) & (all_flags['METS'] == 1)
    all_flags['SOLID_TUMOR'] = (all_flags['Cancer'] == 0) & (all_flags['METS'] == 0) & (all_flags['TUMOR'] == 1)
    all_flags['RHEUMATOID_ARTHRITIS'] = (all_flags['ConnectiveTissue'] == 0) & (all_flags['ARTH'] == 1)
    all_flags['COAGULOPATHY'] = (all_flags['Coagulation'] == 0) & (all_flags['COAG'] == 1)
    all_flags['RHEUMATOID_ARTHRITIS'] = (all_flags['NutritionMetabolic'] == 0) & (all_flags['Obesity'] == 0) & (all_flags['OBESE'] == 1)
    all_flags['WEIGHT_LOSS'] = (all_flags['NutritionMetabolic'] == 0) & (all_flags['WGHTLOSS'] == 1)
    all_flags['FLUID_ELECTROLYTE'] = (all_flags['NutritionMetabolic'] == 0) & (all_flags['LYTES'] == 1)
    all_flags['BLOOD_LOSS_ANEMIA'] = (all_flags['Anemia'] == 0) & (all_flags['BLDLOSS'] == 1)
    all_flags['DEFICIENCY_ANEMIAS'] = (all_flags['Anemia'] == 0) & (all_flags['ANEMDEF'] == 1)
    all_flags['ALCOHOL_ABUSE'] = (all_flags['AlcoholDrug'] == 0) & (all_flags['ALCOHOL'] == 1)
    all_flags['DRUG_ABUSE'] = (all_flags['AlcoholDrug'] == 0) & (all_flags['DRUG'] == 1)
    all_flags['PSYCHOSES'] = (all_flags['Psychoses'] == 0) & (all_flags['PSYCH'] == 1)
    all_flags['DEPRESSION'] = (all_flags['DepressiveNeuroses'] == 0) & (all_flags['DEPRESS'] == 1)


def diag_to_elixhauser_sql(cfg):
    sig = 'DIAGNOSIS_Elixhauser'

    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    raw_mimic_def = RawMimicElixhauser()
    db_engine = get_sql_engine(raw_mimic_def.DBTYPE, raw_mimic_def.DBNAME, raw_mimic_def.username,
                               raw_mimic_def.password)
    select = ''
    for el in elixhauser_diag:
        select += el + ', '
    select = select[:-2]
    sql_query = "SELECT eli.SUBJECT_ID, eli.HADM_ID, adm.DISCHTIME, " + select + " \
    FROM " + raw_mimic_def.TABLE + " eli \
    INNER JOIN admissions adm ON eli.hadm_id = adm.hadm_id"
    df = pd.read_sql(sql_query, db_engine)
    id2nr = get_id2nr_map(work_folder)
    df['medialid'] = df['subject_id'].astype(str).map(id2nr).astype(int)
    df['sig'] = sig
    diag_df = pd.DataFrame()
    cols = ['medialid', 'sig', 'dischtime', 'val']
    for el in elixhauser_diag:
        el_df = df[df[el.lower()] == 1]
        el_df['val'] = el
        diag_df = diag_df.append(el_df[cols])
    diag_df.sort_values(by=['medialid', 'dischtime'], inplace=True)
    write_tsv(diag_df[cols], out_folder, sig, mode='w')


def drg_to_file(cfg):
    sig = 'DRG'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)

    drg_df = pd.read_csv(os.path.join(raw_path, 'DRGCODES.csv'), encoding='utf-8', na_filter=False, dtype=str,
                         usecols=['SUBJECT_ID', 'HADM_ID', 'DRG_TYPE', 'DRG_CODE'])
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8', dtype=str,
                                usecols=['HADM_ID', 'DISCHTIME'])
    drg_df = drg_df.merge(admissions_df, how='left', on='HADM_ID')

    drg_df['medialid'] = drg_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    drg_df['DRG_CODE'] = drg_df['DRG_TYPE'] + ':' + drg_df['DRG_CODE']
    drg_df['signal'] = sig
    drg_df.sort_values(by=['medialid', 'DISCHTIME'], inplace=True)
    write_tsv(drg_df[['medialid', 'signal', 'DISCHTIME', 'DRG_CODE']], out_folder, sig, mode='w')


def transfers_to_file(cfg):
    sig = 'TRANSFERS'
    work_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map(work_folder)

    trans_df = pd.read_csv(os.path.join(raw_path, 'TRANSFERS.csv'), encoding='utf-8', na_filter=False, dtype=str)
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8', dtype=str,
                                usecols=['HADM_ID', 'ADMITTIME', 'DISCHTIME', 'ADMISSION_LOCATION', 'DISCHARGE_LOCATION'])
    trans_df = trans_df.merge(admissions_df, on='HADM_ID', how='left')
    trans_df['medialid'] = trans_df['SUBJECT_ID'].astype(str).map(id2nr).astype(int)
    trans_df.loc[trans_df['CURR_CAREUNIT'].str.strip() != '', 'CURR_WARDID'] = trans_df['CURR_CAREUNIT'] + ':' + trans_df['CURR_WARDID']
    trans_df.loc[trans_df['PREV_CAREUNIT'].str.strip() != '', 'PREV_WARDID'] = trans_df['PREV_CAREUNIT'] + ':' + trans_df['PREV_WARDID']

    trans_df.loc[(trans_df['CURR_CAREUNIT'].str.strip() == '') &
                 (trans_df['CURR_WARDID'].str.strip() != ''), 'CURR_WARDID'] = 'WARD:' + trans_df['CURR_WARDID']
    trans_df.loc[(trans_df['PREV_CAREUNIT'].str.strip() == '') &
                (trans_df['PREV_WARDID'].str.strip() != ''), 'PREV_WARDID'] = 'WARD:' + trans_df['PREV_WARDID']

    trans_df.loc[(trans_df['CURR_WARDID'].str.strip() == ''), 'CURR_WARDID'] = replace_spaces(trans_df[trans_df['CURR_WARDID'].str.strip() == '']['DISCHARGE_LOCATION'])
    trans_df.loc[(trans_df['PREV_WARDID'].str.strip() == ''), 'PREV_WARDID'] = replace_spaces(trans_df[trans_df['PREV_WARDID'].str.strip() == '']['ADMISSION_LOCATION'])
    trans_df.loc[trans_df['OUTTIME'].str.strip() == '', 'OUTTIME'] = trans_df['INTIME']
    trans_df = trans_df[(trans_df['INTIME'].str.strip() != '') & (trans_df['OUTTIME'].str.strip() != '')]
    trans_df.sort_values(['medialid', 'INTIME'], inplace=True)
    trans_df['signal'] = sig
    cols = ['medialid', 'signal', 'INTIME', 'OUTTIME', 'HADM_ID', 'EVENTTYPE', 'PREV_WARDID', 'CURR_WARDID']
    write_tsv(trans_df[cols], out_folder, sig, mode='w')

    sig = 'STAY'
    stay_df = trans_df[trans_df['EVENTTYPE'] != 'discharge'].copy()
    stay_df['signal'] = sig
    cols = ['medialid', 'signal', 'INTIME', 'OUTTIME', 'CURR_WARDID']
    write_tsv(stay_df[cols], out_folder, sig, mode='w')


if __name__ == '__main__':
    cfg = Configuration()
    #mimic_labs_chart_to_files(cfg)
    #mimic_demographic_to_files(cfg)
    #mimic_admission_to_files(cfg)
    #mimic_transfer_to_files(cfg)
    #icd9_diagnosis_to_file(cfg)
    #procedures_to_file(cfg)
    #cpt_procedures_to_file(cfg)
    #diag_to_elixhauser_sql(cfg)
    #create_train_signal(cfg)
    #drg_to_file(cfg)
    transfers_to_file(cfg)
