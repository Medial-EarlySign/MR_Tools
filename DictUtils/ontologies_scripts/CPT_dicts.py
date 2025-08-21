import pandas as pd
from utils import replace_spaces, code_desc_to_dict_df, write_tsv
import os
ONTO_NAME = 'CPT'
cpt_file = '..\\Ontologies\\' + ONTO_NAME + '\\CPT codes.txt'
cpt_add_file = '..\\Ontologies\\' + ONTO_NAME + '\\cpt_add.txt'
dict_path = '..\\Ontologies\\' + ONTO_NAME + '\\dicts'

if __name__ == '__main__':
    dcstart = 700000
    dict_file = 'dict.cpt'
    cpt_df = pd.read_csv(cpt_file, sep='\t', usecols=[0, 1], dtype={'CPT_CODE': str})
    cpt_add_df = pd.read_csv(cpt_add_file, sep='\t')
    cpt_add_df['CPT_DESCR'] = cpt_add_df['CPT_DESCR'].str.replace(' No Precert Req', '')
    cpt_df = cpt_df.append(cpt_add_df)
    cpt_df.drop_duplicates(subset='CPT_CODE', keep='first', inplace=True)
    cpt_df['CPT_CODE'] = 'CPT_CODE:' + cpt_df['CPT_CODE'].str.strip()
    cpt_df['CPT_DESCR'] = replace_spaces(cpt_df['CPT_DESCR'])
    cpt_df['dup'] = cpt_df.groupby('CPT_DESCR').cumcount()
    cpt_df['CPT_DESCR'] = cpt_df['CPT_DESCR'].where(cpt_df['dup'] == 0, cpt_df['CPT_DESCR'] + '_' + cpt_df['dup'].astype(str))
    cpt_dict = code_desc_to_dict_df(cpt_df, dcstart, ['CPT_CODE', 'CPT_DESCR'])
    write_tsv(cpt_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')





