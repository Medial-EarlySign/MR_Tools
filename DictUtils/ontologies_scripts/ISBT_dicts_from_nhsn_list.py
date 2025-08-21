import os
import pandas as pd
from dict_from_bioportal import code_bioportal_df, build_def_dict, build_set_dict, def_wo_chars


if __name__ == '__main__':
    ONTO_NAME = 'ISBT'
    isbt_codes_csv = '..\\Ontologies\\' + ONTO_NAME + '\\ISBT_codes_description.csv'
    isbt_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.isbt'

    isbt_index_start = 700000
    if os.path.exists(isbt_dict_file):
        os.remove(isbt_dict_file)

    isbt_codes_df = pd.read_csv(isbt_codes_csv, sep='\t')
    isbt_dict = build_def_dict('ISBT', isbt_codes_df, 'ISBT', 'Description', isbt_index_start)
    isbt_dict.to_csv(isbt_dict_file, sep='\t', index=False, header=False)
    set_dict = isbt_codes_df[['prodCDC', 'DESC']].copy()
    set_dict['prodCDC'] = 'ISBT_CDC' + ':' + set_dict['prodCDC']
    set_dict['type'] = 'SET'
    set_dict[['type', 'prodCDC', 'DESC']].to_csv(isbt_dict_file, sep='\t', index=False, header=False, mode='a')
