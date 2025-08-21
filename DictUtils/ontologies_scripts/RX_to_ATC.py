import pandas as pd
from utils import replace_spaces, code_desc_to_dict_df, write_tsv
import os
FROM_ONTO_NAME = 'RX'
TRU_ONTO_NAME = 'NDC'
TO_ONTO_NAME = 'ATC'


def read_rx_ndc_map(map_file):
    rx_ndc_map = pd.read_csv(map_file, sep='\t')
    rx_ndc_map = rx_ndc_map[(rx_ndc_map['ndcs'] != '[]') & (rx_ndc_map['ndcs'] != 'ndcs')]
    rx_ndc_map['ndcs'] = rx_ndc_map['ndcs'].apply(lambda x: x.strip("[]").replace("'", "").split(", "))
    #rx_ndc_map[rx_ndc_map['rxcui'].astype(int).isin(rx_df['RXN_CD'].unique().tolist())]
    map_list = []
    for i, r in rx_ndc_map.iterrows():
        if len(r['ndcs']) > 0:
            for ndc in r['ndcs']:
                map_list.append({'rxcui': r['rxcui'], 'ndc9': ndc[0:9]})

    rx_map = pd.DataFrame(map_list)
    # ndcs = rx_map[['ndc9']].drop_duplicates().copy()
    ndcs = rx_map.drop_duplicates('ndc9').copy()
    ndcs['code_pref'] = ndcs['ndc9'].str[:-4].astype(int).astype(str).str.zfill(4)
    ndcs['code_suf'] = ndcs['ndc9'].str[-4:].astype(int).astype(str).str.zfill(3)
    ndcs['code_suf2'] = ndcs['ndc9'].str[-4:].astype(int).astype(str).str.zfill(4)
    ndcs['code'] = ndcs['code_pref'] + '-' + ndcs['code_suf']
    ndcs['code'] = ndcs['code'].where(ndcs['code_pref'].str.len() >= 5, ndcs['code_pref'] + '-' + ndcs['code_suf2'])
    return ndcs


if __name__ == "__main__":
    #Create RX_Norm def file from description got from Geisinger
    dcstart = 6000
    dict_file = 'dict.rx_defs'
    rx_list_file = '..\\Ontologies\\' + FROM_ONTO_NAME + '\\gei_rxnorm_list_o.txt'
    dict_path = '..\\Ontologies\\' + FROM_ONTO_NAME + '\\dicts'
    rx_df = pd.read_csv(rx_list_file, sep='\t')
    rx_dict = rx_df[['RXN_CD', 'RXN_NM']].copy()
    rx_dict['RXN_NM'] = 'RX_DESC:' + rx_dict['RXN_CD'].astype(str) + ':' + replace_spaces(rx_df['RXN_NM'])
    rx_dict['RXN_CD'] = 'RX_CODE:' + rx_dict['RXN_CD'].astype(str)
    rx_dict.drop_duplicates(inplace=True)
    rx_dict = code_desc_to_dict_df(rx_dict, dcstart, ['RXN_CD', 'RXN_NM'])
    write_tsv(rx_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')

    rx_ndc_file = '..\\Ontologies\\' + FROM_ONTO_NAME + '\\rxnorm_ndc_map.csv'
    rx_ndc_df = read_rx_ndc_map(rx_ndc_file)
    rx_ndc_df['code'] = 'NDC_CODE:' + rx_ndc_df['code']

    # Read NDC dict to filter out NDCs that does not exists
    ndc_dict_file = '..\\Ontologies\\' + TRU_ONTO_NAME + '\\dicts\\dict.ndc_defs'
    ndc_dict = pd.read_csv(ndc_dict_file, sep='\t', names=['defid', 'code'], usecols=[1, 2])
    ndc_dict = ndc_dict[ndc_dict['code'].str.contains('NDC_CODE')]
    # ndc_dict['code'] = ndc_dict['code'].str.replace('NDC_CODE:', '')
    ndcs_codes = ndc_dict['code'].unique()
    rx_ndc_df = rx_ndc_df[rx_ndc_df['code'].isin(ndcs_codes)]
    #print(rx_ndc_df)
    # read the missing mapping (cases where no NDC found using the APIs so manually map RxNorm to ATC
    missing_file = '..\\Ontologies\\' + FROM_ONTO_NAME + '\\missing_rx_atc_map.txt'
    missing_df = pd.read_csv(missing_file, sep='\t', dtype=str)

    dict_file = 'dict.rx_atc_set'
    atc_ndc_set_file = '..\\Ontologies\\' + TRU_ONTO_NAME + '\\dicts\\dict.atc_ndc_set'
    atc_ndc_set = pd.read_csv(atc_ndc_set_file, sep='\t', usecols=[1, 2], names=['atc', 'ndc'])
    rx_atc_map = rx_ndc_df[['code', 'rxcui']].merge(atc_ndc_set, left_on='code', right_on='ndc', how='left')
    rx_atc_map = rx_atc_map[rx_atc_map['atc'].notnull()][['rxcui', 'atc']]
    rx_atc_map = rx_atc_map.append(missing_df)
    rx_atc_map.drop_duplicates(inplace=True)
    rx_atc_map['rxcui'] = 'RX_CODE:' + rx_atc_map['rxcui']
    rx_atc_map['set'] = 'SET'
    write_tsv(rx_atc_map[['set', 'atc', 'rxcui']], dict_path, dict_file, mode='w')
