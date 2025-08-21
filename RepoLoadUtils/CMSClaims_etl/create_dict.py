import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS, write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df


def create_county_dict(source_dir, dict_path):
    sec = 'FIPSCODE'
    dict_file = 'dict.county'
    dc_start = 1000
    map_df = pd.read_csv(os.path.join(source_dir, 'zip_county_map.txt'), usecols=[1, 3], sep='\t')
    map_df.drop_duplicates(inplace=True)
    dict_df = code_desc_to_dict_df(map_df, dc_start, ['county', 'FIPSCode'])
    cols = ['def', 'defid', 'code']
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(dict_df[cols], dict_path, dict_file)
    first_line = 'SECTION\t' + sec + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def create_state_dict(source_dir, dict_path):
    sec = 'SATTECODE'
    dict_file = 'dict.state'
    dc_start = 5000
    map_df = pd.read_csv(os.path.join(source_dir, 'state_id_map.txt'), sep='\t')
    map_df.drop_duplicates(subset='StatePostalCode', inplace=True)
    dict_df = code_desc_to_dict_df(map_df, dc_start, ['StatePostalCode', 'StateName', 'StateFIPSCode'])
    cols = ['def', 'defid', 'code']
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(dict_df[cols], dict_path, dict_file)
    first_line = 'SECTION\t' + sec + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


if __name__ == '__main__':
    cfg = Configuration()
    ext_folder = fixOS(cfg.data_external)
    output_folder = os.path.join(fixOS(cfg.work_path), 'rep_configs', 'dicts')
    create_state_dict(ext_folder, output_folder)
    create_county_dict(ext_folder, output_folder)
