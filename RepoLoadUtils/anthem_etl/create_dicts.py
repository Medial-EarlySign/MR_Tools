import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df
from DB import DB
from sql_utils import create_postgres_engine_generic
from shutil import copy


def gender_dict():
    signal = 'GENDER'
    cfg = Configuration()

    dict_path = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    dict_file = 'dict.gender'

    dict1 = {1: 'M', 2: 'F'}
    df = pd.Series(dict1).reset_index()
    df['def'] = 'DEF'
    write_tsv(df[['def', 'index', 0]], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def state_dict():
    signal = 'STATE'
    cfg = Configuration()

    dict_path = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    dict_file = 'dict.state'
    dc_start = 100
    db_det = DB()
    demo_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_eligibility_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    sql_query = "SELECT distinct(state) FROM " + demo_table
    state_df = pd.read_sql_query(sql_query, db_engine)
    state_df = state_df[state_df['state'].str.strip() != '']
    state_df = state_df.assign(defid=range(dc_start, dc_start + state_df.shape[0]))
    state_df['def'] = 'DEF'
    write_tsv(state_df[['def', 'defid', 'state']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


# Assuming dict with values from load is in dict.diag
def diag_dicts():
    signal = 'DIAGNOSIS'
    cfg = Configuration()
    dict_path = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    onto_folder = cfg.ontology_folder

    dict_file = 'dict.diagnosis'
    # Get all codes from DIAGNOSIS loading files:
    final_path = os.path.join(cfg.work_path, 'FinalSignals')
    load_files = os.listdir(final_path)
    load_files = [x for x in load_files if x.startswith(signal)]
    unique_digs = pd.DataFrame()
    for fl in load_files:
        file1 = os.path.join(final_path, fl)
        df = pd.read_csv(file1, sep='\t', usecols=[3], names=['code'])
        #df.drop_duplicates(inplace=True)
        unique_digs = unique_digs.append(df.drop_duplicates())
    unique_digs.drop_duplicates(inplace=True)
    #unique_digs = pd.read_csv(os.path.join(dict_path, 'dict.diag'), sep='\t', usecols=[2], names=['code'], skiprows=1)

    icd10_dict = os.path.join(onto_folder, 'ICD10', 'dicts', 'dict.icd10')
    icd10_df = pd.read_csv(icd10_dict, sep='\t', usecols=[1, 2], names=['defid', 'code'])
    icd10_codes = icd10_df[icd10_df['code'].str.contains('ICD10_CODE')]

    icd9_dict = os.path.join(onto_folder, 'ICD9', 'dicts', 'dict.icd9dx')
    icd9_df = pd.read_csv(icd9_dict, sep='\t', usecols=[1, 2], names=['defid', 'code'])
    icd9_codes = icd9_df[icd9_df['code'].str.contains('ICD9_CODE')]
    icds = icd10_codes.append(icd9_codes)

    cpt_dict = os.path.join(onto_folder, 'CPT', 'dicts', 'dict.cpt')
    cpt_df = pd.read_csv(cpt_dict, sep='\t', usecols=[1, 2], names=['defid', 'code'])
    cpt_codes = cpt_df[cpt_df['code'].str.contains('CPT_CODE')]
    icds = icds.append(cpt_codes)

    miss = unique_digs.merge(icds, on='code', how='left')
    miss = miss[miss['defid'].isnull()][['code']]

    dc_start = 1000
    miss = miss.assign(defid=range(dc_start, dc_start + miss.shape[0]))
    miss['def'] = 'DEF'
    write_tsv(miss[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    # Copy ICD9 and ICD10 def set and map file
    onto_files = [os.path.join(onto_folder, 'CPT', 'dicts', 'dict.cpt'),
                  os.path.join(onto_folder, 'ICD10', 'dicts', 'dict.icd10'),
                  os.path.join(onto_folder, 'ICD10', 'dicts', 'dict.set_icd10'),
                  os.path.join(onto_folder, 'ICD9', 'dicts', 'dict.icd9dx'),
                  os.path.join(onto_folder, 'ICD9', 'dicts', 'dict.set_icd9dx'),
                  ]
    for ont in onto_files:
        copy(ont, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(ont)))


def get_ndc_dict_enriched(cfg):
    # read NDSc from DB
    db_det = DB()
    idc10_table = 'pk_us_487_o_rgprc2ltzklg_anthem_opendata_ndc_product'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    sql_query = "SELECT product_ndc as code, proprietary_name as desc FROM " + idc10_table
    ndc_df = pd.read_sql_query(sql_query, db_engine)

    # Read generic NDC dict
    onto_folder = cfg.ontology_folder
    ndc_dict_file = os.path.join(onto_folder, 'NDC', 'dicts', 'dict.ndc_defs')
    ndc_dict_full = pd.read_csv(ndc_dict_file, sep='\t', names=['def', 'defid', 'code'])
    ndc_dict_df = ndc_dict_full[ndc_dict_full['code'].str.contains('NDC_CODE')].copy()
    ndc_dict_df['code'] = ndc_dict_df['code'].str.replace('NDC_CODE:', '')
    mrg = ndc_df.merge(ndc_dict_df, on='code', how='outer')
    missing_ndcs = mrg[mrg['defid'].isnull()].copy()

    missing_ndcs['desc'] = replace_spaces(missing_ndcs['desc'].str.upper())
    missing_ndcs['desc'] = 'NDC_DESC:' + missing_ndcs['code'] + ':' + missing_ndcs['desc']
    missing_ndcs['code'] = 'NDC_CODE:' + missing_ndcs['code']
    missing_ndcs.drop_duplicates(inplace=True)
    missing_dict = code_desc_to_dict_df(missing_ndcs, ndc_dict_full['defid'].max()+10, ['code', 'desc'])
    ndc_dict_full = ndc_dict_full.append(missing_dict, sort=False)

    # Read NDC manualy added not found list - list of NDC found in Anthem and not in DB/FDA
    man_df = pd.read_csv(os.path.join(cfg.code_folder, 'missing_ndc_manual.txt'), sep='\t', usecols=[0, 1])
    man_df['desc'] = replace_spaces(man_df['desc'].str.upper())
    man_df['desc'] = 'NDC_DESC:' + man_df['code'] + ':' + man_df['desc']
    man_df['code'] = 'NDC_CODE:' + man_df['code']
    man_df = code_desc_to_dict_df(man_df, ndc_dict_full['defid'].max() + 10, ['code', 'desc'])
    ndc_dict_full = ndc_dict_full.append(man_df, sort=False)
    return ndc_dict_full


def to9(ndc):
    splits = ndc.split('-')
    a1 = splits[0].zfill(5)
    a2 = splits[1].zfill(4)
    return a1+a2


def drug_dicts():
    signal = 'Drug'
    cfg = Configuration()
    dict_path = os.path.join(cfg.work_path, 'rep_configs', 'dicts')
    onto_folder = cfg.ontology_folder

    # Create def for each NDC code from DB and from generic NDC dict
    dict_file = 'dict.ndc'
    en_dict = get_ndc_dict_enriched(cfg)
    write_tsv(en_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    # def dict for each code in the source created during load --> dics.drugs

    # create sets for code from source to NDC
    set_file = 'dict.ndc_set'
    unique_drug = pd.read_csv(os.path.join(dict_path, 'dict.drugs'), sep='\t', usecols=[2], names=['code'], skiprows=1)
    unique_drug.drop_duplicates(inplace=True)
    unique_drug.loc[:, 'code9'] = unique_drug['code'].str[4:13]

    en_dict = en_dict[en_dict['code'].str.contains('NDC_CODE')][['code']].copy()
    en_dict['code'] = en_dict['code'].str.replace('NDC_CODE:', '')
    en_dict['code9'] = en_dict['code'].apply(lambda x: to9(x))
    mrg = unique_drug.merge(en_dict, on='code9', how='left')
    set_df = mrg[mrg['code_y'].notnull()]
    set_df.loc[:, 'code_y'] = 'NDC_CODE:' + set_df['code_y']
    set_df.sort_values('code_y', inplace=True)
    set_df.loc[:, 'set'] = 'SET'
    write_tsv(set_df[['set', 'code_y', 'code_x']], dict_path, set_file, mode='w')
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))

    #Copy ATC NDC mapping
    onto_files = [os.path.join(onto_folder, 'NDC', 'dicts', 'dict.atc_ndc_set'),
                  os.path.join(onto_folder, 'ATC', 'dicts', 'dict.atc_defs'),
                  os.path.join(onto_folder, 'ATC', 'dicts', 'dict.atc_sets')]
    for ont in onto_files:
        copy(ont, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(ont)))


if __name__ == '__main__':
    #gender_dict()
    #state_dict()
    diag_dicts()
    #drug_dicts()
