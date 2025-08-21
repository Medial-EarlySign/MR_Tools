import pandas as pd


icd10_dict = '..\\Ontologies\\ICD10\\dicts\\dict.icd10'
icd9_dict = '..\\Ontologies\\ICD9\\dicts\\dict.icd9dx'


def replace_spaces(val_ser):
    return val_ser.str.replace(' ', '_').str.replace(',', '_')


def merge_with_map(icd9_df, icd10_df, mapping_df):
    mapped_df = mapping_df[['icd10cm', 'icd9cm']].merge(icd9_df[['desc9', 'code9']],
                                                        how='left', left_on='icd9cm', right_on='code9')
    mapped_df = mapped_df.merge(icd10_df[['desc10', 'code10']],
                                how='left', left_on='icd10cm', right_on='code10')
    mapped_df = mapped_df[(mapped_df['code9'].notnull()) & (mapped_df['code10'].notnull())]
    mapped_df.drop_duplicates(['icd10cm', 'icd9cm'], inplace=True)
    return mapped_df


def to_map_dict(icd9_df, icd10_df, map_df, desc_dict):
    mapped_df = merge_with_map(icd9_df, icd10_df, map_df)
    mapped_df['set'] = 'SET'
    if 'icd10_2_icd9' in desc_dict:
        mapped_df[['set', 'desc10', 'desc9']].to_csv(desc_dict, sep='\t', header=False, index=False)
    else:
        mapped_df[['set', 'desc9', 'desc10']].to_csv(desc_dict, sep='\t', header=False, index=False)


def add_bidierctional_mapping(m9to10, ma10to9):
    m1 = m9to10.merge(ma10to9, how='right', on='icd9cm')
    add_9 = m1[m1['icd10cm_x'].isnull()].copy()
    add_9.rename(columns={'icd10cm_x': 'icd10cm'}, inplace=True)
    big9 = m9to10.append(add_9, sort=True)

    m2 = m9to10.merge(ma10to9, how='left', on='icd10cm')
    add_10 = m2[m2['icd9cm_y'].isnull()].copy()
    add_10.rename(columns={'icd9cm_y': 'icd9cm'}, inplace=True)
    big10 = ma10to9.append(add_10, sort=True)
    return big9, big10


if __name__ == '__main__':
    map_file9to10 = '..\\Ontologies\\ICD9_TO_ICD10\\icd9toicd10gem.csv'
    map_file10to9 = '..\\Ontologies\\ICD10_TO_ICD9\\icd10toicd9gem.csv'
    m9to10 = pd.read_csv(map_file9to10, dtype={'icd9cm': str}, usecols=['icd10cm', 'icd9cm'])
    ma10to9 = pd.read_csv(map_file10to9, dtype={'icd9cm': str}, usecols=['icd10cm', 'icd9cm'])

    #m9to10, ma10to9 = add_bidierctional_mapping(m9to10, ma10to9)

    df10 = pd.read_csv(icd10_dict, sep='\t', names=['def', 'defid', 'desc10'])
    df10 = pd.concat([df10, df10['desc10'].str.split(':', expand=True)], axis=1)
    df10.rename(columns={1: 'code10'}, inplace=True)

    df9 = pd.read_csv(icd9_dict, sep='\t', names=['def', 'defid', 'desc9'])
    df9 = pd.concat([df9, df9['desc9'].str.split(':', expand=True)], axis=1)
    df9.rename(columns={1: 'code9'}, inplace=True)

    dest_dict9to10 = '..\\Ontologies\\ICD9_TO_ICD10\\dicts\\dict.set_icd9_2_icd10'
    to_map_dict(df9, df10, ma10to9, dest_dict9to10)

    dest_dict10to9 = '..\\Ontologies\\ICD10_TO_ICD9\\dicts\\dict.set_icd10_2_icd9'
    to_map_dict(df9, df10, m9to10, dest_dict10to9)
