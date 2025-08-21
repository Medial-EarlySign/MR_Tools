import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df


def create_gender_dict():
    sig = 'GENDER'
    cfg = Configuration()
    dict_path = os.path.join(fixOS(cfg.work_path), 'rep_configs', 'dicts')

    dict_file = 'dict.gender'
    dict_df = pd.DataFrame(data = [[1, 'M'], [2, 'F']], columns=['defid', 'value'])
    dict_df['def'] = 'DEF'
    cols = ['def', 'defid', 'value']
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(dict_df[cols], dict_path, dict_file)
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_reg_dict(sig, file_names):
    cfg = Configuration()
    dict_path = os.path.join(fixOS(cfg.work_path), 'rep_configs', 'dicts')
    data_path = fixOS(cfg.data_folder)
    dict_file = 'dict.' + sig
    all_dict_df = pd.DataFrame()
    for fl in file_names:
        full_file = os.path.join(data_path, fl)
        sht = 1 if 'GI' in fl else 0
        df = pd.read_excel(full_file, sheet_name=sht)
        df = df[['Dx_Code', 'Dx_Desc']].drop_duplicates()

        dc_start = 1000 * (sht+1)
        df['Dx_Desc'] = replace_spaces(df['Dx_Desc'])

        lists = df.groupby('Dx_Code')['Dx_Desc'].apply(list)
        lists = lists.apply(pd.Series).reset_index()
        dict_df = code_desc_to_dict_df(lists, dc_start, lists.columns.tolist())
        all_dict_df = all_dict_df.append(dict_df)

    cols = ['def', 'defid', 'code']
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(all_dict_df[cols], dict_path, dict_file)
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


if __name__ == '__main__':
    create_gender_dict()
    create_reg_dict('Cancer_Registry', ['colon.neoplasm.xlsx', 'GIBleed.xlsx'])
