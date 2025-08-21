import pandas as pd
import os
import sys

from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces, is_nan
from staging_config import MayoLabs, MayoDemographic
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files, remove_errors
from train_signal import create_train_signal


def cbc_to_files(mayo_def, filter):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    myo_map = pd.read_csv(os.path.join(code_folder, 'mayo_signal_map.csv'), sep='\t')
    lab_chart_cond = (myo_map['source'] == filter)
    # lab_chart_cond = ((myo_map['source'] == filter) & (myo_map['signal'] == 'MPV'))
    map_numeric = myo_map[(myo_map['type'] == 'numeric') & lab_chart_cond]
    print(map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    if os.path.exists(os.path.join(code_folder, 'mixture_units_cfg.txt')):
        special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    else:
        special_factors_signals = None
    numeric_to_files(mayo_def, map_numeric, unit_mult, special_factors_signals, id2nr, out_folder)


def demographic_stage_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    kp_def = MayoDemographic()
    id2nr = get_id2nr_map()
    demo_map = pd.read_csv(os.path.join(code_folder, 'mayo_signal_map.csv'), sep='\t')
    demo_cond = (demo_map['source'] == 'mayodemographic')
    # demo_cond = (demo_map['source'] == 'mayodemographic') & (demo_map['signal'] == 'DEATH')
    kp_map_demo = demo_map[demo_cond]
    print(kp_map_demo)
    demographic_to_files(kp_def, kp_map_demo, id2nr, out_folder)


def registry_load_files(reg, file_names):
    sig = reg
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr_map = get_id2nr_map()
    all_df = pd.DataFrame()
    for fl in file_names:
        full_file = os.path.join(data_path, fl)
        sht = 1 if 'GI' in fl else 0
        colon_df = pd.read_excel(full_file, sheet_name=sht)
        colon_df['medialid'] = colon_df['Clinic'].astype(str).map(id2nr_map)
        colon_df = colon_df[colon_df['medialid'].notnull()]
        colon_df['date'] = pd.to_datetime(colon_df['Dx_Date'], format='%m/%d/%Y %H:%M').dt.date
        colon_df['id_int'] = colon_df['medialid'].astype(int)
        all_df = all_df.append(colon_df, sort=True)
    all_df.sort_values(by=['id_int', 'date'], inplace=True)
    all_df['signal'] = sig
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(all_df[['medialid', 'signal', 'date', 'Dx_Code']], out_folder, sig)


if __name__ == '__main__':
    cbc_to_files(MayoLabs(), 'mayolabs')
    #demographic_stage_to_files()
    #registry_load_files('Cancer_Registry', ['colon.neoplasm.xlsx', 'GIBleed.xlsx'])
    #create_train_signal(Configuration())


