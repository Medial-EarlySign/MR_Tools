import pandas as pd
from dict_from_bioportal import build_def_dict, build_set_dict
from utils import replace_spaces

ONTO_NAME = 'ICD10'

ICD10_codes_csv = '..\\Ontologies\\' + ONTO_NAME + '\\icd10cm_order_2017.csv'
ICD10_codes_csv19 = '..\\Ontologies\\' + ONTO_NAME + '\\icd10cm_order_2019.txt'
ICD10_codes_csv_more = '..\\Ontologies\\' + ONTO_NAME + '\\ICD_from_DMWB.csv'
ICD10_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.icd10'
ICD10_set_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_icd10'

ICD10_pcs_codes_csv19 = '..\\Ontologies\\' + ONTO_NAME + '\\icd10pcs_codes_2019.txt'
ICD10_pcs_codes_bioprtal = '..\\Ontologies\\' + ONTO_NAME + '\\ICD10PCS.csv'
ICD10_pcs_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.icd10pcs'
ICD10_pcs_set_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_icd10pcs'

icd10_med_index_start = 1000000

code_ranges = {
        'A00-B99': 'Certain infectious and parasitic diseases',
        'C00-D48': 'Neoplasms',
        'D50-D89': 'Diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism',
        'E00-E90': 'Endocrine, nutritional and metabolic diseases',
        'F00-F99': 'Mental and behavioural disorders',
        'G00-G99': 'Diseases of the nervous system',
        'H00-H59': 'Diseases of the eye and adnexa',
        'H60-H95': 'Diseases of the ear and mastoid process',
        'I00-I99': 'Diseases of the circulatory system',
        'J00-J99': 'Diseases of the respiratory system',
        'K00-K93': 'Diseases of the digestive system',
        'L00-L99': 'Diseases of the skin and subcutaneous tissue',
        'M00-M99': 'Diseases of the musculoskeletal system and connective tissue',
        'N00-N99': 'Diseases of the genitourinary system',
        'O00-O99': 'Pregnancy, childbirth and the puerperium',
        'P00-P96': 'Certain conditions originating in the perinatal period',
        'Q00-Q99': 'Congenital malformations, deformations and chromosomal abnormalities',
        'R00-R99': 'Symptoms, signs and abnormal clinical and laboratory findings, not elsewhere classified',
        'S00-T98': 'Injury, poisoning and certain other consequences of external causes',
        'V01-Y98': 'External causes of morbidity and mortality',
        'Z00-Z99': 'Factors influencing health status and contact with health services',
        'U00-U99': 'Codes for special purposes'}


def add_range_level(last_index):
    range_dict = pd.DataFrame(columns = ['type', 'mediald', 'desc'])
    for key, value in code_ranges.items():
        last_index = last_index + 1
        dict1 = {'type': 'DEF', 'mediald': last_index, 'desc': 'ICD10_CODE:' + key}
        range_dict = range_dict.append(dict1, ignore_index=True)
        dict1 = {'type': 'DEF', 'mediald': last_index, 'desc': 'ICD10_CODE:' + key + ':' + value}
        range_dict = range_dict.append(dict1, ignore_index=True)
    range_dict['desc'] = replace_spaces(range_dict['desc'])
    return range_dict


def code_cms_df(csv_file):
    bp_df = pd.read_fwf(csv_file, colspecs=[(6, 13), (14, 15), (16, 76)], names=['code', 'leaf', 'desc'])
    return bp_df[['code', 'desc', 'leaf']]


def code_pcs_cms_df(csv_file):
    bp_df = pd.read_fwf(csv_file, colspecs=[(0, 8), (9, 200)], names=['code', 'desc'])
    return bp_df[['code', 'desc']]


def build_code_parent_df(orig_df):
    codes = orig_df['code'].values
    parent_df = orig_df.copy()
    parent_df['parent'] = orig_df['code'].map(lambda x: x[:-1])
    parent_df = parent_df[parent_df['parent'].isin(codes)]
    return parent_df[['code', 'parent']]


def add_range_sets(orig_df):
    high_level_codes = orig_df[orig_df['code'].str.len() == 3]['code'].values
    range_set = pd.DataFrame(columns=['code', 'parent'])
    for key, value in code_ranges.items():
        range1 = key.split('-')
        low_code = range1[0]
        high_code = range1[1]
        for cd in high_level_codes:
            if cd >= low_code and cd <= high_code:
                range_set = range_set.append({'code': cd, 'parent': key}, ignore_index=True)

    # for hlc in high_level_codes:
    #     if hlc not in range_set['code'].values:
    #         print(' code ' + hlc + " not in amy range")
    return range_set


if __name__ == '__main__':
    #  Build the icd10 DEF dict
    icd10_df17 = code_cms_df(ICD10_codes_csv)
    icd10_df19 = code_cms_df(ICD10_codes_csv19)
    icd_df_more = pd.read_csv(ICD10_codes_csv_more, names=['code', 'desc'])

    codes19 = icd10_df19['code'].values
    onlyin17 = icd10_df17[~icd10_df17['code'].isin(codes19)]

    icd10_df = pd.concat([icd10_df19, onlyin17, icd_df_more], sort=True)
    icd10_df.drop_duplicates(subset='code', keep='first', inplace=True)
    icd10_dict = build_def_dict('ICD10', icd10_df, 'code', 'desc', icd10_med_index_start)
    last_index = icd10_dict['mediald'].max()
    rng_dict = add_range_level(last_index)
    icd10_dict = icd10_dict.append(rng_dict, ignore_index=True)
    icd10_dict.to_csv(ICD10_dict_file, sep='\t', index=False, header=False)

    #  Build the icd10 SET dict
    code_parent_df = build_code_parent_df(icd10_df)
    code_parent_range = add_range_sets(icd10_df)
    code_parent_df = code_parent_df.append(code_parent_range, ignore_index=True)
    sets2_df = build_set_dict(icd10_dict, code_parent_df)
    sets2_df[['typ', 'outer_desc', 'inner_desc']].to_csv(ICD10_set_dict_file, sep='\t', index=False, header=False, encoding='ascii')

    #  Build the icd10 PCS DEF dict
    #icd10_pcs_df19 = code_pcs_cms_df(ICD10_pcs_codes_csv19)
    icd10_pcs_df19 = pd.read_csv(ICD10_pcs_codes_bioprtal)
    icd10_pcs_df19['code'] = icd10_pcs_df19['Class ID'].apply(lambda x: x.split('/')[-1])
    icd10_pcs_dict = build_def_dict('ICD10', icd10_pcs_df19, 'code', 'Preferred Label', last_index+1000)
    icd10_pcs_dict.to_csv(ICD10_pcs_dict_file, sep='\t', index=False, header=False)

    code_parent_df = build_code_parent_df(icd10_pcs_df19)
    code_parent_df['code'] = 'ICD10_CODE:' + code_parent_df['code']
    code_parent_df['parent'] = 'ICD10_CODE:' + code_parent_df['parent']
    code_parent_df['typ'] = 'SET'
    #code_parent_range = add_range_sets(icd10_pcs_df19)
    #code_parent_df = code_parent_df.append(code_parent_range, ignore_index=True)
    #sets2_df = build_set_dict(icd10_pcs_dict, code_parent_df)
    code_parent_df[['typ', 'parent', 'code']].to_csv(ICD10_pcs_set_dict_file, sep='\t', index=False, header=False, encoding='ascii')