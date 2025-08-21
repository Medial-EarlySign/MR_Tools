import xml.etree.ElementTree as et
import pandas as pd
import os

rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_diags_file = 'rambom_diag_codes.csv'
rambam_diag_dict_file = 'dict.diagnoses'

ICD9_dict = 'W:\\Data\\Mapping\\ICD9\\dict.icd9'
ICD10_dict = 'W:\\Data\\Mapping\\ICD10\\dict.icd10'
SNMI_dict = 'W:\\Data\\Mapping\\SNMI\\dict.snmi'


def parse_one_xml(xml_file_name):
    code_list = []
    tree = et.parse(xml_file_name)
    root = tree.getroot()
    cond_dict = {}
    for child in root:
        if child.attrib['Type'] == 'ev_diagnoses':
            for chch in child:
                if chch.attrib['Name'] == 'conditioncode':
                    cond_dict = {'code':  chch.text, 'desc': chch.attrib['Hier']}
                    code_list.append(cond_dict)
    return code_list


def read_rambam__xmls():
    xml_files = os.listdir(rambam_xml_dir)  # [19000:25000]

    diag_df = pd.DataFrame()
    cnt = 0
    for file in xml_files:
        print(cnt)
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        cnt = cnt+1
        ret_list = parse_one_xml(xml_fd)
        if len(ret_list) > 0:
            diag_df = diag_df.append(ret_list)
            diag_df.drop_duplicates(inplace=True)
        xml_fd.close()

    print(diag_df.shape)
    diag_df.to_csv(rambam_diags_file, index=False, sep='\t')
    return diag_df


def load_rambam_diag():
    return pd.read_csv(rambam_diags_file, sep='\t')


def map_rambam_codes(rambam_codes, onto_dict_file):
    onto_def = pd.read_csv(onto_dict_file, sep='\t', names=['typ', 'medialid', 'desc'])
    onto_def['list'] = onto_def['desc'].str.split(':')
    onto_def['code_orig'] = onto_def.apply(lambda row: row['list'][1], axis=1)   # keep the orig code to find procedures
    onto_def['code'] = onto_def['code_orig'].str.replace('.', '')
    onto_def['code'] = onto_def['code'].str.replace('/', '')
    onto_def['code'] = onto_def['code'].str.replace('-', '')

    lists = onto_def[['medialid', 'desc']].groupby(['medialid']).agg(lambda x: list(set(x.tolist())))
    onto_def = onto_def[['code', 'code_orig', 'medialid']].groupby('medialid').first()
    onto_def = pd.concat([onto_def, lists], axis=1, sort=False)

    #  remove the codes that are procedures and not diagnstict where the dot are in lower position 001.0 is diag 00.10 is procidure
    onto_def['dot_loc'] = onto_def['code_orig'].str.find('.')
    onto_def.sort_values(['code', 'dot_loc'], ascending=[True, False], inplace=True)
    onto_def.drop_duplicates('code', inplace=True)

    onto_def = onto_def.reset_index(drop=False).set_index('code', drop=True)

    rambam_codes['code'] = rambam_codes['code'].str.replace('/', '')
    rambam_codes['desc_list'] = rambam_codes['code'].map(onto_def['desc'])
    rambam_codes['medialid'] = rambam_codes['code'].map(onto_def['medialid'])

    return rambam_codes


if __name__ == '__main__':
    if os.path.isfile(rambam_diags_file):
        diag_df = load_rambam_diag()
    else:
        diag_df = read_rambam__xmls()
    to_drop = []
    to_rename = {}
    diag_df.reset_index()
    dict_df = diag_df['desc'].str.split(':|~', expand=True)
    for i in dict_df.columns:
        if i % 2:
            to_rename[i] = int((i-1)/2)
        else:
            to_drop.append(i)

    print(to_rename)
    print(to_drop)

    #  XML descriptions to df with colums to each desc 0-9
    dict_df.drop(to_drop, axis=1, inplace=True)
    dict_df.rename(to_rename, axis=1, inplace=True)
    diag_df = diag_df.merge(dict_df, left_index=True, right_index=True)
    diag_df.drop('desc', axis=1, inplace=True)
    diag_df.to_csv("rambam_diag_hier_all.csv", index=False)

    rambam_diag_dict_icd9 = map_rambam_codes(diag_df[['code']], ICD9_dict)
    rambam_diag_dict_snmi = map_rambam_codes(diag_df[['code']], SNMI_dict)
    rambam_diag_dict_icd10 = map_rambam_codes(diag_df[['code']], ICD10_dict)

    rambam_diag_dict = rambam_diag_dict_icd9[rambam_diag_dict_icd9['desc_list'].notnull()]
    missing_codes = rambam_diag_dict_icd9[rambam_diag_dict_icd9['desc_list'].isnull()]
    missing_codes = missing_codes[['code']].merge(rambam_diag_dict_snmi, on='code')
    rambam_diag_dict = pd.concat([rambam_diag_dict, missing_codes[missing_codes['desc_list'].notnull()]])

    missing_codes = missing_codes[missing_codes['desc_list'].isnull()]
    missing_codes = missing_codes[['code']].merge(rambam_diag_dict_icd10, on='code')
    rambam_diag_dict = pd.concat([rambam_diag_dict, missing_codes[missing_codes['desc_list'].notnull()]])

    missing_codes = missing_codes[missing_codes['desc_list'].isnull()]

    rambam_def = pd.DataFrame()
    for ind, row in rambam_diag_dict.iterrows():
        for desc in row['desc_list']:
            rambam_def = rambam_def.append({'typ': 'DEF', 'medialid': str(int(row['medialid'])),
                                            'desc': desc}, ignore_index=True)

    rambam_def[['typ', 'medialid', 'desc']].to_csv(rambam_diag_dict_file, sep='\t', index=False, header=False)

    print(rambam_def)
    '''
    rambam_diag_dict = pd.DataFrame(columns=['typ', 'medialid', 'desc'])


    diag_df['prefix'] = 'DIAG_ICD9_CODE:'
    diag_df['prefix'] = diag_df['prefix'].where(~diag_df['code'].str.startswith('M'), 'DIAG_SNMI_CODE:')
    diag_df['code'] = diag_df['code'].str.replace('/', '',)
    rambam_diag_dict['desc'] = diag_df['prefix'] + diag_df['code']
    rambam_diag_dict['medialid'] = rambam_diag_dict.index + icd9_med_index_start
    rambam_diag_dict['typ'] = 'DEF'
    rambam_diag_dict[['typ', 'medialid', 'desc']].to_csv(rambam_diag_dict_file, sep='\t', index=False, header=False)
    '''