import os
import pandas as pd
from utils import replace_spaces, write_tsv, code_desc_to_dict_df

onto_path ='..\\Ontologies\\'
ccs_maps_path = onto_path+'CCS'
out_path = ccs_maps_path+'\\dicts'

def read_icd_dict(icd_dict_file):
    icd_dict_df = pd.read_csv(icd_dict_file, sep='\t', skiprows=1, names=['def', 'defid', 'code'])
    icds = icd_dict_df[icd_dict_df['code'].str.contains('ICD9_CODE:')]['code']
    return icds


def ccs_dict(ccs_map_file, icds, out_folder, dict_file_name, ind):
    ccs_map_df = pd.read_csv(ccs_map_file, dtype=str)
    ccs_map_df['ccsdesc'] = 'CCS_DESC:' + ccs_map_df['ccs'].astype(str) + ':' + replace_spaces(ccs_map_df['ccsdesc'])
    ccs_map_df['ccs'] = 'CCS_CODE:' + ccs_map_df['ccs'].astype(str)
    ccs_map_df['icd'] = 'ICD9_CODE:' + ccs_map_df['icd']
    legal_set_df = ccs_map_df[ccs_map_df['icd'].isin(icds)]
    legal_set_df.loc[:, 'set'] = 'SET'
    ccs_defs = ccs_map_df.drop_duplicates(['ccs', 'ccsdesc'])[['ccs', 'ccsdesc']].copy()
    ccs_def_dict = code_desc_to_dict_df(ccs_defs, ind, ['ccs', 'ccsdesc'])
    write_tsv(ccs_def_dict[['def', 'defid', 'code']], out_folder, dict_file_name, mode='w')
    write_tsv(legal_set_df[['set', 'ccs', 'icd']], out_folder, dict_file_name, mode='a')


if __name__ == '__main__':
    icd9_dict_file = 'dict.icd9dx'
    icd9_dict_file = os.path.join(onto_path, 'ICD9', 'dicts', icd9_dict_file)
    legal_icd9 = read_icd_dict(icd9_dict_file)

    ccs_diag_set_file = 'dict.ccs_diag_sets'
    ccs_ind = 960000
    diag_map_file = os.path.join(ccs_maps_path, 'dxicd2ccsxw.csv')
    ccs_dict(diag_map_file, legal_icd9, out_path, ccs_diag_set_file, ccs_ind)

    ccs_diag_set_file = 'dict.ccs_proc_sets'
    ccs_ind = 970000
    diag_map_file = os.path.join(ccs_maps_path, 'pricd2ccsxw.csv')
    ccs_dict(diag_map_file, legal_icd9, out_path, ccs_diag_set_file, ccs_ind)







    print(ccs_maps_path)
