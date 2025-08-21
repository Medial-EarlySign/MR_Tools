import pandas as pd
from dict_from_bioportal import code_bioportal_df

FROM_ONT_NAME = 'ICD9'
TO_ONT_NAME = 'ICD10'
DEST = 'ICD9_TO_ICD10'

ICD10_codes_csv = '..\\Ontologies\\' + TO_ONT_NAME + '\\icd10cm_order_2017.csv'
ICD10_codes_csv_more = '..\\Ontologies\\' + TO_ONT_NAME + '\\ICD_from_DMWB.csv'
ICD10_dict_file = '..\\Ontologies\\' + DEST + '\\dicts\\dict.set_icd9_2_icd10'

ICD9all_codes_csv = '..\\Ontologies\\' + FROM_ONT_NAME + '\\ICD9CM.csv'

mapping_file = '..\\Ontologies\\' + DEST + '\\icd9toicd10gem.csv'


def replace_spaces(val_ser):
    return val_ser.str.replace(' ', '_').str.replace(',', '_')


if __name__ == '__main__':
    #  Build the icd9 DEF dict
    icd10_df = pd.read_fwf(ICD10_codes_csv, colspecs=[(6, 13), (14, 15), (16, 76)], names=['code', 'leaf', 'desc'])
    icd_df_more = pd.read_csv(ICD10_codes_csv_more, names=['code', 'desc'])
    icd10_df = pd.concat([icd10_df, icd_df_more], sort=True)
    icd10_df.drop_duplicates(subset='code', keep='first', inplace=True)

    icd9_df = code_bioportal_df(ICD9all_codes_csv)
    icd9_df['clean_code'] = icd9_df['code'].str.replace('.', '')

    mapping_df = pd.read_csv(mapping_file, dtype={'icd9cm': str})

    mapped_df = icd9_df.merge(mapping_df[['icd10cm', 'icd9cm']], how='left', left_on='clean_code', right_on='icd9cm')
    mapped_df = mapped_df.merge(icd10_df[['code', 'desc']], how='left', left_on='icd10cm', right_on='code')
    mapped_df = mapped_df[mapped_df['code_y'].notnull()]
    mapped_df['icd10'] = 'ICD10_CODE:' + mapped_df['code_y']
    mapped_df['icd9'] = 'ICD9_CODE:' + mapped_df['clean_code']
    mapped_df['set'] = 'SET'
    mapped_df[['set', 'icd10', 'icd9']].to_csv(ICD10_dict_file, sep='\t', header=False, index=False)
    print(mapped_df)