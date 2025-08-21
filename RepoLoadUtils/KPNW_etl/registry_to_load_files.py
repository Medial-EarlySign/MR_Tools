import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv, read_first_line, get_dict_set_df
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


# def get_dict_set_df(cfg, signal):
#     sig_dicts = []
#     dict_path = os.path.join(fixOS(cfg.repo_folder), 'dicts')
#     for f in os.listdir(dict_path):
#         first_line = read_first_line(os.path.join(dict_path, f))
#         if signal in first_line:
#             sig_dicts.append(f)
#     if len(sig_dicts) == 0:
#         return pd.DataFrame()
#     all_dicts = pd.DataFrame()
#     for dct in sig_dicts:
#         dict_df = pd.read_csv(os.path.join(dict_path, dct), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
#         all_dicts = all_dicts.append(dict_df, sort=False)
#
#     def_df = all_dicts[all_dicts['typ'] == 'DEF'].copy()
#     def_df_map = def_df.set_index('desc')['codeid']
#
#     set_df = all_dicts[all_dicts['typ'] == 'SET'].copy()
#     set_df.rename(columns={'codeid': 'outer', 'desc': 'inner'}, inplace=True)
#     set_df.loc[:, 'inner_code'] = set_df['inner'].map(def_df_map)
#     def_df = def_df.append(set_df[['outer', 'inner_code']].rename(columns={'outer': 'desc', 'inner_code': 'codeid'}),
#                            ignore_index=True, sort=False)
#
#     # while not set_df.empty:
#     #     set_df = set_df[['outer', 'inner']].merge(set_df[['outer', 'inner']], how='left', left_on='inner',
#     #                                               right_on='outer')
#     #     set_df = set_df[set_df['inner_y'].notnull()]
#     #     set_df.loc[:, 'inner_code'] = set_df['inner_y'].map(def_df_map)
#     #     def_df = def_df.append(set_df[['outer_x', 'inner_code']].rename(columns={'outer_x': 'desc', 'inner_code': 'codeid'}),
#     #                            ignore_index=True)
#     #     set_df.rename(columns={'outer_x': 'outer', 'inner_y': 'inner'}, inplace=True)
#
#     return def_df[['codeid', 'desc']]
#

def get_dict_df(cfg, dictionery_file):
    if not dictionery_file:
        return pd.DataFrame()
    reg_path = fixOS(cfg.repo_folder)
    dict_path = os.path.join(reg_path, 'dicts')
    dict_df = pd.read_csv(os.path.join(dict_path, dictionery_file), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
    dict_df = dict_df[dict_df['typ'] == 'DEF']
    return dict_df[['codeid', 'desc']]


def get_signal(rep, signal):
    sig_df = rep.get_sig(signal, translate=False)
    assert ('time0' in sig_df.columns)
    sig_df.rename(columns={'time0': 'date'}, inplace=True)
    # if 'date' not in sig_df.columns:
    #     if 'date_start' in sig_df.columns.tolist():
    #         sig_df.rename(columns={'date_start': 'date'}, inplace=True)
    #     else:
    #         assert(signal == 'DEATH')
    #         sig_df.rename(columns={'time': 'date'}, inplace=True)
    return sig_df


def get_reg_list(cfg, reg_list):
    if not reg_list:
        return pd.DataFrame()
    code_folder = fixOS(cfg.code_folder)
    list_file = os.path.join(code_folder, 'registries', reg_list)
    reg_list_df = pd.read_csv(list_file, usecols=[0], names=['desc'])
    return reg_list_df


def merge_sig_dict_reg(sig_df, dict_df, reg_list):
    if dict_df.empty or reg_list.empty:
        print('dict or reg list are None')
        return sig_df
    relevant_codes = reg_list.merge(dict_df, how='left', on='desc')
    reg = sig_df[sig_df['val0'].isin(relevant_codes['codeid'].values)].copy()
    return reg


def to_loading_file(cfg, rep, sig, signals, reg_lists, grades):
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    kp_rep = fixOS(cfg.repo)
    rep.read_all(kp_rep, [], ['GENDER'])
    print(med.cerr())
    registry_df_list = []
    for signal, reg_list, grade in zip(signals, reg_lists, grades):
        print(signal, reg_list)
        sig_df = get_signal(rep, signal)
        dict_df = get_dict_set_df(cfg.repo_folder, signal)
        reg_list = get_reg_list(cfg, reg_list)
        reg = merge_sig_dict_reg(sig_df, dict_df, reg_list)
        reg['value'] = grade
        print(reg.shape)
        registry_df_list.append(reg[['pid', 'date', 'value']])

    all_registrys_df = pd.concat(registry_df_list, ignore_index=True, sort=True)
    all_registrys_df.sort_values(by=['pid', 'date', 'value'], inplace=True)

    all_registrys_df.drop_duplicates(subset=['pid', 'date'], inplace=True, keep='first')
    if sig == 'COVID_REG':
        all_registrys_df.drop_duplicates(subset=['pid'], inplace=True, keep='first')
    print(all_registrys_df.shape)
    all_registrys_df['signal'] = sig
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(all_registrys_df[['pid', 'signal', 'date', 'value']], out_folder, sig)


def flu_vacc(cfg, rep):
    sig = 'Vaccination_flu'
    signals = ['Vaccination', 'DIAGNOSIS', 'Drug']
    reg_lists = ['flu.Vaccination.list', 'flu.Vaccination_Diagnaosis.list', 'flu.Vaccination.drug.list']
    grades = [1, 1, 1, 1]
    to_loading_file(cfg, rep, sig, signals, reg_lists, grades)


def complications(cfg, rep):
    sig = 'Complications'
    signals = ['DEATH', 'ADMISSION', 'DIAGNOSIS']
    reg_lists = [None, 'flu_complications_grade_2_admissions', 'flu_complications_grade_3']
    grades = [1, 2, 3]
    to_loading_file(cfg, rep, sig, signals, reg_lists, grades)


def flu_reg(cfg, rep):
    sig = 'FLU_REG'
    signals = ['DIAGNOSIS', 'DIAGNOSIS', 'DIAGNOSIS', 'Drug']
    reg_lists = ['flu_grade_1', 'flu_grade_2', 'flu_grade_3', 'flu.drug.list']
    grades = [1, 2, 3, 2]
    to_loading_file(cfg, rep, sig, signals, reg_lists, grades)


def covid_reg(cfg, rep):
    sig = 'COVID_REG'
    signals = ['DIAGNOSIS', 'COVID19_TEST']
    reg_lists = ['covid_diagnosis.list', 'covid_test_positive.list']
    grades = [1, 1]
    to_loading_file(cfg, rep, sig, signals, reg_lists, grades)


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    flu_vacc(cfg, rep)
    complications(cfg, rep)
    flu_reg(cfg, rep)
    covid_reg(cfg, rep)

