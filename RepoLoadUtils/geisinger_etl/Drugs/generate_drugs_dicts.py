#!/opt/medial/dist/usr/bin/python
import pandas as pd
import os
import sys
import re


def is_nan(num):
    return num != num

# /nas1/Work/Users/Avi/NWP/data$ /nas1/UsersData/avi/MR/Tools/RepoLoadUtils/KPNW_etl/generate_drugs_dicts.py drug_names3 atc_codes ndc_atc4_2019.csv sysnonyms product.txt ndc_name_connector

# prep final table from res file:
#  grep Deci run1 | grep -v NONE | grep -v nan | awk '{print $4"\t"$10}' | sort | uniq > run1.ndc2atc
# or
# grep Deci run2 | awk '{print $4"\t"$10}' | sort | uniq > run2.ndc2atc


###################################
## globals
###################################
ndc_key = 'NDC2'
words_to_ignore = ["PUMP", "GROUP", "VERY", "POTENT", "ORAL", "TOTAL", "AND", "ALL", "SYSTEM", "WITH", "FOR", "USE",
                   "NORMAL", "C", "INHIBITOR", "INHIBITORS", "PRODUCTS", "W", "BLOOD", "GLUCOSE", "LOW", "NON",
                   "COMB", "RENAL", "VIT", "GAS", "SALT", "GUM", "CELL", "MILK", "H", "K", "OXYGEN", "S", "ALUM", 'NAN',
                   'ACID', 'AGENTS', 'CODE', 'COMBINATIONS', 'DERIVATIVES', 'DIURETICS', 'OLD', 'OTHER'
                   ]


#############################################################################
### functions
#############################################################################
# parses the ndc and adds a (int):(int) representation on its 2 first fields as
# key. We need this to work in all tables
def add_ndc_key(df, ndc_col, key_col, sp='-'):
    h_col = "split_my_ncd"
    df_new = df[ndc_col].str.split(sp, expand=True)

    df[key_col] = df_new[0].str.lstrip('0') + ":" + df_new[1].str.lstrip('0')


# getting rid of non alphanumerics, moving to uppercase and splitting to words
def get_normalized_words_t(text, d_syn):
    # s = re.sub('[^0-9a-zA-Z]+', ' ', text)
    s = re.sub('[^a-zA-Z]+', ' ', str(text))
    s = re.sub('  *', ' ', s)
    s = re.sub(' [a-zA-Z] ', ' ', s)
    s = re.sub(' [a-zA-Z][a-zA-Z] ', ' ', s)
    s = s.upper()
    words = s.split()
    words = list(set(words))
    with_syns = [x for x in words if x in d_syn.index]
    if len(with_syns) > 0:
        syns = flatten_to_set(d_syn.loc[with_syns].values.tolist())
        words = words + list(syns)
    words = [w for w in words if w not in words_to_ignore]
    return words


def get_normalized_words_list(list_texts, d_syn):
    all_words = []
    for t in list_texts:
        all_words = all_words + get_normalized_words_t(t, d_syn)
    return all_words


# preparing a dictionary from a word to all the ATC codes it is a part of
# also returning a weight for each word which is how many times it appeared
# in different 4 letters ATC (changed to 3...)
def prep_atc_codes_tables(df_atc, d_syn):
    df_atc['words'] = df_atc['ATC_Desc'].apply(lambda x: get_normalized_words_t(x, d_syn))
    df_atc["Desc_Len"] = df_atc['words'].str.len()
    df_atc["ATC4"] = df_atc['ATC_Code'].str[4:8] + df_atc['ATC_Code'].str[9:10]
    df_atc["Depth"] = 9 - df_atc['ATC_Code'].str.count('_')

    words_df = pd.DataFrame(df_atc['words'].values.tolist(), index=df_atc['ATC_Code'])
    words_df = words_df.stack().to_frame().reset_index()
    words_df['ATC3'] = words_df['ATC_Code'].str[4:7]
    dict_df = words_df.groupby(0)['ATC3'].apply(list)
    dict_df.rename('ATC3_list', inplace=True)

    full_dict_df = words_df.groupby(0)['ATC_Code'].apply(list)
    full_dict_df.rename('ATC_full_list', inplace=True)

    weights = dict_df.apply(lambda x: 1/len(set(x)))
    weights.rename('weights', inplace=True)
    words_df = words_df.merge(weights.reset_index(), how='left', on=0)
    tot_weight = words_df.groupby('ATC_Code')['weights'].sum(axis=1)
    df_atc = df_atc.merge(tot_weight.reset_index(), how='left', on='ATC_Code')
    dict_df = pd.concat([dict_df, weights, full_dict_df], axis=1)
    return dict_df, df_atc


def flatten_to_set(list_of_lists):
    return set([y for x in list_of_lists if not is_nan(x) for y in x])


# for each NDC name, we collect all the words in all the descriptions of it
# returning a dictionary from NDC code to a unique set of these words
# we also add all the descriptions in the product table
def prep_names_for_search(df_names, df_prod, d_syn):
    ncd_cnts = df_names.groupby(ndc_key)['Count'].sum()
    ncd_words0 = df_names.groupby(ndc_key)['Drug_Name'].apply(lambda x: get_normalized_words_list(list(x), d_syn))
    ndcs = df_names[ndc_key].unique()
    df_prod_short = df_prod[df_prod[ndc_key].isin(ndcs)]
    ncd_words1 = df_prod_short.groupby(ndc_key)['PROPRIETARYNAME'].apply(lambda x: get_normalized_words_list(list(x), d_syn))
    ncd_words2 = df_prod_short.groupby(ndc_key)['NONPROPRIETARYNAME'].apply(lambda x: get_normalized_words_list(list(x), d_syn))
    ncd_words3 = df_prod_short.groupby(ndc_key)['LABELERNAME'].apply(lambda x: get_normalized_words_list(list(x), d_syn))
    ncd_words4 = df_prod_short.groupby(ndc_key)['PHARM_CLASSES'].apply(lambda x: get_normalized_words_list(list(x), d_syn))
    ncd_words_df = pd.concat([ncd_words0, ncd_words1, ncd_words2, ncd_words3, ncd_words4], axis=1, sort=True)
    ncd_words = ncd_words_df.apply(lambda row: flatten_to_set(row.tolist()), axis=1)
    ncd_words = pd.concat([ncd_words, ncd_cnts], axis=1)
    ncd_words.rename(columns={0: 'words'}, inplace=True)
    return ncd_words


#
# for each ndc, going over all unique words and summings scores for all relevant atcs
def search_names_in_atc_dict(atc_words_df, ndc_words_df, df_atc, ndc2atc4):
    match_list = []
    ndc_words_df.sort_values(by='Count', ascending=False, inplace=True)
    #ndc_words_df = ndc_words_df[ndc_words_df.index == '69374:953']
    for ndc, row in ndc_words_df.iterrows():
        curr_d = ndc2atc4[ndc] if ndc in ndc2atc4.index else {}
        ws = [x for x in row['words'] if x in atc_words_df.index]
        one_ndc_word_df = atc_words_df.loc[ws]
        all_atcs = one_ndc_word_df['ATC_full_list'].values.tolist()
        all_atcs = flatten_to_set(all_atcs)
        atc_for_ndc = df_atc[df_atc['ATC_Code'].isin(all_atcs)].copy()

        if not atc_for_ndc.empty:
            words_df = pd.DataFrame(one_ndc_word_df['ATC_full_list'].values.tolist(), index=one_ndc_word_df.index)
            words_df = words_df.stack().to_frame().reset_index(1)
            grp = words_df.merge(one_ndc_word_df[['weights']], left_index=True, right_index=True).groupby(0)
            weights_ndc = pd.concat([grp['weights'].sum().rename('weights_ndc'), grp.apply(lambda x: x.index.tolist()).rename('wcommon')], axis=1)
            atc_for_ndc = atc_for_ndc.merge(weights_ndc, how='left', left_on='ATC_Code', right_index=True)

            #  The total weight function
            atc_for_ndc['weights_ndc'] = atc_for_ndc['weights_ndc'] + \
                                         (0.75*atc_for_ndc['weights_ndc']/atc_for_ndc['weights']) + \
                                         0.15*atc_for_ndc['Depth'] + \
                                         0.5*atc_for_ndc['wcommon'].str.len()/atc_for_ndc['Desc_Len'] + \
                                         0.1*atc_for_ndc['wcommon'].str.len()
            # Give bonus for the ATC that has match in the ndc to ATC mapping
            cond = atc_for_ndc['ATC4'].isin(curr_d)
            atc_for_ndc.loc[cond, 'weights_ndc'] = atc_for_ndc[cond]['weights_ndc'] + atc_for_ndc['Depth']

        #  Print findings
        print("==============================================")
        print(ndc, atc_for_ndc.shape[0], row['words'], "count: ", row['Count'])
        print("====>", curr_d)
        if not atc_for_ndc.empty:
            for i, r in atc_for_ndc.sort_values(by='weights_ndc', ascending=False).iterrows():
                if r['weights_ndc'] >= 0.1:
                    print(r['weights_ndc'], r['ATC_Code'], r['ATC_Desc'], " wcommon: ", r['wcommon'])

        if atc_for_ndc.empty and len(curr_d) == 0:
            print("==============================================")
            print(ndc, atc_for_ndc.shape[0], row['words'], "count: ", row['Count'])
            print("====>", curr_d)
            code = "NONE_" + str(len(curr_d))
            print("Decision: NoMatch: ", ndc, "count: ", row['Count'], "score: -1  code: ", code,
                  "words: ", m['wcommon'])
            match_list.append({'match_type': 'NoMatch', 'ndc': ndc, 'count': row['Count'], 'score': -1, 'code': code,
                               'words': m['wcommon']})
            continue

        if not atc_for_ndc.empty and len(curr_d) == 0:
            # ATC code match not found (get best score
            best_score = atc_for_ndc['weights_ndc'].max()
            max_df = atc_for_ndc[atc_for_ndc['weights_ndc'] == best_score]  # all the element with max score
            for i, m in max_df.iterrows():
                print("Decision: ScoreOnly NDC: ", ndc, "count: ", row['Count'], "score: ", m['weights_ndc'], " code: ",
                      m['ATC_Code'], " wcommon: ", m['wcommon'])
                match_list.append({'match_type': 'ScoreOnly', 'ndc': ndc, 'count': row['Count'],
                                   'score': m['weights_ndc'], 'code': m['ATC_Code'], 'words': m['wcommon']})
            continue

        atc4score = atc_for_ndc[atc_for_ndc['ATC4'].isin(curr_d)]
        if not atc4score.empty:  # ATC code match found (get best score for each ATC found)
            for atc, df in atc4score.groupby('ATC4'):
                curr_d.remove(atc)
                max_df = df[df['weights_ndc'] == df['weights_ndc'].max()]
                for i, m in max_df.iterrows():
                    code = m['ATC_Code']
                    print("Decision: NDC2ATC4+Score NDC: ", ndc, "count: ", row['Count'], "score: ",
                          m['weights_ndc'], " code: ", code, " wcommon: ", m['wcommon'])
                    match_list.append({'match_type': 'NDC2ATC4+Score', 'ndc': ndc, 'count': row['Count'],
                                       'score':  m['weights_ndc'], 'code': code, 'words': m['wcommon']})
        for atc in curr_d:  # For all acts that not found in matched in the atc_for_ndc
            code = "ATC_" + atc[0:4] + "_" + atc[4:5] + "__"
            print("Decision: NDC2ATC4: ", ndc, "count: ", row['Count'], "score: ",
                  0, " code: ", code, " wcommon: ", [])
            match_list.append({'match_type': 'Only NDC2ATC4', 'ndc': ndc, 'count': row['Count'],
                               'score': 0, 'code': code, 'words': []})

    return pd.DataFrame(match_list)


def prep_ndc2atc4_dictionary(df_ndc):
    df_ndc1 = df_ndc[['ATC4', 'NDC2']].drop_duplicates()
    d2 = df_ndc1.groupby('NDC2')['ATC4'].apply(list)
    # return d2.to_dict()
    return d2


def get_syn_dict(df_syn, bank_syns_df):
    splt_names = df_syn['Name1'].str.split(',', expand=True)
    splt_names['Name2'] = df_syn['Name2']
    to_stack = splt_names.set_index('Name2', drop=True)
    dict_df = to_stack.stack().to_frame()
    dict_df['Name2'] = dict_df.index.get_level_values(0)
    dict_df['Name2'] = dict_df['Name2'].str.split(',')
    dict_df.rename({0: 'index'}, axis=1, inplace=True)
    dict_df.set_index('index', inplace=True)
    bank_syns_df.rename(columns={'Common name': 'index', 'syn_list': 'Name2'}, inplace=True)
    bank_syns_df.set_index('index', inplace=True)
    dict_df = pd.concat([dict_df, bank_syns_df])
    # return dict_df['Name2'].to_dict()
    return dict_df['Name2']


#############################################################################
#### M A I N 
#############################################################################

def match(): # (drug_names_file, atc_codes_file, ndc_to_atc4_file, synonyms_file, ndc_product_file, res_file):
    #drug_names_file = sys.argv[1]
    #atc_codes_file = sys.argv[2]
    #ndc_to_atc4_file = sys.argv[3]
    #synonyms_file = sys.argv[4]
    #ndc_product_file = sys.argv[5]

    # ndc_name_connector = sys.argv[6]
    drug_names_file = 'NDC_List_20200409.csv'
    atc_codes_file = 'atc_codes'
    ndc_to_atc4_file = 'H:\\MR\\Tools\\RepoLoadUtils\\KPNW_etl\\Drug\\ndc_atc4_2019.csv'
    synonyms_file = 'H:\\MR\\Tools\\RepoLoadUtils\\KPNW_etl\\Drug\\synonyms'
    ndc_product_file = 'H:\\MR\\Tools\\RepoLoadUtils\\KPNW_etl\\Drug\\product.txt'
    drug_bank_syns = 'H:\\MR\\Tools\\RepoLoadUtils\\KPNW_etl\\Drug\\drugbank_synonyms.txt'
    res_file = 'match_result.txt'
    # reading all files to pandas
    if 'pharmpy' in ndc_to_atc4_file:
        df_ndc = pd.read_csv(ndc_to_atc4_file, usecols=[0, 1], names=['NDC', 'ATC4'], sep='\t', dtype=str,  header=0)
    else:
        df_ndc = pd.read_csv(ndc_to_atc4_file, sep=',', usecols=[2, 4], dtype=str)
    df_atc = pd.read_csv(atc_codes_file, sep='\t', header=None, names=["ATC_Code", "ATC_Desc"])
    #df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
    #                       dtype={'Count': int,  "NDC": str, "Drug_Name": str})
    df_names = pd.read_csv(drug_names_file, header=1, usecols=[0, 2, 5], names=["NDC", "Drug_Name", "Count"])
    df_syn = pd.read_csv(synonyms_file, sep='\t', header=None, names=["Name1", "Name2"])
    bank_syns_df = pd.read_csv(drug_bank_syns,sep='\t')
    df_prod = pd.read_csv(ndc_product_file, sep='\t', encoding="ISO-8859-1", dtype=str)


    add_ndc_key(df_prod, 'PRODUCTNDC', ndc_key)
    add_ndc_key(df_names, 'NDC', ndc_key)
    add_ndc_key(df_ndc, 'NDC', ndc_key)
    bank_syns_df['syn_list'] = bank_syns_df['syn_list'].apply(lambda x: eval(x))

    d_syn = get_syn_dict(df_syn, bank_syns_df)
    ndc2atc4 = prep_ndc2atc4_dictionary(df_ndc)
    atc_words_df, df_atc = prep_atc_codes_tables(df_atc, df_syn)
    ndc_words_df = prep_names_for_search(df_names, df_prod, d_syn)

    res_df = search_names_in_atc_dict(atc_words_df, ndc_words_df, df_atc, ndc2atc4)
    res_df.to_csv(res_file, sep='\t', index=False)
    return res_df


if __name__ == "__main__":
    # match(sys.argv[1:])
    res_file = 'match_result.txt'
    if os.path.exists(res_file):
        res_df = pd.read_csv(res_file, sep='\t')
    else:
        res_df = match() # (sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], res_file)

    #drug_names_file = sys.argv[1]
    #kp_ndc = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
    #                     dtype={'Count': int, "NDC": str, "Drug_Name": str})
    drug_names_file = 'NDC_List_20200409.csv'
    kp_ndc = pd.read_csv(drug_names_file, header=1, usecols=[0, 2, 5], names=["NDC", "Drug_Name", "Count"])
    add_ndc_key(kp_ndc, 'NDC', ndc_key)
    #kp_map_file = sys.argv[6]

    #kp_map_df = pd.read_csv(kp_map_file, sep='\t', names=['Drug_Name', 'drugid'], header=0)
    #kp_ndc = kp_ndc.merge(kp_map_df, how='left', on='Drug_Name')
    res_df = res_df.merge(kp_ndc, how='outer', left_on='ndc', right_on='NDC2')
    res_df = res_df[(res_df['code'].notnull()) & (res_df['Drug_Name'].notnull())]
    res_df = res_df[~res_df['code'].str.contains('NONE')]
    grp = res_df.groupby('Drug_Name')
    #map_res = pd.concat([grp['Drug_Name'].first(), grp['ndc'].apply(set), grp['code'].apply(set)], axis=1)
    map_res = pd.concat([grp['ndc'].apply(set), grp['code'].apply(set)], axis=1)
    map_res['map'] = 'MAP'
    map_res.reset_index(inplace=True)
    #map_res[['map', 'Drug_Name', 'drugid', 'ndc', 'code']].to_csv('mapping_drug_names_to_atc', sep='\t', index=False)
    map_res[['map', 'Drug_Name', 'ndc', 'code']].to_csv('mapping_drug_names_to_atc', sep='\t', index=False)
    print('DONE')
