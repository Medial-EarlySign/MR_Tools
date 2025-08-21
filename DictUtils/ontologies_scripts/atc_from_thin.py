import os
import pandas as pd

ONTO_NAME = 'ATC'

drug_codes_file = '..\\Ontologies\\' + ONTO_NAME + '\\Drugcodes1801.txt'
atc_codes_file = '..\\Ontologies\\' + ONTO_NAME + '\\ATCTerms1801.txt'
dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.atc_defs'
set_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.atc_sets'

ATCTerms_fwf = {'ATC': (0, 8), 'Term': (8, 264)}


def atc_code_from_atc(df, col):
    return 'ATC_' + df[col].str.replace(' ', '_').str.pad(width=8, side='right', fillchar='_')


def atc_dicts():
    if not (os.path.exists(drug_codes_file)):
        raise NameError('config error - drug codes don''t exists')
    if not (os.path.exists(atc_codes_file)):
        raise NameError('config error - atc terms exists')
    atc_start = 100000

    atc_codes_df = pd.read_fwf(atc_codes_file, colspecs=list(ATCTerms_fwf.values()), names=list(ATCTerms_fwf.keys()))

    len_dicts = {1: 3, 2: 3, 3: 4, 4: 6, 6: 8, 8: 8}
    set_dict_hier = pd.DataFrame()
    # Set from ATC hierarchy
    for _, atc1 in atc_codes_df.iterrows():
        val = atc1['ATC']
        for inn in [s for s in atc_codes_df['ATC'].values if val in s and len(s) <= len_dicts[len(val)] and val != s]:
            set_dict_hier = set_dict_hier.append({'outter': val, 'inner': inn}, ignore_index=True)
    set_dict_hier['inner'] = atc_code_from_atc(set_dict_hier, 'inner')
    set_dict_hier['outter'] = atc_code_from_atc(set_dict_hier, 'outter')
    set_dict_hier['type'] = 'SET'
    set_dict_hier[['type', 'outter', 'inner']].to_csv(set_file, sep='\t', index=False, header=False, line_terminator='\n')

    # Crate ATC def files
    atc_codes_df = atc_codes_df.append({'ATC': 'G03X X',
                                        'Term': 'OTHER SEX HORMONES AND MODULATORS OF THE GENITAL SYSTEM'},
                                       ignore_index=True)
    atc_codes_df = atc_codes_df.assign(defid=range(atc_start, atc_start + atc_codes_df.shape[0]))
    atc_codes_df['ATC'] = atc_code_from_atc(atc_codes_df, 'ATC')
    atc_codes_df['Term'] = atc_codes_df['Term'].str.replace(' ', '_')
    atc_codes_df['Term'] = atc_codes_df['ATC'] + ':' + atc_codes_df['Term'].str.strip()
    to_stack = atc_codes_df.set_index('defid', drop=True)
    atc_dict = to_stack.stack().to_frame()
    atc_dict['defid'] = atc_dict.index.get_level_values(0)
    atc_dict.rename({0: 'code'}, axis=1, inplace=True)
    atc_dict['type'] = 'DEF'
    atc_dict[['type', 'defid', 'code']].to_csv(dict_file, sep='\t', index=False, header=False, line_terminator='\n')
    print('DONE atc_dicts')


if __name__ == '__main__':
    atc_dicts()
