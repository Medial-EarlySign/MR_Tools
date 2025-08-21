import pandas as pd
from utils import replace_spaces, code_desc_to_dict_df, write_tsv
import os
ONTO_NAME = 'NDC'
ndc_product_file = '..\\Ontologies\\' + ONTO_NAME + '\\ndcxls\\product.txt'
dict_path = '..\\Ontologies\\' + ONTO_NAME + '\\dicts'


def get_product_df(ndc_product_file):
    ndc_df = pd.read_csv(ndc_product_file, sep='\t',encoding="ISO-8859-1", usecols=['PRODUCTNDC', 'PROPRIETARYNAME', 'SUBSTANCENAME'])
    ndc_df['SUBSTANCENAME'] = ndc_df['SUBSTANCENAME'].str.upper()
    ndc_df['SUBSTANCENAME'].fillna('', inplace=True)
    ndc_df['PROPRIETARYNAME'] = replace_spaces(ndc_df['PROPRIETARYNAME'].str.upper())
    ndc_df['PROPRIETARYNAME'].fillna('', inplace=True)
    ndc_df['PROPRIETARYNAME'] = ndc_df['PRODUCTNDC'] + ':' + ndc_df['PROPRIETARYNAME']
    ndc_df['PRODUCTNDC'] = 'NDC_CODE:' + ndc_df['PRODUCTNDC']
    ndc_df.drop_duplicates(inplace=True)
    return ndc_df


def write_ndc_def_dict(ndc_dict):
    dcstart = 300000
    dict_file = 'dict.ndc_defs'
    ndc_dict['len'] = ndc_dict['PROPRIETARYNAME'].str.len()
    ndc_dict.drop_duplicates('PRODUCTNDC', inplace=True, keep='last')
    ndc_dict = code_desc_to_dict_df(ndc_dict, dcstart, ['PRODUCTNDC', 'PROPRIETARYNAME'])
    write_tsv(ndc_dict[['def', 'defid', 'code']], dict_path, dict_file, mode='w')


def get_atc_ndc_map(ndc_df, onto_dir):
    TO_ONTO_NAME = 'ATC'
    atc_file = os.path.join(onto_dir,  TO_ONTO_NAME,  'atc_codes')
    atc_df = pd.read_csv(atc_file, sep='\t', names=['atc', 'desc'])
    atc_df['desc'] = atc_df['desc'].str.upper()

    syn_file = os.path.join(onto_dir,  ONTO_NAME, 'synonyms')
    syns = pd.read_csv(syn_file, sep='\t', names=['s1', 's2'])

    ignore = ['HYDROCHLORIDE', 'ACID', 'SODIUM', 'FUMARATE', 'POTASSIUM', 'CALCIUM', 'TARTRATE', 'NITRATE',
             'BESYLATE', 'SULFATE', 'BISULFATE', 'HYCLATE', 'ACETONIDE', 'SUCCINATE', 'DIHYDROCHLORIDE', 'PROPIONATE',
             'HYDROBROMIDE', 'CITRATE', 'HEMIHYDRATE', 'GLUCONATE', 'TROMETHAMINE', 'CHLORIDE', 'MESYLATE', 'OXALATE',
             'DIHYDRATE', 'MONOHYDRATE', 'PHOSPHATE', 'ACETATE', 'MALEATE']

    spacial_cases = [('AMOXICILLIN; CLAVULANATE POTASSIUM', 'ATC_J01C_R02'),
                     ('CLAVULANATE POTASSIUM; AMOXICILLIN',  'ATC_J01C_R02'),
                     ('AMOXICILLIN; AMOXICILLIN SODIUM; CLAVULANATE POTASSIUM', 'ATC_J01C_R02'),
                     ('HYDROCODONE BITARTRATE; ACETAMINOPHEN', 'ATC_N02B_E51'),
                     ('POLYETHYLENE GLYCOL 3350', 'ATC_A06A_D15'),
                     ('ACETAMINOPHEN; CODEINE PHOSPHATE', 'ATC_N02A_J06'),
                     ('PROMETHAZINE HYDROCHLORIDE; CODEINE PHOSPHATE', 'ATC_N02A_A59'),
                     ('ESOMEPRAZOLE MAGNESIUM', 'ATC_A02B_C05'),
                     ('ESOMEPRAZOLE MAGNESIUM DIHYDRATE', 'ATC_A02B_C05'),
                     ('BUTALBITAL; ACETAMINOPHEN; CAFFEINE', 'ATC_N05C_B01'),
                     ('ALENDRONATE SODIUM', 'ATC_M05B_A04'),
                     ('CHANTIX', 'ATC_N07B_A03'),
                     ('HYDROCODONE BITARTRATE; HOMATROPINE METHYLBROMIDE', 'ATC_R05D_A03'),
                     ('LOSARTAN POTASSIUM; HYDROCHLOROTHIAZIDE', 'ATC_C09D_A01'),
                     ('HYDROCHLOROTHIAZIDE; LOSARTAN POTASSIUM', 'ATC_C09D_A01'),
                     ('AMOXICILLIN; CLAVULANIC ACID', 'ATC_J01C_R02'),
                     ('NORGESTIMATE AND ETHINYL ESTRADIOL', 'ATC_G03A_A11')]


    #Add names to ATC from synonyms
    for i, r in syns.iterrows():
        exist = atc_df[atc_df['desc'] == r['s1']]
        if exist.shape[0] > 0:
            print('Already in ATC')
            continue
        new_df = atc_df[atc_df['desc'] == r['s2']]
        if new_df.shape[0] == 0:
            continue
        if new_df.shape[0] != 1:
            print(r['s2'] +' !!!! more then one option !!!')
        atc_df = atc_df.append({'atc': new_df.iloc[0]['atc'], 'desc': r['s1']}, ignore_index=True)

    # if word can be ignore add name to look for without the word
    ndc_df.loc[:, 'orig_SUBSTANCENAME'] = ndc_df['SUBSTANCENAME']
    for ig in ignore:
        ndc_df.loc[ndc_df['SUBSTANCENAME'].str.contains(ig),'SUBSTANCENAME'] = ndc_df['SUBSTANCENAME']+';'+ndc_df['SUBSTANCENAME'].str.replace(ig, '').str.strip()
    split_df = ndc_df['SUBSTANCENAME'].str.split(';', n=20, expand=True)
    ndc_df1 = ndc_df.join(split_df)

    mached = pd.DataFrame()
    not_matched = ndc_df1.copy()[['PRODUCTNDC', 'SUBSTANCENAME', 'orig_SUBSTANCENAME']+list(range(0,11))]
    for sc in spacial_cases:
        special_match = ndc_df1[ndc_df1['orig_SUBSTANCENAME'] == sc[0]][['PRODUCTNDC', 'SUBSTANCENAME']].copy()
        special_match['atc'] = sc[1]
        mached = mached.append(special_match[['PRODUCTNDC', 'SUBSTANCENAME', 'atc']])
        not_matched = not_matched[not_matched['orig_SUBSTANCENAME'] != sc[0]]

    for i in range(0,11):
        print(i)
        not_matched[i] = not_matched[i].str.strip()
        mrg = not_matched.merge(atc_df, left_on=i, right_on='desc', how='left')
        not_matched = mrg[mrg['atc'].isnull()][['PRODUCTNDC','SUBSTANCENAME']+list(range(0,11))]
        mached = mached.append(mrg[mrg['atc'].notnull()][['PRODUCTNDC','SUBSTANCENAME','atc']])
        print(not_matched.shape)
        print(mached.shape)
    return mached


if __name__ == '__main__':
    ndc_df = get_product_df(ndc_product_file)
    ndc_dict_df = ndc_df[['PRODUCTNDC', 'PROPRIETARYNAME']].copy()
    write_ndc_def_dict(ndc_dict_df)

    ndc_to_match = ndc_df[['PRODUCTNDC', 'SUBSTANCENAME']].copy()
    matched_set = get_atc_ndc_map(ndc_to_match, '..\\Ontologies\\')
    print(matched_set)
    set_file = 'dict.atc_ndc_set'
    matched_set['set'] = 'SET'
    write_tsv(matched_set[['set', 'atc', 'PRODUCTNDC']], dict_path, set_file, mode='w')
