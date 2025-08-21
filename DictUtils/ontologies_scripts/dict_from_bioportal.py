import pandas as pd


def add_fisrt_line(first_line, file):
    with open(file, "r+", encoding="utf8") as f:
        a = f.read()
        a = a.replace('\r\n', '\n')
    with open(file, "w+", encoding="utf8") as f:
        f.write(first_line + a)


def get_code_decs_map(def_df):
    def_df['list'] = def_df['desc'].str.split(':')
    def_df['code'] = def_df.apply(lambda row: row['list'][1], axis=1)
    code_name_map = def_df[['code', 'desc']].copy()
    code_name_map['desc_len'] = code_name_map['desc'].str.len()
    code_name_map.sort_values(['code', 'desc_len'], ascending=[True, True], inplace=True)
    code_name_map.drop_duplicates('code', inplace=True)
    code_name_map = code_name_map[['code', 'desc']].set_index('code', drop=True)['desc']
    return code_name_map


def code_bioportal_df(csv_file):
    bp_df = pd.read_csv(csv_file)
    bp_df = bp_df[bp_df['Parents'].notnull()]
    bp_df['uri_list'] = bp_df['Class ID'].str.split('/')
    bp_df['code'] = bp_df.apply(lambda row: row['uri_list'][-1], axis=1)
    bp_df['uri_list'] = bp_df['Parents'].str.split('/')
    bp_df['parent'] = bp_df.apply(lambda row: row['uri_list'][-1], axis=1)

    return bp_df[['code', 'Preferred Label', 'parent']]


def build_def_dict(prefix, bp_df, code_field, desc_field, medial_start_ind):
    bp_df = bp_df.assign(mediald=range(medial_start_ind, medial_start_ind + bp_df.shape[0]))
    bp_df[code_field] = bp_df[code_field].str.strip().str.replace(' ', '_')
    bp_df['CODE'] = prefix + '_CODE:' + bp_df[code_field].str.strip()
    if desc_field:
        bp_df[desc_field] = bp_df[desc_field].str.strip().str.replace(' ', '_')
        bp_df[desc_field] = bp_df[desc_field].str.strip().str.replace(',', '')
        bp_df['DESC'] = prefix + '_DESC:' + bp_df[code_field].str.strip() + ':' + bp_df[desc_field].str.strip()

        to_stack = bp_df[['mediald', 'CODE', 'DESC']].set_index('mediald', drop=True)
        icd9_dict = to_stack.stack().to_frame()
        icd9_dict['mediald'] = icd9_dict.index.get_level_values(0)
        icd9_dict.rename({0: 'desc'}, axis=1, inplace=True)
    else:
        icd9_dict = bp_df[['mediald', 'CODE']]
        icd9_dict.rename({'CODE': 'desc'}, axis=1, inplace=True)
    icd9_dict['type'] = 'DEF'
    icd9_dict.drop_duplicates('desc', inplace=True)
    icd9_dict = icd9_dict[icd9_dict['desc'].notnull()]
    return icd9_dict[['type', 'mediald', 'desc']]


def def_wo_chars(prefix, def_df, char):
    def_df_code = def_df[def_df['desc'].str.contains(prefix + '_CODE:')].copy()
    def_df_code = def_df[def_df['desc'].str.contains(char, regex=False)]
    def_df_code['desc'] = def_df_code['desc'].str.replace(char, '', regex=False)
    return def_df_code


def build_set_dict(def_dict, id_to_parent_df, char_to_remove=None):
    # id, parent cuples list to SET couples
    sets_df = pd.DataFrame(columns=['typ', 'outer', 'inner'])
    sets_df['outer'] = id_to_parent_df['parent']
    sets_df['inner'] = id_to_parent_df['code']

    code_name_map = get_code_decs_map(def_dict)

    sets_df['outer_desc'] = sets_df['outer'].map(code_name_map)
    sets_df['inner_desc'] = sets_df['inner'].map(code_name_map)
    sets_df.drop_duplicates(['outer_desc', 'inner_desc'], inplace=True)
    sets_df.dropna(subset=['outer_desc', 'inner_desc'], inplace=True)

    # For each inner create line with no special char
    if char_to_remove:
        sets_df_no_dot = pd.DataFrame()
        sets_df_no_dot['outer_desc'] = sets_df['inner_desc'].where(
            sets_df['inner_desc'].str.contains(char_to_remove, regex=False)).dropna()
        sets_df_no_dot['inner_desc'] = sets_df_no_dot['outer_desc'].str.replace(char_to_remove, '')
        sets_df_no_dot.drop_duplicates(['outer_desc', 'inner_desc'], inplace=True)
        sets_df = sets_df.append(sets_df_no_dot)
    sets_df = sets_df[sets_df['inner_desc'] != sets_df['outer_desc']]
    sets_df['typ'] = 'SET'
    return sets_df[['typ', 'outer_desc', 'inner_desc']]
