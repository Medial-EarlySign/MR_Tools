import xml.etree.cElementTree as et
import pandas as pd
import os
import sys
sys.path.append('..\\')
from ontologies_dicts.dict_from_bioportal import get_code_decs_map


def parse_one_xml(xml_file_name, section_type_list, attr_name_list):
    code_list = []
    try:
        tree = et.parse(xml_file_name)
        root = tree.getroot()
    except OSError:
        print('ERROR: !!!!!!!!!!!!!!!! '+str(xml_file_name)+'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    # for child in root:
    #     if child.attrib['Type'] in section_type_list:
    #         for chch in child:
    #             if chch.attrib['Name'] in attr_name_list:
    #                 if chch.text.isdigit():
    #                     cond_dict = {'code':  chch.text, 'desc': chch.attrib['Hier']}
    #                 else:
    #                     cond_dict = {'code_str': chch.text, 'desc': chch.attrib['Hier']}
    #                 code_list.append(cond_dict)
    # return code_list

    all_ev = root.findall('Ev')
    op_ev = [ev for ev in all_ev if ev.attrib['Type'] in section_type_list]
    for ev in op_ev:
        for attr in attr_name_list:
            attr_name = ev.find(".//Pr[@Name='"+attr+"']")
            if attr_name is not None:
                #if attr_name.attrib['Hier'] == 'None':
                #    print('!!!!!!')
                cond_dict = {'code': attr_name.text, 'desc': attr_name.attrib['Hier']}
                code_list.append(cond_dict)
    return code_list



def read_rambam_xmls(rambam_xml_dir, section_type_list, attr_name_list, rambam_codes_file):
    xml_files = os.listdir(rambam_xml_dir) # [10000:10100]
    diag_df = pd.DataFrame()
    cnt = 0
    for file in xml_files:
        print(cnt)
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        cnt = cnt+1
        ret_list = parse_one_xml(xml_fd, section_type_list, attr_name_list)
        if len(ret_list) > 0:
            diag_df = diag_df.append(ret_list)
            diag_df.drop_duplicates(inplace=True)
        xml_fd.close()

    print(diag_df.shape)
    diag_df.to_csv(rambam_codes_file, index=False, sep='\t')
    return diag_df


def load_rambam_diag(rambam_codes_file):
    return pd.read_csv(rambam_codes_file, sep='\t')


def read_onto_set_dict(onto_set_file):
    onto_set = pd.read_csv(onto_set_file, sep='\t', names=['typ', 'parent', 'code'])
    onto_set['list'] = onto_set['code'].str.split(':')
    onto_set['code_code'] = onto_set.apply(lambda row: row['list'][1], axis=1)
    onto_set['list'] = onto_set['parent'].str.split(':')
    onto_set['parent_code'] = onto_set.apply(lambda row: row['list'][1], axis=1)
    onto_set.drop('list', axis=1, inplace=True)
    return onto_set


def xml_list_to_csv(from_xml):
    to_drop = []
    to_rename = {}
    from_xml.reset_index()
    dict_df = from_xml['desc'].str.split(':|~', expand=True)
    for i in dict_df.columns:
        if i % 2 and i < 16:
            if (i % 4) == 1:
                pref = 'code'
            else:
                pref = 'desc'
            to_rename[i] = pref + str(int(i/4))
        else:
            to_drop.append(i)
    print(to_rename)
    print(to_drop)
    # #  XML descriptions to df with colums to each desc 0-9
    dict_df.drop(to_drop, axis=1, inplace=True)
    dict_df.rename(to_rename, axis=1, inplace=True)
    # #  Strip all values:
    for col in dict_df.columns:
        dict_df[col] = dict_df[col].str.strip()
    return dict_df


def map_rmabam_level(onto, rambam_codes, onto_def, onto_set, level):
    lvl_code_field = 'code' + str(level)
    cod_map = rambam_codes[[lvl_code_field, 'CODE']].copy().dropna()
    cod_map[lvl_code_field] = cod_map[lvl_code_field].str.replace('.', '', regex=False)
    cod_map[lvl_code_field] = cod_map[lvl_code_field].str.replace('/', '', regex=False)

    rambam_onto_map = cod_map.merge(onto_set[['code_code', 'code']], left_on=lvl_code_field, right_on='code_code')
    rambam_onto_map.rename(columns={'CODE': 'inner', 'code': 'outer'}, inplace=True)

    rambam_onto_map_def = cod_map.merge(pd.DataFrame(onto_def), how='left', left_on=lvl_code_field, right_index=True).dropna()
    rambam_onto_map_def.rename(columns={'CODE': 'inner', 'desc': 'outer'}, inplace=True)

    rambam_onto_map = pd.concat([rambam_onto_map[['inner', 'outer']], rambam_onto_map_def[['inner', 'outer']]])
    rambam_onto_map.drop_duplicates(['inner', 'outer'], inplace=True)
    rambam_onto_map['typ'] = 'SET'
    return rambam_onto_map[['typ', 'inner', 'outer']]


def map_rambam_codes(onto, rambam_codes, onto_def_file, onto_set_file):
    onto_set = read_onto_set_dict(onto_set_file)
    onto_def = pd.read_csv(onto_def_file, sep='\t', names=['typ', 'medialid', 'desc'])
    onto_def = get_code_decs_map(onto_def)
    rb_sets_df = pd.DataFrame()
    for i in range(0, 4):
        map_rambam = map_rmabam_level(onto, rambam_codes, onto_def, onto_set, i)
        rb_sets_df = rb_sets_df.append(map_rambam)
        if onto == 'ICD9' or onto == 'SNMI':
            break

    return rb_sets_df


def map_shorter_codes(onto, rambam_codes, onto_def_file, onto_set_file):
    onto_set = read_onto_set_dict(onto_set_file)
    onto_def = pd.read_csv(onto_def_file, sep='\t', names=['typ', 'medialid', 'desc'])
    onto_def = get_code_decs_map(onto_def)
    rb_sets_df = pd.DataFrame()
    rambam_codes.rename(columns={'code': 'code0', 'desc': 'CODE'}, inplace=True)
    while(True):
        rambam_codes['code0'] = rambam_codes['code0'].str[:-1]
        map_rambam = map_rmabam_level(onto, rambam_codes, onto_def, onto_set, 0)
        if map_rambam.shape[0] == 0:
            break
        rambam_codes = rambam_codes[~rambam_codes['CODE'].isin(map_rambam['inner'])]
        rb_sets_df = rb_sets_df.append(map_rambam)
    return rb_sets_df