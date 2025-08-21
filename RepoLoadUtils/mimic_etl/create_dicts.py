import pandas as pd
import os
from shutil import copy
#MR_ROOT = '/opt/medial/tools/bin/'
#sys.path.append(os.path.join(MR_ROOT, 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df
from stage_to_signals import clean_values
from stage_to_load_files import elixhauser_diag
from sql_utils import get_sql_engine
from staging_config import MimicLabs


def create_gender_dict(dict_path):
    sec = 'GENDER'
    gender_map = {'1': '1', 1: 'M', '2': '2', 2: 'F'}
    dict_file = 'dict.gender'
    dict_df = pd.Series(gender_map).reset_index()
    dict_df['def'] = 'DEF'
    write_tsv(dict_df[['def', 'index', 0]], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sec + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_dict_from_admission(raw_path, dict_path):
    demo_sigs = ['MARITAL_STATUS', 'ETHNICITY', 'INSURANCE', 'RELIGION']
    dict_file = 'dict.demo'
    dc_start = 100
    admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8')
    all_codes = admissions_df['MARITAL_STATUS'].unique().tolist()
    all_codes.extend(admissions_df['ETHNICITY'].unique().tolist())
    all_codes.extend(admissions_df['INSURANCE'].unique().tolist())
    all_codes.extend(admissions_df['RELIGION'].unique().tolist())
    df = pd.DataFrame(data=all_codes)
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    df[0] = replace_spaces(df[0])
    df['def'] = 'DEF'
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))
    write_tsv(df[['def', 'defid', 0]], dict_path, dict_file,  mode='w')
    first_line = 'SECTION\t' + ','.join(demo_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    adm_sigs = ['ADMISSION', 'ADMISSION_DIAGNOSIS', 'TRANSFERS']
    dict_file = 'dict.admission'
    dc_start = 1000
    all_codes = admissions_df['ADMISSION_TYPE'].unique().tolist()
    all_codes.extend(admissions_df['ADMISSION_LOCATION'].unique().tolist())
    all_codes.extend(admissions_df['DISCHARGE_LOCATION'].unique().tolist())

    diag_df = admissions_df[admissions_df['DIAGNOSIS'].notnull()].copy()
    diag_df.loc[:, 'DIAGNOSIS'] = diag_df['DIAGNOSIS'].str.replace('\\', ';')
    diag_df.loc[:, 'DIAGNOSIS'] = diag_df['DIAGNOSIS'].str.replace(',', ';')
    diag_df.loc[:, 'diag_list'] = diag_df['DIAGNOSIS'].str.split(';', expand=False)
    single_set = set()
    for i, row in diag_df.iterrows():
        for d in row['diag_list']:
            single_set.add(d)

    all_codes.extend(list(single_set))
    df = pd.DataFrame(data=all_codes)

    df[0] = replace_spaces(df[0])
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True, how='any')
    df['def'] = 'DEF'
    df = df[df[0].str.strip() !='']
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))
    write_tsv(df[['def', 'defid', 0]], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(adm_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_transfers_dict(dict_path):
    sec = ['STAY', 'TRANSFERS']
    first_line = 'SECTION\t' + ','.join(sec) + '\n'
    dict_file = 'dict.transfers'
    dc_start = 2000
    unit_map = {'CCU': 'Coronary care unit',
                'CSRU': 'Cardiac surgery recovery unit',
                'MICU': 'Medical intensive care unit',
                'NICU': 'Neonatal intensive care unit',
                'NWARD': 'Neonatal ward',
                'SICU': 'Surgical intensive care unit',
                'TSICU': 'Trauma/surgical intensive care unit',
                'WARD': 'Non ICU ward'}
    unit_df = pd.Series(unit_map).reset_index()
    unit_df[0] = replace_spaces(unit_df[0])
    dict_df = code_desc_to_dict_df(unit_df, dc_start, ['index', 0])

    trans_df = pd.read_csv(os.path.join(raw_path, 'TRANSFERS.csv'), encoding='utf-8', na_filter=False, dtype=str,
                           usecols=['EVENTTYPE', 'PREV_CAREUNIT', 'CURR_CAREUNIT', 'PREV_WARDID', 'CURR_WARDID'])

    prev_df = trans_df[['PREV_CAREUNIT', 'PREV_WARDID']][trans_df['PREV_WARDID'].str.strip() != ''].copy()
    prev_df.loc[prev_df['PREV_CAREUNIT'].str.strip() == '', 'PREV_CAREUNIT'] = 'WARD'
    prev_df['code'] = prev_df['PREV_CAREUNIT'] + ':' + prev_df['PREV_WARDID']
    prev_df.drop_duplicates('code', inplace=True)

    curr_df = trans_df[['CURR_CAREUNIT', 'CURR_WARDID']][trans_df['CURR_WARDID'].str.strip() != ''].copy()
    curr_df.loc[curr_df['CURR_CAREUNIT'].str.strip() == '', 'CURR_CAREUNIT'] = 'WARD'
    curr_df['code'] = curr_df['CURR_CAREUNIT'] + ':' + curr_df['CURR_WARDID']
    curr_df.drop_duplicates('code', inplace=True)

    dc_start = dict_df['defid'].max() + 1
    event_df = trans_df[['EVENTTYPE']].drop_duplicates().copy()
    event_df = event_df[event_df['EVENTTYPE'].str.strip() != '']
    event_df.rename(columns={'EVENTTYPE': 'code'}, inplace=True)
    event_df = event_df.assign(defid=range(dc_start, dc_start + event_df.shape[0]))

    dc_start = event_df['defid'].max() + 1
    ward_df = pd.concat([curr_df[['code']], prev_df[['code']]]).drop_duplicates()
    ward_df['outer'] = ward_df['code'].apply(lambda x: x.split(':')[0])
    ward_df = ward_df.assign(defid=range(dc_start, dc_start + ward_df.shape[0]))
    dict_df = pd.concat([ward_df, dict_df, event_df], sort=False)
    dict_df['def'] = 'DEF'
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    set_df = dict_df[dict_df['outer'].notnull()][['outer', 'code']].drop_duplicates()
    set_df['set'] = 'SET'
    write_tsv(set_df[['set', 'outer', 'code']], dict_path, dict_file, mode='a')




'''
def create_labs_dict(raw_path, dict_path):
    labs = ['Abdominal_Asses', 'Acanthocytes', 'Acetone', 'Activity', 'Airway_Size', 'Airway_Type',
            'Anisocytosis', 'Barbiturates', 'Basophilic_Stippling', 'Benzodiazepines', 'Bite_Cells',
            'Blood_Gas_Type', 'BurrCells', 'CardiacMurmur', 'Color', 'Dacrocytes', 'Diagnosis_OP',
            'Ectopy_Freq', 'Ectopy_Type', 'Elliptocytes', 'Erythromycin_Given', 'FragmentsInBlood',
            'GCS_Eye', 'GCS_Motor', 'GCS_Verbal', 'GestationalAge', 'HA_Ab', 'HB_cAb', 'HB_sAb', 'HB_sAg',
            'HC_Ab', 'HIV_Ab', 'Head_of_Bed', 'Heart_Rythm', 'Hypochromia', 'Intubated', 'Level_Of_Consc',
            'Macrocytes', 'Microcytes', 'NuclearAb', 'Ovalocytes', 'PaceMaker_Mode', 'PaceMaker_Type',
            'Plateau_Off', 'PlateletsLarge', 'PlateletsManual', 'Poikilocytosis', 'Polychromasia', 'RBFC',
            'Schistocytes', 'Spherocytes', 'Target_Cells', 'Tricyclic_Antidepressants',
            'Urine_Amorphous_Sediment', 'Urine_Amphetamines', 'Urine_Bacteria', 'Urine_Barbiturates',
            'Urine_Benzodiazepines', 'Urine_Bilirubin', 'Urine_Calcium_Oxalate', 'Urine_Cocaine',
            'Urine_Eosinophils', 'Urine_Leukocytes', 'Urine_Methadone', 'Urine_Mucus', 'Urine_Nitrite',
            'Urine_Opitaes', 'Urine_Prot_Elec', 'Urine_Uric_Acid_Crystals', 'Urine_Yeast', 'Vent', 'Vent_Mode',
            'Vent_No', 'Vent_Type', 'VitaminK_Given', 'WBC_Clump', 'Eye_Opening', 'Verbal_Response',
            'Motor_Response', 'Urine_Color', 'Level_of_Consciousness']
    dict_file = 'dict.labs'
    dc_start = 3000
    labs_df = pd.read_csv(os.path.join(raw_path, 'LABEVENTS.csv'), encoding='utf-8')
    str_df = labs_df[(labs_df['VALUENUM'].isnull()) & (labs_df['VALUE'].notnull())]
    str_df.drop_duplicates('VALUE', inplace=True)
    #str_df['VALUE'] = replace_spaces(str_df['VALUE'])
    clean_vals = clean_values(str_df['VALUE'])
    val_list = clean_vals.unique().tolist()
    del labs_df
    #val_list = []
    char_val_list = []
    for char_df in pd.read_csv(os.path.join(raw_path, 'CHARTEVENTS.csv'), chunksize=5000000, quotechar='"'):
        #char_df = pd.read_csv(os.path.join(raw_path, 'CHARTEVENTS.csv'), encoding='utf-8')
        #str_df = char_df[(char_df['VALUENUM'].isnull()) & (char_df['VALUE'].notnull())]
        char_df['is_num'] = pd.to_numeric(char_df['VALUE'], errors='coarse')
        str_df = char_df[(char_df['is_num'].isnull()) & (char_df['VALUE'].notnull())]
        print(str_df.shape)
        if str_df.shape[0] == 0:
            continue
        str_df.drop_duplicates('VALUE', inplace=True)
        #str_df['VALUE'] = str_df['VALUE'].str.replace(',', '.')
        #str_df['VALUE'] = replace_spaces(str_df['VALUE'])
        clean_vals = clean_values(str_df['VALUE'])
        char_val_list = list(set(char_val_list + clean_vals.unique().tolist()))
        print(len(char_val_list))
    val_list = list(set(val_list + char_val_list))
    val_list.extend(['empty_field', '1', '36', '38', '331', '24', '29', '31', '32', '34', '35', '40'])
    vals_df = pd.Series(data=val_list).reset_index()
    vals_df['code'] = replace_spaces(vals_df[0])
    vals_df.dropna(inplace=True, how='any')
    vals_df.drop_duplicates(subset='code', inplace=True)
    vals_df = vals_df.assign(defid=range(dc_start, dc_start + vals_df.shape[0]))
    vals_df['def'] = 'DEF'
    write_tsv(vals_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(labs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
'''

def create_labs_dict(cfg, raw_path, dict_path):
    labs = ['Abdominal_Asses', 'Acanthocytes', 'Acetone', 'Activity', 'Airway_Size', 'Airway_Type',
            'Anisocytosis', 'Barbiturates', 'Basophilic_Stippling', 'Benzodiazepines', 'Bite_Cells',
            'Blood_Gas_Type', 'BurrCells', 'CardiacMurmur', 'Color', 'Dacrocytes', 'Diagnosis_OP',
            'Ectopy_Freq', 'Ectopy_Type', 'Elliptocytes', 'Erythromycin_Given', 'FragmentsInBlood',
            'GCS_Eye', 'GCS_Motor', 'GCS_Verbal', 'GestationalAge', 'HA_Ab', 'HB_cAb', 'HB_sAb', 'HB_sAg',
            'HC_Ab', 'HIV_Ab', 'Head_of_Bed', 'Heart_Rythm', 'Hypochromia', 'Intubated', 'Level_Of_Consc',
            'Macrocytes', 'Microcytes', 'NuclearAb', 'Ovalocytes', 'PaceMaker_Mode', 'PaceMaker_Type',
            'Plateau_Off', 'PlateletsLarge', 'PlateletsManual', 'Poikilocytosis', 'Polychromasia', 'RBFC',
            'Schistocytes', 'Spherocytes', 'Target_Cells', 'Tricyclic_Antidepressants',
            'Urine_Amorphous_Sediment', 'Urine_Amphetamines', 'Urine_Bacteria', 'Urine_Barbiturates',
            'Urine_Benzodiazepines', 'Urine_Bilirubin', 'Urine_Calcium_Oxalate', 'Urine_Cocaine',
            'Urine_Eosinophils', 'Urine_Leukocytes', 'Urine_Methadone', 'Urine_Mucus', 'Urine_Nitrite',
            'Urine_Opitaes', 'Urine_Prot_Elec', 'Urine_Uric_Acid_Crystals', 'Urine_Yeast', 'Vent', 'Vent_Mode',
            'Vent_No', 'Vent_Type', 'VitaminK_Given', 'WBC_Clump', 'Eye_Opening', 'Verbal_Response',
            'Motor_Response', 'Urine_Color', 'Level_of_Consciousness']
    dict_file = 'dict.labs'
    dc_start = 3000
    mimic_def = MimicLabs()
    db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username,
                               mimic_def.password)

    sql_query = "SELECT DISTINCT(value) FROM mimiclabs"
    df = pd.read_sql(sql_query, db_engine)
    df['is_num'] = pd.to_numeric(df['value'], errors='coarse')
    str_df = df[(df['is_num'].isnull()) & (df['value'].notnull()) & (df['value'].str.strip() != '')]
    clean_vals = clean_values(str_df['value'])
    val_list = clean_vals.unique().tolist()
    val_list.extend(['empty_field', '0',  '1', '8', '36', '38', '331', '24', '29', '31', '32', '33', '34', '35', '40'])
    vals_df = pd.Series(data=val_list, name='code').reset_index()
    vals_df = vals_df.assign(defid=range(dc_start, dc_start + vals_df.shape[0]))
    vals_df['def'] = 'DEF'
    write_tsv(vals_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + ','.join(labs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))



def copy_icd9_dicts(cfg, dict_path):
    diag_sigs = ['DIAGNOSIS']
    dx_first_line = 'SECTION\t' + ','.join(diag_sigs) + '\n'
    proc_sigs = 'PROCEDURES'
    sg_first_line = 'SECTION\t' + proc_sigs + '\n'
    onto_folder = os.path.join(fixOS(cfg.ontology_folder), 'ICD9', 'dicts')
    onto_files = os.listdir(onto_folder)
    for ont in onto_files:
        ont_full = os.path.join(onto_folder, ont)
        copy(ont_full, dict_path)
        if 'dx' in ont:
            add_fisrt_line(dx_first_line, os.path.join(dict_path, os.path.basename(ont)))
        else:
            add_fisrt_line(sg_first_line, os.path.join(dict_path, os.path.basename(ont)))

    missing_procs = ['3601', '3605', '3602']
    sg_file = 'dict.icd9sg'
    miss_df = pd.Series(missing_procs, name='code').reset_index()
    miss_df['code'] = 'ICD9_CODE:' + miss_df['code']
    miss_df = miss_df.assign(defid=range(950000, 950000 + miss_df.shape[0]))
    miss_df['def'] = 'DEF'
    write_tsv(miss_df[['def', 'defid', 'code']], dict_path, sg_file, mode='a')


def elixhauser_dict(cfg, dict_path):
    sig = 'DIAGNOSIS_Elixhauser'
    dict_file = 'dict.elixhauser'
    dict_df = pd.DataFrame(data=elixhauser_diag, columns=['elix_diag'])
    dict_df = dict_df.assign(defid=range(100000, 100000 + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    write_tsv(dict_df[['def', 'defid', 'elix_diag']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def ndc11_to9(ncd11):
    ndc9 = ncd11[0:9]
    ndc9_left = ndc9[0:5].astype(int).astype(str).zfill(4)
    if len(ndc9_left) < 5:
        ndc9_right = ndc9[6:].astype(int).astype(str).zfill(4)
    else:
        ndc9_right = ndc9[6:].astype(int).astype(str)
    return ndc9_left + '-' + ndc9_right


def create_drug_dict(cfg, raw_path, dict_path):
    sigs = ['DRUG_PRESCRIPTION', 'DRUG_ADMINISTERED']
    first_line = 'SECTION\t' + ','.join(sigs) + '\n'
    dict_file = 'dict.drugs'
    ds_start = 200000
    onto_folder = fixOS(cfg.ontology_folder)
    drug_df = pd.read_csv(os.path.join(raw_path, 'PRESCRIPTIONS.csv'), encoding='utf-8', na_filter=False, usecols=[7, 18, 12], dtype=str)
    drug_df.drop_duplicates(inplace=True)
    drug_df.loc[:, 'DRUG_NAME'] = 'DRUG:' + replace_spaces(drug_df['DRUG'].str.upper())
    drug_names = drug_df['DRUG_NAME'].unique().tolist()
    drug_df.loc[:, 'ROUTE'] = 'ROUTE:' + replace_spaces(drug_df['ROUTE'])
    routs = drug_df['ROUTE'].unique().tolist()

    dict_df = pd.DataFrame(data=drug_names+routs+['ROUTE:UNKNOWN', 'ROUTE_UNKNOWN', 'CATEGORY_UNKNOWN'], columns=['code'])
    dict_df.drop_duplicates(inplace=True)
    dict_df = dict_df.assign(defid=range(ds_start, ds_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    dict_df = dict_df[(dict_df['code'].notnull()) & (dict_df['code'].str.strip() != '')]
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')

    drug_df_mv = pd.read_csv(os.path.join(raw_path, 'INPUTEVENTS_MV.csv'), encoding='utf-8', na_filter=False, usecols=['ORDERCATEGORYNAME'])
    drug_df_mv.drop_duplicates(inplace=True)
    drug_df_mv['code'] = replace_spaces(drug_df_mv['ORDERCATEGORYNAME'].str[3:])

    drug_df_cv = pd.read_csv(os.path.join(raw_path, 'INPUTEVENTS_CV.csv'), encoding='utf-8', na_filter=False, usecols=['ORIGINALROUTE'])
    drug_df_cv.drop_duplicates(inplace=True)
    drug_df_cv['code'] = replace_spaces(drug_df_cv['ORIGINALROUTE'])
    dict_df3 = pd.concat([drug_df_mv[['code']], drug_df_cv[['code']]])
    dict_df3.drop_duplicates(inplace=True)
    dict_df3 = dict_df3[(dict_df3['code'].notnull()) & (dict_df3['code'].str.strip() != '')]
    ds_start = dict_df['defid'].max()+1
    dict_df3 = dict_df3.assign(defid=range(ds_start, ds_start + dict_df3.shape[0]))
    dict_df3['def'] = 'DEF'
    write_tsv(dict_df3[['def', 'defid', 'code']], dict_path, dict_file, mode='a')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


    # NDC DRUGS MAP
    set_file = 'dict.drug_set'
    ndc_df = drug_df.drop_duplicates(['DRUG_NAME', 'NDC'])
    ndc_df = ndc_df[(ndc_df['NDC'].notnull()) & (ndc_df['NDC'].str.len() > 9)]
    ndc_df['NDC9_r'] = ndc_df['NDC'].str[0:5].astype(int).astype(str).str.zfill(4)
    ndc_df['NDC9_l'] = ndc_df['NDC'].str[5:9].astype(int).astype(str).str.zfill(4)
    ndc_df.loc[ndc_df['NDC9_r'].str.len() == 5, 'NDC9_l'] = ndc_df['NDC'].str[6:10].astype(int).astype(str).str.zfill(3)
    ndc_df.loc[:, 'NDC9'] = 'NDC_CODE:' + ndc_df['NDC9_r'] + '-' + ndc_df['NDC9_l']
    ndc_df['set'] = 'SET'
    write_tsv(ndc_df[['set', 'NDC9', 'DRUG_NAME']], dict_path, set_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))

    onto_files = [os.path.join(onto_folder, 'NDC', 'dicts', 'dict.ndc_defs')]
    for ont in onto_files:
        copy(ont, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(ont)))
    #Add missig NDCS:
    ndc_def_dict = 'dict.ndc_defs'
    ndc_def_df = pd.read_csv(os.path.join(dict_path, ndc_def_dict), sep='\t', names=['def', 'defid', 'code'], skiprows=1)
    ndc_def_df = ndc_def_df[ndc_def_df['code'].str.contains('NDC_CODE')]
    missing = ndc_df[~ndc_df['NDC9'].isin(ndc_def_df['code'].values)]
    missing.drop_duplicates('NDC9', inplace=True)
    missing.loc[:, 'NDC_DRUG_NAME'] = missing['NDC9'].str.replace('NDC_CODE:', '') + ':' + missing['DRUG_NAME']
    miiss_dict = code_desc_to_dict_df(missing, ndc_def_df['defid'].max()+1, ['NDC9', 'NDC_DRUG_NAME'])
    write_tsv(miiss_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='a')


    # Find Antibiotic from d_item table
    not_anti = [225857, 225871, 225882, 225896, 225897, 225903, 225837, 228003]
    mv_anti_df = pd.read_csv(os.path.join(raw_path, 'D_ITEMS.csv'), encoding='utf-8', na_filter=False)
    mv_anti_df = mv_anti_df[(mv_anti_df['LINKSTO'] == 'inputevents_mv') & (mv_anti_df['CATEGORY'] == 'Antibiotics')]
    mv_anti_df = mv_anti_df[~mv_anti_df['ITEMID'].isin(not_anti)]

    row_list = []
    for med in mv_anti_df['LABEL'].str.upper().str.strip():
        meds_splt = med.replace('/', ' ').split(' ')
        for ms in meds_splt:
            if len(ms) < 3 or ms == 'potassium':
                continue
            for i, r in drug_df.iterrows():
                if ms in r['DRUG_NAME'].strip():
                    row_list.append(r)
    drug_anti_df = pd.DataFrame(row_list)
    drug_anti_df.drop_duplicates('DRUG_NAME', inplace=True)
    drug_anti_df['set'] = 'SET'
    drug_anti_df['outer'] = 'Antibiotics'
    write_tsv(drug_anti_df[['set', 'outer', 'DRUG_NAME']], dict_path, set_file, mode='a')


def create_itemid_dict(cfg, raw_path, dict_path):
    sigs = ['DRUG_ADMINISTERED', 'PROCEDURES']
    first_line = 'SECTION\t' + ','.join(sigs) + '\n'
    dict_file = 'dict.itemid'
    ds_start = 100

    itemd_df = pd.read_csv(os.path.join(raw_path, 'D_ITEMS.csv'), encoding='utf-8', na_filter=False, usecols=['ITEMID', 'LABEL', 'LINKSTO', 'CATEGORY'], dtype=str)
    itemd_df = itemd_df[itemd_df['LINKSTO'].isin(['inputevents_cv', 'inputevents_mv', 'procedureevents_mv'])]
    itemd_df['ITEMID'] = 'ITEMID:' + itemd_df['ITEMID'].astype(int).astype(str)
    itemd_df['LABEL'] = itemd_df['ITEMID'] + ':' + replace_spaces(itemd_df['LABEL'])
    dict_df2 = code_desc_to_dict_df(itemd_df, ds_start, ['ITEMID', 'LABEL'])
    dict_df2 = dict_df2.append({'def': 'DEF', 'defid': dict_df2['defid'].max()+1, 'code': 'Antibiotics'}, ignore_index=True)
    write_tsv(dict_df2[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    # Find Antibiotic from d_item table
    not_anti = [225857, 225871, 225882, 225896, 225897, 225903, 225837, 228003]
    mv_anti_df = itemd_df[(itemd_df['LINKSTO'] == 'inputevents_mv') & (itemd_df['CATEGORY'] == 'Antibiotics')]
    mv_anti_df = mv_anti_df[~mv_anti_df['ITEMID'].isin(not_anti)]
    mv_anti_df['set'] = 'SET'
    write_tsv(mv_anti_df[['set', 'CATEGORY', 'LABEL']], dict_path, dict_file, mode='a')


def cpt_dict(cfg, raw_path, dict_path):
    sigs = ['PROCEDURES_CPT']
    first_line = 'SECTION\t' + ','.join(sigs) + '\n'
    dict_file = 'dict.cpt'

    ont_file = os.path.join(fixOS(cfg.ontology_folder), 'CPT', 'dicts', dict_file)
    copy(ont_file, dict_path)
    missing = ['G0364', 'G0002', 'G0121', 'G0272', '99999']
    missing_df = pd.DataFrame(data=missing, columns=['code'])
    missing_df = missing_df.assign(defid=range(720000, 720000 + missing_df.shape[0]))
    missing_df['code'] = 'CPT_CODE:' + missing_df['code']
    missing_df['def'] = 'DEF'
    write_tsv(missing_df[['def', 'defid', 'code']], dict_path, dict_file, mode='a')
    add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(ont_file)))

    '''
    ds_start = 1000
    cpt_df = pd.read_csv(os.path.join(raw_path, 'CPTEVENTS.csv'), encoding='utf-8', na_filter=False, dtype=str,
                         usecols=['CPT_CD', 'SUBSECTIONHEADER', 'DESCRIPTION'])
    cpt_df.drop_duplicates(inplace=True)
    cpt_df['CPT_CD'] = 'CPT_CODE:' + cpt_df['CPT_CD']
    cpt_df.loc[cpt_df['SUBSECTIONHEADER'].isnull(), 'SUBSECTIONHEADER'] = cpt_df['DESCRIPTION']
    cpt_df['SUBSECTIONHEADER'] = replace_spaces(cpt_df['SUBSECTIONHEADER'])
    dict_df = code_desc_to_dict_df(cpt_df, ds_start, ['CPT_CD', 'SUBSECTIONHEADER'])
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    '''


def drg_dict(cfg, raw_path, dict_path):
    sigs = ['DRG']
    first_line = 'SECTION\t' + ','.join(sigs) + '\n'
    dict_file = 'dict.drg'
    ds_start = 1000
    drg_df = pd.read_csv(os.path.join(raw_path, 'DRGCODES.csv'), encoding='utf-8', na_filter=False, dtype=str,
                         usecols=['DRG_TYPE', 'DRG_CODE', 'DESCRIPTION'])
    drg_df.drop_duplicates(['DRG_TYPE', 'DRG_CODE'], inplace=True)
    drg_df['DRG_CODE'] = drg_df['DRG_TYPE'] + ':' + drg_df['DRG_CODE']
    drg_df['DESCRIPTION'] = replace_spaces(drg_df['DESCRIPTION'])
    drg_df['DESCRIPTION'] = drg_df['DRG_CODE'] + ':' + drg_df['DESCRIPTION']
    dict_df = code_desc_to_dict_df(drg_df, ds_start, ['DRG_CODE', 'DESCRIPTION'])
    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


if __name__ == '__main__':
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(work_folder, 'rep_configs', 'dicts')
    final_path = os.path.join(work_folder, 'FinalSignals')
    raw_path = fixOS(cfg.data_folder)

    #create_gender_dict(dict_path)
    create_dict_from_admission(raw_path, dict_path)
    #create_transfers_dict(dict_path)
    #create_labs_dict(cfg, raw_path, dict_path)
    #copy_icd9_dicts(cfg, dict_path)
    #elixhauser_dict(cfg, dict_path)
    #create_drug_dict(cfg, raw_path, dict_path)
    #create_itemid_dict(cfg, raw_path, dict_path)
    #cpt_dict(cfg, raw_path, dict_path)
    #drg_dict(cfg, raw_path, dict_path)
