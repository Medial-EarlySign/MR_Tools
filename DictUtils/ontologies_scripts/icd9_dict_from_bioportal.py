import pandas as pd
from dict_from_bioportal import code_bioportal_df, build_def_dict, build_set_dict, def_wo_chars


ONTO_NAME = 'ICD9'

ICD9all_codes_csv = '..\\Ontologies\\' + ONTO_NAME + '\\ICD9CM.csv'
ICD9_procedure_codes = '..\\Ontologies\\' + ONTO_NAME + '\\icd9sg2015.csv'
ICD9dx_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.icd9dx'
ICD9sg_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.icd9sg'
ICD9dx_set_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_icd9dx'
ICD9sg_set_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_icd9sg'

icd9_med_index_start = 900000


def split_dx_sg(def_dict, id_to_parent_df):
    ret_cols = def_dict.columns
    sg_code_list = pd.read_csv(ICD9_procedure_codes, converters={'prcdrcd': str})['prcdrcd']
    sg_code_list = sg_code_list.str[0:2] + '.' + sg_code_list.str[2:4]
    parents = id_to_parent_df[id_to_parent_df['code'].isin(sg_code_list.values)]['parent']
    grandp = id_to_parent_df[id_to_parent_df['code'].isin(parents.values)]['parent']
    sg_code_list = sg_code_list.append(parents).append(grandp)
    def_dict['list'] = def_dict['desc'].str.split(':')
    def_dict['code'] = def_dict.apply(lambda row: row['list'][1], axis=1)
    return def_dict[~def_dict['code'].isin(sg_code_list.values)][ret_cols], def_dict[def_dict['code'].isin(sg_code_list.values)][ret_cols]


if __name__ == '__main__':
    #  Build the icd9 DEF dict
    icd9_df = code_bioportal_df(ICD9all_codes_csv)
    icd9_dict = build_def_dict('ICD9', icd9_df, 'code', 'Preferred Label', icd9_med_index_start)

    icd9dx_dict, icd9sg_dict = split_dx_sg(icd9_dict, icd9_df[['code', 'parent']])

    icd9dx_dict_no_char = def_wo_chars('ICD9', icd9dx_dict, '.')
    icd9sg_dict_no_char = def_wo_chars('ICD9', icd9sg_dict, '.')
    icd9dx_dict = pd.concat([icd9dx_dict, icd9dx_dict_no_char]).sort_values(['mediald', 'desc'])
    icd9sg_dict = pd.concat([icd9sg_dict, icd9sg_dict_no_char]).sort_values(['mediald', 'desc'])

    icd9dx_dict.to_csv(ICD9dx_dict, sep='\t', index=False, header=False)
    icd9sg_dict.to_csv(ICD9sg_dict, sep='\t', index=False, header=False)

    #  Build the icd9 SET dict
    #setdx_df = build_set_dict(icd9dx_dict, icd9_df, '.')
    #setsg_df = build_set_dict(icd9sg_dict, icd9_df, '.')
    setdx_df = build_set_dict(icd9dx_dict, icd9_df)
    setsg_df = build_set_dict(icd9sg_dict, icd9_df)
    setdx_df[['typ', 'outer_desc', 'inner_desc']].to_csv(ICD9dx_set_dict, sep='\t', index=False, header=False)
    setsg_df[['typ', 'outer_desc', 'inner_desc']].to_csv(ICD9sg_set_dict, sep='\t', index=False, header=False)
