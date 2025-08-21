import pandas as pd
from utils import replace_spaces, code_desc_to_dict_df, write_tsv
import os
ONTO_NAME = 'HCPCS'
hcpc_file = '..\\Ontologies\\' + ONTO_NAME + '\\HCPC2018 simplied.txt'
hcpc_file2011 = '..\\Ontologies\\' + ONTO_NAME + '\\2011_HCPCS_codes.txt'
dict_path = '..\\Ontologies\\' + ONTO_NAME + '\\dicts'

if __name__ == '__main__':
    dcstart = 800000
    dict_file = 'dict.hcpcs'
    hc_df = pd.read_csv(hcpc_file, sep='\t', skiprows=4)
    hc_df['LONG DESCRIPTION'] = hc_df['HCPC'].str.strip() + ':' + replace_spaces(hc_df['LONG DESCRIPTION'])
    hc_df['HCPC'] = 'HCPCS_CODE:' + hc_df['HCPC'].str.strip()
    hc_dict = code_desc_to_dict_df(hc_df, dcstart, ['HCPC', 'LONG DESCRIPTION'])
    write_tsv(hc_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')

    dcstart = 600000
    dict_file = 'dict.hcpcs_2011'
    hc_df = pd.read_csv(hcpc_file2011,sep='\t', usecols=[0, 3])
    hc_df.drop_duplicates(subset=['HCPC'], inplace=True)
    hc_df['HCPC'] = hc_df['HCPC'].where(hc_df['HCPC'].str.strip().str.len() == 2, 'HCPCS_CODE:' + hc_df['HCPC'].str.strip())
    hc_df['HCPC'] = hc_df['HCPC'].where(hc_df['HCPC'].str.strip().str.len() != 2, 'MODIFIER:'+hc_df['HCPC'].str.strip())
    hc_df['Long Description'] = replace_spaces(hc_df['Long Description'])
    hc_df['dup'] = hc_df.groupby('Long Description').cumcount()
    hc_df['Long Description'] = hc_df['Long Description'].where(hc_df['dup'] == 0,  hc_df['Long Description']+'_'+hc_df['dup'].astype(str))
    hc_dict = code_desc_to_dict_df(hc_df, dcstart, ['HCPC', 'Long Description'])
    write_tsv(hc_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')