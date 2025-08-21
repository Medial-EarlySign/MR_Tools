import pandas as pd

ONTO_NAME = 'ICD9'

ICD9dx_codes_json = '..\\' + ONTO_NAME + '\\codes.json'


ICD9dx_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.icd9dx'
ICD9dx_set_dict = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_icd9dx'


icd9_med_index_start = 900000


def code_json_to_df(json_file):
    icd9_json_df = pd.read_json(json_file)
    depth1 = icd9_json_df[0].apply(pd.Series).drop_duplicates()
    depth2 = icd9_json_df[1].apply(pd.Series).drop_duplicates()
    depth3 = icd9_json_df[2].apply(pd.Series).drop_duplicates()
    depth4 = icd9_json_df[3].apply(pd.Series).drop_duplicates()
    depth5 = icd9_json_df[4].apply(pd.Series).drop_duplicates()
    icd9_df = pd.concat([depth1, depth2, depth3, depth4, depth5])

    return icd9_df


def code_json_to_hier(json_file):
    icd9_json_ser = pd.read_json(json_file, typ='series')
    icd9_json_hier_list = icd9_json_ser.apply(lambda x: [c['code'] for c in x])
    icd9_json_hier = pd.DataFrame()
    icd9_json_hier = icd9_json_hier.from_records(icd9_json_hier_list.apply(lambda x: {'code': x[-1], 'hier': x[:-1]}))
    return icd9_json_hier


def build_icd9_def_dict(icd9_df, code_field, desc_field):
    icd9dx_df['mediald'] = icd9dx_df.index + icd9_med_index_start
    icd9_df['pref'] = 'DIAG_ICD9_CODE:'
    #if 'href' in icd9_df.columns:
    #    icd9_df['pref'].where(icd9_df['href'].isnull(), 'DIAG_ICD9_GROUP:', inplace=True)
    icd9_df['DIAG_CODE'] = icd9_df['pref'] + icd9_df[code_field]
    icd9_df['DIAG_DESC'] = 'DIAG_ICD9_DESC:' + icd9_df[code_field] + ':' + icd9_df[desc_field]

    to_stack = icd9_df[['mediald', 'DIAG_CODE', 'DIAG_DESC']].set_index('mediald', drop=True)

    icd9_dict = to_stack.stack().to_frame()
    icd9_dict['mediald'] = icd9_dict.index.get_level_values(0)
    icd9_dict['type'] = 'DEF'
    icd9_dict.rename({0: 'desc'}, axis=1, inplace=True)
    icd9_dict.drop_duplicates(inplace=True)
    return icd9_dict[['type', 'mediald', 'desc']]


def build_icd9_set_dict(icd9def_dict):
    icd9def_dict['list'] = icd9dx_dict['desc'].str.split(':')
    icd9def_dict['code'] = icd9dx_dict.apply(lambda row: row['list'][1], axis=1)
    icd9_hier = code_json_to_hier(ICD9dx_codes_json)

    # hierchay list to SET couples
    sets_df = pd.DataFrame()
    for _, lf in icd9_hier.iterrows():
        if lf['code'] not in lf['hier']:
            lf['hier'].append(lf['code'])
        for i in range(len(lf['hier']) - 1, 0, -1):
            sets_df = sets_df.append({'outer': lf['hier'][i - 1], 'inner': lf['hier'][i]}, ignore_index=True)
    print(sets_df)

    # build dict to replace codes with DESC
    code_name_map = icd9def_dict[['code', 'desc']].copy()
    code_name_map['desc_len'] = code_name_map['desc'].str.len()
    code_name_map.sort_values(['code', 'desc_len'], inplace=True)
    code_name_map.drop_duplicates('code', inplace=True)
    code_name_map = code_name_map[['code', 'desc']].set_index('code', drop=True)['desc']

    sets_df['set'] = 'SET'
    sets_df['outer_desc'] = sets_df['outer'].map(code_name_map)
    sets_df['inner_desc'] = sets_df['inner'].map(code_name_map)
    sets_df.drop_duplicates(['set', 'outer_desc', 'inner_desc'], inplace=True)
    sets_df.dropna(subset=['set', 'outer_desc', 'inner_desc'], inplace=True)

    # For each inner create line with no '.'
    sets_df_no_dot = pd.DataFrame()
    sets_df_no_dot['set'] = 'SET'
    sets_df_no_dot['outer_desc'] = sets_df['inner_desc'].where(
        sets_df['inner_desc'].str.contains('.', regex=False)).dropna()
    sets_df_no_dot['inner_desc'] = sets_df_no_dot['outer_desc'].str.replace('.', '')
    sets_df_no_dot.drop_duplicates(['set', 'outer_desc', 'inner_desc'], inplace=True)
    sets_df = sets_df.append(sets_df_no_dot)
    sets_df = sets_df[sets_df['inner_desc'] != sets_df['outer_desc']]
    return sets_df


if __name__ == '__main__':
    #  Build the icd9 DEF dict
    icd9dx_df = code_json_to_df(ICD9dx_codes_json)
    icd9dx_dict = build_icd9_def_dict(icd9dx_df, 'code', 'descr')
    icd9dx_dict.to_csv(ICD9dx_dict, sep='\t', index=False, header=False)

    #  Build the icd9 SET dict

    sets2_df = build_icd9_set_dict(icd9dx_dict)
    sets2_df[['set', 'outer_desc', 'inner_desc']].to_csv(ICD9dx_set_dict, sep='\t', index=False, header=False)
