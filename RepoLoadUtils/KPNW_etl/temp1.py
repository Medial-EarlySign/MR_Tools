import os
import pandas as pd
from Configuration import Configuration
from utils import fixOS


def add_ndc_key(df, ndc_col, key_col, sp='-'):
    df_new = df[ndc_col].str.split(sp, expand=True)
    df[key_col] = df_new[0].str.lstrip('0') + ":" + df_new[1].str.lstrip('0')


def final_map_with_desc():
    cfg = Configuration()
    out_folser = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    drug_names_file = os.path.join(code_folder, 'Drug', 'Drug_names3')
    df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
                           dtype={'Count': int, "NDC": str, "Drug_Name": str})
    df_names = df_names.groupby('Drug_Name')['Count'].sum().reset_index()


    kp_map_file = os.path.join(code_folder, 'Drug', 'drug_names_map.csv')
    kp_map_df = pd.read_csv(kp_map_file, sep='\t', names=['Drug_Name', 'drugid'], header=0)
    df_names = df_names.merge(kp_map_df, how='left', on='Drug_Name')

    map_file = os.path.join(code_folder, 'Drug', 'mapping_drug_names_to_atc')
    map_df = pd.read_csv(map_file, sep='\t', usecols=[1, 2, 3, 4])
    map_df['ndc'] = map_df['ndc'].apply(lambda x: eval(x))
    map_df['code'] = map_df['code'].apply(lambda x: eval(x))
    map_df = map_df.merge(df_names)

    ndc_to_atc4_file = os.path.join(code_folder, 'Drug', 'ndc_atc_pharmpy.csv')
    df_ndc = pd.read_csv(ndc_to_atc4_file, usecols=[0, 1, 2], names=['NDC', 'ATC4', 'ATC_Desc'], sep='\t', dtype=str, header=0)
    add_ndc_key(df_ndc, 'NDC', 'NDC2')
    df_ndc['ATC_Desc'] = df_ndc['ATC4']+':'+df_ndc['ATC_Desc']
    df_ndc_atc_map = df_ndc.groupby('NDC2')['ATC_Desc'].apply(list)

    ndc_product_file = os.path.join(code_folder, 'Drug', 'product.txt')
    df_prod = pd.read_csv(ndc_product_file, sep='\t', usecols=[1, 3], encoding="ISO-8859-1", dtype=str)
    add_ndc_key(df_prod, 'PRODUCTNDC', 'NDC2')
    df_prod = df_prod.set_index('NDC2')['PROPRIETARYNAME']

    atc_codes_file = os.path.join(code_folder, 'Drug', 'atc_codes')
    df_atc = pd.read_csv(atc_codes_file, sep='\t', header=None, names=["ATC_Code", "ATC_Desc"])
    df_atc = df_atc.set_index('ATC_Code')['ATC_Desc']

    map_df['ndc_prod_map'] = map_df['ndc'].apply(lambda x: {y: df_prod[y] if y in df_prod.index else '' for y in x})
    map_df['ndc_atc_map'] = map_df['ndc'].apply(lambda x: {y: df_ndc_atc_map[y] if y in df_ndc_atc_map.index else '' for y in x})
    map_df['code'] = map_df['code'].apply(lambda x: {y: df_atc[y] if y in df_atc.index else '' for y in x})
    map_df.sort_values(by='Count', ascending=False, inplace=True)
    map_df.to_csv(os.path.join(out_folser, 'drugs_match.txt'), sep='\t', index=False)


def comp_map_file():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    drug_names_file = os.path.join(code_folder, 'Drug', 'Drug_names3')
    df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
                           dtype={'Count': int, "NDC": str, "Drug_Name": str})
    df_names_unq = df_names.groupby('Drug_Name')['Count'].sum().reset_index()

    map_file = os.path.join(code_folder, 'Drug', 'mapping_drug_names_to_atc')
    map_file1 = os.path.join(code_folder, 'mapping_drug_names_to_atc0307')

    map_df = pd.read_csv(map_file, sep='\t')
    map_df1 = pd.read_csv(map_file1, sep='\t', names=['map', 'Drug_Name', 'drugid', 'ndc', 'code'], header=None)
    map_df['ndc'] = map_df['ndc'].apply(lambda x: eval(x))
    map_df1['ndc'] = map_df1['ndc'].apply(lambda x: eval(x))
    map_df['code'] = map_df['code'].apply(lambda x: eval(x))
    map_df1['code'] = map_df1['code'].apply(lambda x: eval(x))
    mrg = map_df.merge(map_df1, on='drugid')
    mrg = mrg.merge(df_names_unq, how='left', left_on='Drug_Name_x', right_on='Drug_Name')
    mrg.sort_values(by='Count', inplace=True)
    mrg.set_index('drugid', inplace=True)
    cnt = 0
    for kp, r, in mrg.iterrows():
        #if len(r['ndc_x'].difference(r['ndc_y'])) != 0:
        if len(set(r['ndc_y']) - r['ndc_x']) != 0:
            #print(kp + ' NDC diff ' + str(r['ndc_x'].difference(r['ndc_y'])) + ' - ' + str(r['Count']))
            print(kp + ' NDC diff ' + str(set(r['ndc_y']) - r['ndc_x']))
            cnt += 1
        #if len(r['code_x'].difference(r['code_y'])) != 0:
        if len(set(r['code_y']) - r['code_x']) != 0:
            #print(kp + ' Code diff ' + str(r['code_x'].difference(r['code_y'])) + ' - ' + str(r['Count']))
            print(kp + ' Code diff ' + str(set(r['code_y']) - r['code_x']) + ' - ' + str(r['Count']))
            cnt += 1
    print(str(cnt) + ' diffs')


def comp_rx_maps():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)

    yaron_map_file =  os.path.join(code_folder, 'Drug', 'ndc_atc4_2019.csv')
    tamar_map_file = os.path.join(code_folder, 'Drug', 'ndc_atc_pharmpy.csv')
    drug_names_file = os.path.join(code_folder, 'Drug', 'Drug_names3')

    df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
                           dtype={'Count': int, "NDC": str, "Drug_Name": str})
    df_names = df_names[~df_names['NDC'].str.contains('MISSING')]

    y_map_df = pd.read_csv(yaron_map_file, sep=',', usecols=[2, 4], dtype=str)
    t_map_df = pd.read_csv(tamar_map_file, sep='\t')
    y_map_df.drop_duplicates(inplace=True)
    t_map_df.drop_duplicates(inplace=True)
    add_ndc_key(y_map_df, 'NDC', 'NDC2')
    add_ndc_key(t_map_df, 'ndc', 'NDC2')
    add_ndc_key(df_names, 'NDC', 'NDC2')

    y_match = df_names.merge(y_map_df, how='left', on='NDC2')
    t_match = df_names.merge(t_map_df[['NDC2', 'atc']], how='left', on='NDC2')
    print()


def comp_match_file():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)

    # Drug name read
    drug_names_file = os.path.join(code_folder, 'Drug', 'Drug_names3')
    df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count", "NDC", "Drug_Name"],
                           dtype={'Count': int, "NDC": str, "Drug_Name": str})
    df_names = df_names[~df_names['NDC'].str.contains('MISSING')]
    add_ndc_key(df_names, 'NDC', 'NDC2')

    # KP list
    kp_map_file = os.path.join(code_folder, 'Drug', 'drug_names_map.csv')
    kp_map_df = pd.read_csv(kp_map_file, sep='\t', names=['Drug_Name', 'drugid'], header=0)
    kp_ndc = df_names.merge(kp_map_df, how='left', on='Drug_Name')

    res2_file = os.path.join(code_folder, 'Drug', 'match_result2.txt')
    res3_file = os.path.join(code_folder, 'Drug', 'match_result3.txt')
    res4_file = os.path.join(code_folder, 'Drug', 'match_result4.txt')
    res2_df = pd.read_csv(res2_file, sep='\t')
    res3_df = pd.read_csv(res3_file, sep='\t')
    res4_df = pd.read_csv(res4_file, sep='\t')
    res2_df = res2_df[~res2_df['ndc'].str.contains('MISSING')]
    res3_df = res3_df[~res3_df['ndc'].str.contains('MISSING')]
    res4_df = res4_df[~res4_df['ndc'].str.contains('MISSING')]
    print('\nrxNav map list')
    print(res2_df.groupby('match_type')['ndc'].count())
    print('\nmap using pharmpy')
    print(res3_df.groupby('match_type')['ndc'].count())
    print('\nmap using pharmpy with drug bank synonyms')
    print(res4_df.groupby('match_type')['ndc'].count())


def build_syn_list():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)

    # Drug name read
    drug_bank_file = os.path.join(code_folder, 'Drug', 'drugbank vocabulary.csv')
    drug_bank_df = pd.read_csv(drug_bank_file, usecols=[2, 5])
    drug_bank_df = drug_bank_df[drug_bank_df['Synonyms'].notnull()]
    drug_bank_df['Synonyms'] = drug_bank_df['Synonyms'].str.strip().str.upper()
    drug_bank_df['Common name'] = drug_bank_df['Common name'].str.upper()
    drug_bank_df['syn_list'] = drug_bank_df['Synonyms'].str.split('|', expand=False)
    drug_bank_df['syn_list'] = drug_bank_df['syn_list'].apply(lambda x: [y.strip() for y in x])

    drug_bank_df[['Common name', 'syn_list']].to_csv(os.path.join(code_folder, 'Drug', 'drugbank_synonyms.txt'), sep='\t', index=False)



if __name__ == '__main__':
    file1 = 'W:\\Users\\Tamar\\kpnw_load\\FinalSignals\\HbA1C1'
    df = pd.read_csv(file1, sep='\t', names=['pid', 'sig', 'time', 'val1', 'val2', 'val3', 'val4'])
    frompid = 3283500
    topid =   3284000
    df[(df['pid']>frompid) & (df['pid']<topid)].to_csv(file1+'_4', sep='\t', index=False, header=False)
    print(df)
    #comp_map_file()
    #comp_rx_maps()
    #comp_match_file()
    #build_syn_list()
    #final_map_with_desc()
