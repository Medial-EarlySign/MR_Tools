
import pandas as pd
import os
from shutil import copy
#MR_ROOT = '/opt/medial/tools/bin/'
#sys.path.append(os.path.join(MR_ROOT, 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces
from drugs_to_load import build_drug_map
from create_dicts import ndc11_ndc9, code_desc_to_dict_df
from NDC_to_ATC import get_atc_ndc_map
from stage_to_load_files import build_diag_map


def get_kp_drugs():
    dict_df = build_drug_map().reset_index()
    dict_df.rename(columns={'drug_name': 'desc', 'drugid': 'code'}, inplace=True)
    kp_drugs_df = dict_df[dict_df['code'].str.startswith('KP:')].copy()
    return kp_drugs_df


def get_missing_ndcs(cfg):
    onto_folder = fixOS(cfg.ontology_folder)
    dict_df = build_drug_map().reset_index()
    dict_df.rename(columns={'drug_name': 'desc', 'drugid': 'code'}, inplace=True)
    dict_df['desc'] = replace_spaces(dict_df['desc'].str.upper())
    #dict_df = dict_df[~dict_df['desc'].astype(str).str.contains('WALMART')]
    dict_df.drop_duplicates(inplace=True)

    #dict_df['len'] = dict_df['desc'].str.len()
    #dict_df.sort_values(by=['code', 'len'], inplace=True, na_position='first')
    #dict_df.drop_duplicates('code', keep='last', inplace=True)
    kp_ncd_dict_df = dict_df[dict_df['code'].str.startswith('KP_NDC:')].copy()
    kp_ncd_dict_df['NDC9'] = kp_ncd_dict_df['code'].str.replace('KP_NDC:', '')
    kp_ncd_dict_df['NDC9'] = kp_ncd_dict_df['NDC9'].apply(lambda x: 'NDC_CODE:'+ndc11_ndc9(x))

    ndc_dict_file = os.path.join(onto_folder, 'NDC', 'dicts', 'dict.ndc_defs')
    ndc_dict_full = pd.read_csv(ndc_dict_file, sep='\t', skiprows=1, names=['def', 'defid', 'code'])
    ndc_df = ndc_dict_full[ndc_dict_full['code'].str.contains('NDC_CODE:')].copy()

    mrg1 = kp_ncd_dict_df.merge(ndc_df, how='left', left_on='NDC9', right_on='code')
    return mrg1[mrg1['defid'].isnull()][['desc', 'NDC9']].copy()


if __name__ == '__main__':
    signal = 'Drug'
    first_line = 'SECTION\t' + signal + '\n'
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    onto_folder = fixOS(cfg.ontology_folder)
    dict_path = os.path.join(work_folder, 'rep_configs', 'dicts')

    # Build basic dict from source values
    dc_start = 10000
    dict_file = 'dict.Drug'

    dict_df = build_drug_map().reset_index()
    dict_df.rename(columns={'drug_name': 'desc', 'drugid': 'code'}, inplace=True)
    #dict_df['desc'] = replace_spaces(dict_df['desc'].str.upper())
    #dict_df.drop_duplicates(inplace=True)

    dict_df['len'] = dict_df['desc'].str.len()
    dict_df.sort_values(by=['code', 'len'], inplace=True, na_position='first')
    dict_df.drop_duplicates('code', keep='last', inplace=True)

    final_dict_df = code_desc_to_dict_df(dict_df, dc_start, ['code', 'desc'])
    write_tsv(final_dict_df[['def', 'defid', 'code']], dict_path, dict_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    # Add NDC9 columns
    kp_ncd_dict_df = dict_df[dict_df['code'].str.startswith('KP_NDC:')].copy()
    kp_ncd_dict_df['NDC9'] = kp_ncd_dict_df['code'].str.replace('KP_NDC:', '')
    kp_ncd_dict_df['NDC9'] = kp_ncd_dict_df['NDC9'].apply(lambda x: ndc11_ndc9(x))

    # Copy generic dicts
    to_copy = [os.path.join(onto_folder, 'ATC', 'dicts', 'dict.atc_defs'),
               os.path.join(onto_folder, 'ATC', 'dicts', 'dict.atc_sets'),
               os.path.join(onto_folder, 'NDC', 'dicts', 'dict.atc_ndc_set'),
               os.path.join(onto_folder, 'NDC', 'dicts', 'dict.ndc_defs')]
    for fl in to_copy:
        copy(fl, dict_path)
        add_fisrt_line(first_line, os.path.join(dict_path, os.path.basename(fl)))


    # Add NDCs with description found in KP and not in the FDA product.txt file
    missing_ndcs = get_missing_ndcs(cfg)
    # in some common cases the get_missing_ndcs peeks the wrong option, fixing...
    missing_ndcs.loc[missing_ndcs['NDC9'] == 'NDC_CODE:49999-908', 'desc'] = 'ALBUTEROL'
    missing_ndcs.loc[missing_ndcs['NDC9'] == 'NDC_CODE:10939-081', 'desc'] = 'FAMOTIDINE'
    missing_ndcs.loc[missing_ndcs['NDC9'] == 'NDC_CODE:10939-156', 'desc'] = 'CETIRIZINE'
    missing_ndcs.loc[missing_ndcs['NDC9'] == 'NDC_CODE:54569-5605', 'desc'] = 'INSULINS'
    missing_ndcs.loc[missing_ndcs['NDC9'] == 'NDC_CODE:54569-2318', 'desc'] = 'INSULINS'
    missing_ndcs['desc'] = missing_ndcs['desc'].str.replace('FLU_VACCINE', 'INFLUENZA VACCINES')


    to_def_dict = missing_ndcs.drop_duplicates('NDC9')
    to_def_dict['desc'] = to_def_dict['NDC9'].str.replace('NDC_CODE:', '') + ':' + to_def_dict['desc']
    dc_start = 450000
    miss_dict = code_desc_to_dict_df(to_def_dict, dc_start, ['NDC9', 'desc'])
    write_tsv(miss_dict[['def', 'defid', 'code']], dict_path,  'dict.ndc_defs', mode='a')

    # Read extended (with values found only in KP) NDC dict
    ndc_dict_file = os.path.join(dict_path, 'dict.ndc_defs')
    ndc_dict_full = pd.read_csv(ndc_dict_file, sep='\t', names=['def', 'defid', 'NDC9_full'], skiprows=1)
    ndc_dict_df = ndc_dict_full[ndc_dict_full['NDC9_full'].str.contains('NDC_CODE')].copy()
    ndc_dict_df['NDC9'] = ndc_dict_df['NDC9_full'].str.replace('NDC_CODE:', '')
    # Add set for extended NDCs
    mrg = kp_ncd_dict_df.merge(ndc_dict_df, on='NDC9', how='left')
    set_dict = mrg[mrg['defid'].notnull()][['NDC9_full', 'code']].copy()

    set_file = 'dict.Drug_set'
    set_dict['set'] = 'SET'
    write_tsv(set_dict[['set', 'NDC9_full', 'code']], dict_path, set_file, mode='w')
    first_line = 'SECTION\t' + signal + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))


    # Try to map to ATC (same as NDC to ATC mapping is done)
    missing_ndcs['SUBSTANCENAME'] = missing_ndcs['desc'].str.replace('_', ';').astype(str)
    missing_ndcs.rename(columns={'NDC9': 'PRODUCTNDC'}, inplace=True)

    #to_set_dict = missing_ndcs.copy()
    kp_ndc_set = get_atc_ndc_map(missing_ndcs[['PRODUCTNDC', 'SUBSTANCENAME']], onto_folder)
    set_file = 'dict.atc_ndc_set'
    kp_ndc_set['set'] = 'SET'
    kp_ndc_set.drop_duplicates(['set', 'atc', 'PRODUCTNDC'], inplace=True)
    write_tsv(kp_ndc_set[['set', 'atc', 'PRODUCTNDC']], dict_path, set_file, mode='a')

    # Try to map drugs with no NDC to ATC
    kp_drugs = get_kp_drugs()
    kp_drugs['desc'] = kp_drugs['desc'].str.replace('FLU_VACCINE', 'INFLUENZA VACCINES')
    kp_drugs['SUBSTANCENAME'] = kp_drugs['desc'].str.replace('_', ';').astype(str)
    kp_drugs.rename(columns={'code': 'PRODUCTNDC'}, inplace=True)
    kp_atc_set = get_atc_ndc_map(kp_drugs[['PRODUCTNDC', 'SUBSTANCENAME']], onto_folder)
    kp_atc_set['set'] = 'SET'
    write_tsv(kp_atc_set[['set', 'atc', 'PRODUCTNDC']], dict_path, set_file, mode='a')
