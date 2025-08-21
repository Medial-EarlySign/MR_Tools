import os
import pandas as pd
from shutil import copy
from Configuration import Configuration
from utils import write_tsv, fixOS, add_fisrt_line, is_nan, add_last_line
from rambam_utils import hier_field_to_dict, get_dict_item
from stage_to_drugs import med_maps
from stage_to_microbiology import get_specimen_map


def code_desc_to_dict_df(df, dc_start):
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))

    to_stack = df[['defid', 'code', 'desc']].set_index('defid', drop=True)
    dict_df = to_stack.stack().to_frame()
    dict_df['defid'] = dict_df.index.get_level_values(0)
    dict_df.rename({0: 'code'}, axis=1, inplace=True)
    dict_df['def'] = 'DEF'
    return dict_df


def raw_to_simple_dict(signal, raw_df, desc_field, idstart, dict_path, dict_file, trans_map=pd.Series(), empty_line=True):
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    code_field = desc_field[:-4]
    dict_df = raw_df.drop_duplicates(subset=[desc_field, code_field])
    dict_df.rename(columns={desc_field: 'hier'}, inplace=True)
    dict_df['hier_dict'] = dict_df['hier'].apply(lambda x: hier_field_to_dict(x))
    dict_df['code'] = dict_df['hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    assert code_field in dict_df.columns
    dict_df['code'] = dict_df['code'].where(dict_df['code'] != '_', dict_df[code_field])
    dict_df['code'] = dict_df['code'].astype(str)
    dict_df = dict_df[dict_df['code'] != 'Null']
    dict_df['desc'] = dict_df['hier_dict'].apply(lambda x: get_dict_item(x, '1'))
    if not trans_map.empty:
        dict_df['desc'] = dict_df['desc'].map(trans_map)

    dict_df['desc'] = get_desc(dict_df)
    dict_df = code_desc_to_dict_df(dict_df, idstart)
    if empty_line:
        dict_df = dict_df.append(pd.Series({'def': 'DEF', 'defid': 1, 'code': 'EMPTY_VALUE'}), ignore_index=True, sort=False)

    #Add to dict codes with numeric format - there are cases where code == 973 and in Hier it is 00973
    dict_df['codef'] = pd.to_numeric(dict_df['code'], downcast='integer', errors='coerce')
    def_dict = dict_df[dict_df['codef'].notnull()]
    def_dict['codef'] = def_dict['codef'].astype(int).astype(str)
    def_dict = def_dict[def_dict['code'] != def_dict['codef']].drop_duplicates(subset='codef')
    def_dict = def_dict[~def_dict['codef'].isin(dict_df['code'].values)]
    def_dict = def_dict.drop(columns='code').rename(columns={'codef': 'code'})
    dict_df = dict_df.append(def_dict, ignore_index=True, sort=False)
    dict_df.drop_duplicates(subset='code', inplace=True)
    dict_df.sort_values(by='defid', inplace=True)

    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    return dict_df


def get_desc(df, prefix='RAMBAM_CODE', with_code=True):
    if with_code:
        return prefix + ':' + df['code'].astype(str) + ':' + df['desc']
    else:
        return prefix + ':' + df['desc']


def create_intermediates_files(raw_table_path, inter_path, med_file_name, details_file_name, unit_quant_file_name):
    all_meds_df = pd.DataFrame()
    all_det_df = pd.DataFrame()
    all_unit_qunt_df = pd.DataFrame()
    for event_type, sig in med_maps.items():
        print('Reading table for ' + event_type)
        raw_table = pd.read_csv(os.path.join(raw_table_path, event_type), sep='\t',  encoding='utf-8')
        meds_df = raw_table[['medicationcode', 'medicationcodeHier']]
        all_meds_df = all_meds_df.append(meds_df.drop_duplicates(), ignore_index=True, sort=False)

        det_df = raw_table[['frequencycode', 'frequencycodeHier',
                            'routecode', 'routecodeHier',
                            'formcode', 'formcodeHier']]

        all_det_df = all_det_df.append(det_df.drop_duplicates(),  ignore_index=True, sort=False)

        unit_df = raw_table[['quantitiy_unitcode', 'quantitiy_unitcodeHier', 'quantity_value']]
        all_unit_qunt_df = all_unit_qunt_df.append(unit_df.drop_duplicates(), ignore_index=True, sort=False)

    all_meds_df.to_csv(os.path.join(inter_path, med_file_name), sep='\t')
    all_det_df.to_csv(os.path.join(inter_path, details_file_name), sep='\t')
    all_unit_qunt_df.to_csv(os.path.join(inter_path, unit_quant_file_name), sep='\t')



def create_atc_hier(meds_df, out_path):
    atc_start = 30000
    dict_file = 'dict.atc_defs'
    dict_set_file = 'dict.atc_sets'

    if os.path.exists(os.path.join(out_path, dict_file)):
        os.remove(os.path.join(out_path, dict_file))
    if os.path.exists(os.path.join(out_path, dict_set_file)):
        os.remove(os.path.join(out_path, dict_set_file))

    atc_def_df = pd.DataFrame()
    stc_set_df = pd.DataFrame()
    meds_df['hier_dict'] = meds_df['medicationcodeHier'].apply(lambda x: hier_field_to_dict(x))
    meds_df['code'] = meds_df['hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    meds_df['desc'] = meds_df['hier_dict'].apply(lambda x: get_dict_item(x, '1'))
    meds_df['desc'] = get_desc(meds_df)

    ser_hier = meds_df['desc']
    for i in range(2, 14, 2):
        stc_set_df_1 = pd.DataFrame()
        if i == 2:  # not ATC but generic names should include the rambam name
            ser1 = 'GENERIC::' + meds_df['hier_dict'].apply(lambda x: get_dict_item(x, str(i))) + ':' + meds_df['hier_dict'].apply(lambda x: get_dict_item(x, str(i + 1)))
        else:
            ser1 = 'ATC:' + meds_df['hier_dict'].apply(lambda x: get_dict_item(x, str(i))) + ':' + meds_df['hier_dict'].apply(lambda x: get_dict_item(x, str(i+1)))
        stc_set_df_1 = stc_set_df_1.assign(inner=ser_hier.values)
        stc_set_df_1 = stc_set_df_1.assign(outer=ser1.values)
        if i > 2:
            ser_hier = ser1
        atc_def_df = atc_def_df.append(pd.DataFrame(ser1), sort=False)
        stc_set_df = stc_set_df.append(pd.DataFrame(stc_set_df_1), sort=False)
    atc_def_df.drop_duplicates(inplace=True)
    atc_def_df = atc_def_df.assign(defid=range(atc_start, atc_start + atc_def_df.shape[0]))
    atc_def_df['def'] = 'DEF'

    stc_set_df.drop_duplicates(inplace=True)
    stc_set_df['set'] = 'SET'

    write_tsv(atc_def_df[['def', 'defid', 'hier_dict']], out_path, dict_file)
    write_tsv(stc_set_df[['set', 'outer', 'inner']], out_path, dict_set_file)
    first_line = 'SECTION' + '\t' + ",".join(med_maps.values()) + '\n'
    add_fisrt_line(first_line, os.path.join(out_path, dict_file))
    add_fisrt_line(first_line, os.path.join(out_path, dict_set_file))
    print('DONE atc dicts')


def create_info_dict(info_df, out_path):
    inf_start = 220000
    dict_file = 'dict.drug_info_defs'
    if os.path.exists(os.path.join(out_path, dict_file)):
        os.remove(os.path.join(out_path, dict_file))

    info_df['freq_code'] = info_df['freq_hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    info_df['freq_name'] = info_df['freq_hier_dict'].apply(lambda x: get_dict_item(x, '1'))

    info_df['route_code'] = info_df['route_hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    info_df['route_name'] = info_df['route_hier_dict'].apply(lambda x: get_dict_item(x, '1'))

    info_df['form_code'] = info_df['form_hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    info_df['form_name'] = info_df['form_hier_dict'].apply(lambda x: get_dict_item(x, '1'))

    info_df['unit_code'] = info_df['unit_hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    info_df['unit_name'] = info_df['unit_hier_dict'].apply(lambda x: get_dict_item(x, '1'))

    info_df['code'] = 'ROUTE:' + info_df['route_code'] + '|FORM:' + info_df['form_code'] + '|FREQ:' + info_df['freq_code']
    info_df['desc'] = 'ROUTE:' + info_df['route_name'] + '|FORM:' + info_df['form_name'] + '|FREQ:' + info_df['freq_name']

    med_def_id = info_df[['code', 'desc']].copy()
    drug_info_dict = code_desc_to_dict_df(med_def_id, inf_start)
    drug_info_dict.drop_duplicates(subset='code', inplace=True)

    write_tsv(drug_info_dict[['def', 'defid', 'code']], out_path, dict_file)
    first_line = 'SECTION' + '\t' + ",".join(med_maps.values()) + '\n'
    add_fisrt_line(first_line, os.path.join(out_path, dict_file))
    print('DONE drug_info dict')


def create_drug_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    code_path = fixOS(cfg.code_folder)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    inter_path = os.path.join(out_folder, 'outputs')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    inter_med_file = 'all_meds_hier.csv'
    inter_details_file = 'all_details.csv'
    inter_unit_qunt_file = 'all_unit_quant.csv'
    if not (os.path.exists(os.path.join(inter_path, inter_med_file))):
        create_intermediates_files(table_path, inter_path, inter_med_file, inter_details_file, inter_unit_qunt_file)

    all_meds_df = pd.read_csv(os.path.join(inter_path, inter_med_file), sep='\t')
    all_meds_df.drop_duplicates(inplace=True)
    #all_meds_df = all_meds_df[all_meds_df['medicationcodeHier'] != 'None']
    dc_start = 1200
    dict_file = 'dict.drugs_defs'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    raw_to_simple_dict(",".join(med_maps.values()), all_meds_df, 'medicationcodeHier', dc_start, dict_path, dict_file)
    create_atc_hier(all_meds_df, dict_path)

    dict_file = 'dict.dosage'
    dc_start = 7000
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    all_units_df = pd.read_csv(os.path.join(inter_path, inter_unit_qunt_file), sep='\t')
    all_units_df.drop_duplicates(subset=['quantitiy_unitcode', 'quantitiy_unitcodeHier', 'quantity_value'], inplace=True)
    all_units_df['unit_hier_dict'] = all_units_df['quantitiy_unitcodeHier'].apply(lambda x: hier_field_to_dict(x))
    all_units_df['unit_code'] = all_units_df['unit_hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    all_units_df['unit_name'] = all_units_df['unit_hier_dict'].apply(lambda x: get_dict_item(x, '1'))
    all_units_df['quantity_value'] = all_units_df['quantity_value'].astype(str)
    all_units_df['quantity_value'] = all_units_df['quantity_value'].where(all_units_df['quantity_value'].str[-2:] != '.0', all_units_df['quantity_value'].str[:-2])
    all_units_df['code'] = all_units_df['quantity_value'].astype(str).replace(r'.0$', '') + '|' + all_units_df['unit_name']
    missing = [{'code': '0.013|Mcg/Kg/min'}, {'code': '0.014|mg'}, {'code': '0.037|mg'}, {'code': '0.558|mg'}]
    all_units_df = all_units_df.append(missing, ignore_index=True)
    all_units_df.drop_duplicates(subset='code', inplace=True)
    all_units_df['def'] = 'DEF'
    all_units_df = all_units_df.assign(defid=range(dc_start, dc_start + all_units_df.shape[0]))
    write_tsv(all_units_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\t'+",".join(med_maps.values())+'\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    #all_info_df['freq_hier_dict'] = all_info_df['frequencycodeHier'].apply(lambda x: hier_field_to_dict(x))
    #all_info_df['route_hier_dict'] = all_info_df['routecodeHier'].apply(lambda x: hier_field_to_dict(x))
    #all_info_df['form_hier_dict'] = all_info_df['formcodeHier'].apply(lambda x: hier_field_to_dict(x))
    #all_info_df['unit_hier_dict'] = all_info_df['quantitiy_unitcodeHier'].apply(lambda x: hier_field_to_dict(x))
    #create_info_dict(all_info_df, dict_path)
    dict_file = 'dict.route_form'
    dc_start = 25000
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    rounte_form_map_df = pd.read_csv(os.path.join(code_path, 'route_form_mapping.txt'), sep='\t')
    rounte_form_def_df = rounte_form_map_df.drop_duplicates(subset ='Route|FORM')[['Route|FORM']]
    rounte_form_def_df.rename(columns={'Route|FORM': 'code'}, inplace=True)
    rounte_form_def_df['def'] = 'DEF'
    rounte_form_def_df = rounte_form_def_df.assign(defid=range(dc_start, dc_start + rounte_form_def_df.shape[0]))
    write_tsv(rounte_form_def_df[['def', 'defid', 'code']], dict_path, dict_file)
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_procedure_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    code_folder = fixOS(cfg.code_folder)
    ontology_folder = os.path.join(code_folder, '..\\..\\DictUtils\\Ontologies\\')
    icd9_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.icd9sg')
    icd9_set_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.set_icd9sg')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    dc_start = 110000
    dict_file = 'dict.procedures'
    dict_set_file = 'dict.set_procedures'

    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    if os.path.exists(os.path.join(dict_path, dict_set_file)):
        os.remove(os.path.join(dict_path, dict_set_file))

    raw_table = pd.read_csv(os.path.join(table_path, 'ev_procedures'), sep='\t', encoding='utf-8', low_memory=False)
    raw_table_ins = pd.read_csv(os.path.join(table_path, 'ev_institutes'), sep='\t', encoding='utf-8', low_memory=False)
    raw_table = raw_table.append(raw_table_ins, ignore_index=True, sort=False)
    raw_to_simple_dict('PROCEDURE', raw_table, 'servicecodeHier', dc_start, dict_path, dict_file)

    # Need to add code that appears as in in code and in hier start with 0 eg code=239 in hier 0:0239

    proc_df = raw_table[['servicecodeHier']].drop_duplicates()
    proc_df['hier_dict'] = proc_df['servicecodeHier'].apply(lambda x: hier_field_to_dict(x))
    proc_df['code'] = proc_df['hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    proc_df['desc'] = proc_df['hier_dict'].apply(lambda x: get_dict_item(x, '1'))
    proc_df['desc'] = get_desc(proc_df)

    proc_def_id = proc_df[['code', 'desc']].copy()
    icd9_dict_df = pd.read_csv(icd9_dict, sep='\t', names=['def', 'medid', 'code'], header=1, low_memory=False)
    icd9_dict_df = pd.concat([icd9_dict_df, icd9_dict_df['code'].str.split(':', expand=True)], axis=1)
    set_df = proc_def_id.merge(icd9_dict_df, right_on=1, left_on='code', how='left')
    set_df = set_df[set_df['code_y'].notnull()][['code_y', 'desc']]
    set_df.drop_duplicates(subset='desc', keep='last',inplace=True)
    set_df['set'] = 'SET'
    first_line = 'SECTION\tPROCEDURE\n'
    write_tsv(set_df[['set', 'code_y', 'desc']], dict_path, dict_set_file)
    add_fisrt_line(first_line, os.path.join(dict_path, dict_set_file))
    copy(icd9_dict, dict_path)
    copy(icd9_set_dict, dict_path)
    add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(icd9_dict)))
    add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(icd9_set_dict)))

    print('DONE proc_dicts')


def create_clinic_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    code_folder = fixOS(cfg.code_folder)

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    trans_map = pd.read_csv(os.path.join(code_folder, 'dept_heb_to_eng.csv'), sep='\t', names=['heb', 'eng'], header=None)
    trans_map.replace(' ', '_', regex=True, inplace=True)
    trans_map = trans_map.set_index('heb')['eng']
    dc_start = 10000
    dict_file = 'dict.department'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    raw_table_visit = pd.read_csv(os.path.join(table_path, 'ev_outpatient_visits'), sep='\t', encoding='utf-8', low_memory=False)
    raw_table_stay = pd.read_csv(os.path.join(table_path, 'ev_transfers'), sep='\t', encoding='utf-8', low_memory=False)
    raw_table = raw_table_visit.append(raw_table_stay, sort=False)

    #  Craete clinic dict including translation
    def_dict = raw_to_simple_dict('VISIT,STAY', raw_table, 'departmentcodeHier', dc_start, dict_path, dict_file, trans_map)

    # Create visit type dict
    dict_file = 'dict.visittype'
    id_start = 10000 + def_dict.shape[0] + 100
    raw_to_simple_dict('VISIT', raw_table_visit, 'visittypeHier', id_start, dict_path, dict_file, empty_line=False)
    print('DONE STAY dicts')


def create_consult_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    dc_start = 10000
    dict_file = 'dict.consultations'
    raw_table = pd.read_csv(os.path.join(table_path, 'ev_consultations'), sep='\t', encoding='utf-8')
    simple_dict = raw_to_simple_dict('CONSULTATION', raw_table, 'consultingdepartmentHier', dc_start, dict_path, dict_file)

    print('DONE CONSULTATION dicts')


def create_admission_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    dc_start = 10000
    dict_file = 'dict.admissiontype'
    raw_table = pd.read_csv(os.path.join(table_path, 'ev_admissions'), sep='\t', encoding='utf-8')
    raw_to_simple_dict('ADMISSION', raw_table, 'admissionsourcecodeHier', dc_start, dict_path, dict_file)
    print('DONE ADMISSION dicts')


def match_ontology_to_ontology(diag_df, dict_path, dict_set_file):
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    ontology_folder = os.path.join(code_folder, '..\\..\\DictUtils\\Ontologies\\')
    icd9_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.icd9dx')
    icd9_set_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.set_icd9dx')
    icd10_dict = os.path.join(ontology_folder, 'ICD10', 'dicts', 'dict.icd10')
    icd10_set_dict = os.path.join(ontology_folder, 'ICD10', 'dicts', 'dict.set_icd10')

    # Merge rambam code with ICD9
    icd9_dict_df = pd.read_csv(icd9_dict, sep='\t', names=['def', 'medid', 'code'], header=1)
    icd9_dict_df = pd.concat([icd9_dict_df, icd9_dict_df['code'].str.split(':', expand=True)], axis=1)
    icd9_dict_df = icd9_dict_df[icd9_dict_df[0] == 'ICD9_DESC']

    icd10_dict_df = pd.read_csv(icd10_dict, sep='\t', names=['def', 'medid', 'code'], header=1)
    icd10_dict_df = pd.concat([icd10_dict_df, icd10_dict_df['code'].str.split(':', expand=True)], axis=1)
    icd10_dict_df = icd10_dict_df[icd10_dict_df[0] == 'ICD10_DESC']

    onto_map = icd9_dict_df.append(icd10_dict_df, sort=False)
    onto_map = onto_map.drop_duplicates(subset=1, keep='first').set_index(1)['code']
    diag_df['code_map'] = diag_df['code'].map(onto_map)
    diag_df['code_hr1_map'] = diag_df['code_hr1'].map(onto_map)
    diag_df['code_hr2_map'] = diag_df['code_hr2'].map(onto_map)

    set_df1 = diag_df[['code_hr1_map', 'code_map']]
    set_df1 = set_df1[set_df1['code_hr1_map'] != set_df1['code_map']]
    set_df1.dropna(inplace=True)
    set_df1.rename(columns={'code_hr1_map': 'outer', 'code_map': 'inner'}, inplace=True)

    set_df2 = diag_df[['code_hr2_map', 'code_hr1_map']]
    set_df2 = set_df2[set_df2['code_hr2_map'] != set_df2['code_hr1_map']]
    set_df2.dropna(inplace=True)
    set_df2.rename(columns={'code_hr2_map': 'outer', 'code_hr1_map': 'inner'}, inplace=True)

    set_df = pd.concat([set_df1, set_df2])
    set_df = set_df[set_df['outer'].str[:4] != set_df['inner'].str[:4]]  # Remove seting from the same ontology --> can be found in onto dicts
    set_df['set'] = 'SET'
    write_tsv(set_df[['set', 'outer', 'inner']], dict_path, dict_set_file)


def match_rambam_to_ontology(diag_df, dict_path, dict_set_file):
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    ontology_folder = os.path.join(code_folder, '..\\..\\DictUtils\\Ontologies\\')
    icd9_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.icd9dx')
    icd9_set_dict = os.path.join(ontology_folder, 'ICD9', 'dicts', 'dict.set_icd9dx')
    icd10_dict = os.path.join(ontology_folder, 'ICD10', 'dicts', 'dict.icd10')
    icd10_set_dict = os.path.join(ontology_folder, 'ICD10', 'dicts', 'dict.set_icd10')

    # Merge rambam code with ICD9
    icd9_dict_df = pd.read_csv(icd9_dict, sep='\t', names=['def', 'medid', 'code'], header=1)
    icd9_dict_df = pd.concat([icd9_dict_df, icd9_dict_df['code'].str.split(':', expand=True)], axis=1)
    icd9_dict_df = icd9_dict_df[icd9_dict_df[0] == 'ICD9_DESC']

    set_df1 = diag_df.merge(icd9_dict_df, right_on=1, left_on='code', how='left')
    set_df1 = set_df1[set_df1['code_y'].notnull()][['code_y', 'desc']]
    set_df1.drop_duplicates(subset='desc', keep='last', inplace=True)
    # No additional matched for hier 1 with ICD9

    # Merge rambam code with ICD10
    icd10_dict_df = pd.read_csv(icd10_dict, sep='\t', names=['def', 'medid', 'code'], header=1)
    icd10_dict_df = pd.concat([icd10_dict_df, icd10_dict_df['code'].str.split(':', expand=True)], axis=1)
    icd10_dict_df = icd10_dict_df[icd10_dict_df[0] == 'ICD10_DESC']

    diag_df_not_matched = diag_df[~diag_df['desc'].isin(set_df1['desc'].values)]  # Remove the matched values
    set_df2 = diag_df_not_matched.merge(icd10_dict_df, right_on=1, left_on='code', how='left')
    set_df2 = set_df2[set_df2['code_y'].notnull()][['code_y', 'desc']]

    # Merge hier 1 code with ICD10 with no .
    diag_df_not_matched = diag_df_not_matched[~diag_df_not_matched['desc'].isin(set_df2['desc'].values)]
    set_df3 = diag_df_not_matched.merge(icd10_dict_df, right_on=1, left_on='code_hr1', how='left')
    set_df3 = set_df3[set_df3['code_y'].notnull()][['code_y', 'desc']]

    # Merge hier 1 code with ICD10 with no .
    diag_df_not_matched = diag_df_not_matched[~diag_df_not_matched['desc'].isin(set_df3['desc'].values)]
    set_df4 = diag_df_not_matched.merge(icd10_dict_df, right_on=1, left_on='code_hr2', how='left')
    set_df4 = set_df4[set_df4['code_y'].notnull()][['code_y', 'desc']]

    set_df = pd.concat([set_df1, set_df2, set_df3, set_df4])
    set_df['set'] = 'SET'

    diad_sigs = ['DIAGNOSIS', 'DIAGNOSIS_PRIMARY', 'DIAGNOSIS_SECONDARY', 'DIAGNOSIS_PAST']
    diag_dicts = [icd9_dict, icd9_set_dict, icd10_dict, icd10_set_dict]
    write_tsv(set_df[['set', 'code_y', 'desc']], dict_path, dict_set_file)
    first_line = 'SECTION' + '\t' + ",".join(diad_sigs) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_set_file))
    for dc in diag_dicts:
        copy(dc, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(dc)))


def create_diagnosis_hier(raw_df, dict_path):
    dict_set_file = 'dict.diagnosis_sets'

    if os.path.exists(os.path.join(dict_path, dict_set_file)):
        os.remove(os.path.join(dict_path, dict_set_file))

    diag_df = raw_df[['conditioncode', 'conditioncodeHier']]
    diag_df.drop_duplicates(inplace=True)
    diag_df.rename(columns={'conditioncode': 'code', 'conditioncodeHier': 'hier'}, inplace=True)
    diag_df['hier_dict'] = diag_df['hier'].apply(lambda x: hier_field_to_dict(x))
    diag_df['code'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '0'))
    diag_df['desc'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '1'))
    diag_df['desc'] = get_desc(diag_df)

    diag_df['code_hr1'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '2'))
    diag_df['desc_hr1'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '3'))
    diag_df['code_hr1'] = diag_df['code_hr1'].str.replace('.', '')

    diag_df['code_hr2'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '4'))
    diag_df['desc_hr2'] = diag_df['hier_dict'].apply(lambda x: get_dict_item(x, '5'))
    diag_df['code_hr2'] = diag_df['code_hr2'].str.replace('.', '')

    match_rambam_to_ontology(diag_df, dict_path, dict_set_file)
    match_ontology_to_ontology(diag_df, dict_path, dict_set_file)


def create_diagnosis_dicts():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    inter_path = os.path.join(out_folder, 'outputs')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    inter_diag_file = 'all_diagnoses_hier.csv'
    dict_file = 'dict.diagnosis_defs'
    id_start = 110000
    if not (os.path.exists(os.path.join(inter_path, inter_diag_file))):
        print('Reading table for   ev_diagnoses')
        raw_table = pd.read_csv(os.path.join(table_path, 'ev_diagnoses'), sep='\t', encoding='utf-8',
                                dtype={'conditioncode': str})
        all_diag_df = raw_table[['conditioncode', 'conditioncodeHier', 'sequencenumber', 'sequencenumberHier']].drop_duplicates()
        all_diag_df.to_csv(os.path.join(inter_path, inter_diag_file), sep='\t')

    all_diag_df = pd.read_csv(os.path.join(inter_path, inter_diag_file), sep='\t')
    raw_to_simple_dict('DIAGNOSIS,DIAGNOSIS_PRIMARY,DIAGNOSIS_SECONDARY,DIAGNOSIS_PAST', all_diag_df.copy(),
                       'conditioncodeHier', id_start, dict_path, dict_file)

    create_diagnosis_hier(all_diag_df, dict_path)

    id_start = 110000 + all_diag_df.shape[0] + 100
    dict_file = 'dict.diagnosis_type'
    raw_to_simple_dict('DIAGNOSIS', all_diag_df.copy(),
                       'sequencenumberHier', id_start, dict_path, dict_file, empty_line=False)

    print('DONE DIAGNOSIS dicts')


def create_demographics_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    raw_table = pd.read_csv(os.path.join(table_path, 'ev_demographics_event'), sep='\t', encoding='utf-8')

    dc_start = 10000
    dict_file = 'dict.ethnicity'
    raw_to_simple_dict('ETHNICITY', raw_table, 'nationalityHier', dc_start, dict_path, dict_file)
    print('DONE ETHNICITY dicts')

    dc_start = 20000
    dict_file = 'dict.insurance'
    raw_to_simple_dict('INSURANCE', raw_table, 'hmoHier', dc_start, dict_path, dict_file)
    print('DONE INSURANCE dicts')


def create_surgery_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)

    raw_table = pd.read_csv(os.path.join(table_path, 'ev_surgeries'), sep='\t', encoding='utf-8')

    dc_start = 10000
    dict_file = 'dict.surgery'
    raw_to_simple_dict('SURGERY', raw_table, 'performedprocedurecodeHier', dc_start, dict_path, dict_file)

    dc_start = 50000
    dict_file = 'dict.surgerytype'
    raw_to_simple_dict('SURGERY', raw_table, 'surgerytypeHier', dc_start, dict_path, dict_file, empty_line=False)
    print('DONE SURGERY dicts')


def create_microbiology_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    code_path = fixOS(cfg.code_folder)

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    specimen_map = get_specimen_map(os.path.join(code_path, 'specimen_map.txt'))
    raw_table = pd.read_csv(os.path.join(table_path, 'ev_lab_results_microbiology'), sep='\t', encoding='utf-8')
    dc_start = 10000
    dict_file = 'dict.microbiology'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))

    all_spec_organ_df = raw_table.drop_duplicates(subset=['specimenmaterialcodeHier', 'specimenmaterialcode',
                                                          'microorganism_codeHier', 'microorganism_codeHier'])

    all_spec_organ_df['specimen_dict'] = all_spec_organ_df['specimenmaterialcodeHier'].apply(lambda x: hier_field_to_dict(x))
    all_spec_organ_df['specimen'] = all_spec_organ_df['specimen_dict'].apply(lambda x: get_dict_item(x, '1'))
    all_spec_organ_df['specimen'] = all_spec_organ_df['specimen'].map(specimen_map)
    all_spec_organ_df['specimen'].fillna('NoSpec', inplace=True)

    all_spec_organ_df['organism_dict'] = all_spec_organ_df['microorganism_codeHier'].apply(lambda x: hier_field_to_dict(x))
    all_spec_organ_df['organism'] = all_spec_organ_df['organism_dict'].apply(lambda x: get_dict_item(x, '2'))
    all_spec_organ_df.loc[all_spec_organ_df['organism'] == '_', 'organism'] = 'NoOrganism'

    all_spec_organ_df['code'] = all_spec_organ_df['specimen'] + '|' + all_spec_organ_df['organism']
    all_spec_organ_df.drop_duplicates(subset='code', inplace=True)
    all_spec_organ_df['def'] = 'DEF'

    all_anti_df = raw_table.drop_duplicates(subset=['antibioticcode', 'antibioticcodeHier',
                                                    'susceptibilityinterpretation', 'susceptibilityinterpretationHier'])

    all_anti_df['antibiotic_dict'] = all_anti_df['antibioticcodeHier'].apply(lambda x: hier_field_to_dict(x))
    all_anti_df['antibiotic_name'] = all_anti_df['antibiotic_dict'].apply(lambda x: get_dict_item(x, '1'))
    all_anti_df['antibiotic_atc'] = all_anti_df['antibiotic_dict'].apply(lambda x: get_dict_item(x, '2'))
    all_anti_df.loc[all_anti_df['antibiotic_name'] == '_', 'antibiotic_name'] = 'NoAntiBiotics'
    all_anti_df.loc[all_anti_df['antibiotic_atc'] == '_', 'antibiotic_atc'] = 'NA'

    all_anti_df['susceptibility_dict'] = all_anti_df['susceptibilityinterpretationHier'].apply(lambda x: hier_field_to_dict(x))
    all_anti_df['susceptibility'] = all_anti_df['susceptibility_dict'].apply(lambda x: get_dict_item(x, '1'))
    all_anti_df.loc[all_anti_df['susceptibility'] == '_', 'susceptibility'] = 'NA'
    all_anti_df['code'] = all_anti_df['antibiotic_name'] + '|' + all_anti_df['antibiotic_atc'] + '|' + all_anti_df['susceptibility']
    all_anti_df['def'] = 'DEF'
    dict_df = pd.concat([all_spec_organ_df[['def', 'code']], all_anti_df[['def', 'code']]])
    dict_df.drop_duplicates(inplace=True)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))

    write_tsv(dict_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\tMICROBIOLOGY\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_blood_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'rep_configs', 'dicts')
    table_path = os.path.join(out_folder, 'raw_tables')
    code_path = fixOS(cfg.code_folder)

    ontology_folder = os.path.join(code_path, '..\\..\\DictUtils\\Ontologies\\')
    isbt_dict_file = os.path.join(ontology_folder, 'ISBT', 'dicts', 'dict.isbt')
    isbt_dict_df = pd.read_csv(isbt_dict_file, sep='\t', names=['def', 'medid', 'code'], header=None)
    isbt_dict_df = isbt_dict_df[isbt_dict_df['def'] == 'DEF']
    isbt_dict_df['list'] = isbt_dict_df['code'].str.split(':')
    isbt_dict_df['isbt'] = isbt_dict_df.apply(lambda row: row['list'][1], axis=1)

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(table_path)):
        raise NameError('config error - table path don''t exists')

    if not (os.path.exists(dict_path)):
        os.makedirs(dict_path)
    raw_table_blood = pd.read_csv(os.path.join(table_path, 'ev_blood_bank'), sep='\t', encoding='utf-8')
    pb_start = 10000
    dict_file = 'dict.blood_product'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    bp_dict = raw_to_simple_dict('BLOOD_PRODUCT', raw_table_blood, 'bloodproducttypeHier', pb_start, dict_path, dict_file)

    bp_dict['short_code'] = bp_dict['code'].str[0:5]
    mrg = bp_dict.merge(isbt_dict_df, how='left', left_on='short_code', right_on='isbt')
    mrg = mrg[mrg['isbt'].notnull()]
    mrg = mrg[mrg['code_y'].str.contains('ISBT_DESC')]
    set_dict = mrg[['code_y', 'code_x']]
    set_dict['set'] = 'SET'
    write_tsv(set_dict[['set', 'code_y', 'code_x']], dict_path, dict_file)
    first_line = 'SECTION\tBLOOD_PRODUCT\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    copy(isbt_dict_file, dict_path)
    add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(isbt_dict_file)))

    print(mrg)


if __name__ == '__main__':
    create_drug_dicts()
    # create_procedure_dict()
    # create_clinic_dict()
    # create_consult_dict()
    # create_admission_dict()
    # create_diagnosis_dicts()
    # create_demographics_dict()
    # create_surgery_dict()
    # create_microbiology_dict()
    # create_blood_dict()

