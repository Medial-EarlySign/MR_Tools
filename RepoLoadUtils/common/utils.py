import pandas as pd
import numpy as np
import os
import sys


def read_tsv(file_name, path, names=None, header=1, dtype=None):
    full_file = os.path.join(path, file_name)
    df = pd.read_csv(full_file, sep='\t', names=names, header=header, dtype=dtype)
    return df


def write_tsv(df, path, file_name, headers=False, mode='a'):
    if not(os.path.exists(path)):
        os.makedirs(path)
    full_file = os.path.join(path, file_name)
    df.to_csv(full_file, sep='\t', index=False, header=headers, mode=mode, line_terminator='\n')


def append_sort_write_tsv(df, path, file_name, all_columns, sort_by, headers=False):
    if not(os.path.exists(path)):
        os.makedirs(path)
    full_file = os.path.join(path, file_name)
    if os.path.isfile(full_file):
        file_df = pd.read_csv(full_file, sep='\t', names=all_columns, header=None, dtype=str)
        df = df.append(file_df)
    df.sort_values(by=sort_by, inplace=True)
    df[all_columns].to_csv(full_file, sep='\t', index=False, header=headers, mode='w', line_terminator='\n')


def write_tsv_fd(fd, df, path, file_name, headers=False):
    if not(os.path.exists(path)):
        os.makedirs(path)
    full_file = os.path.join(path, file_name)
    if fd is None:
        fd = open(full_file, mode='a', newline='\n')
    df.to_csv(fd, sep='\t', index=False, header=headers, mode='a', line_terminator='\n')
    return fd


def add_fisrt_line(first_line, file):
    with open(file, "r+", encoding="utf8", newline='\n') as f:
        a = f.read()
    with open(file, "w+", encoding="utf8", newline='\n') as f:
        f.write(first_line + a)


def read_first_line(file):
    with open(file) as f:
        first_line = f.readline()
    return first_line


def add_last_line(last_line, file):
    with open(file, "a+", encoding="utf8", newline='\n') as f:
        f.write(last_line)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_user():
    user_name = os.environ.get('USERNAME')
    if user_name is None:
        user_name = os.environ.get('USER')
        if 'internal' in user_name:
            user_name = user_name.split('-')[0]
    return user_name


def unix_path(pt):
    isUnixPath = pt.find('\\') == -1
    if isUnixPath:
        return pt
    else:
        res = ''
        if pt.startswith('\\\\nas1') or pt.startswith('\\\\nas3'):
            res = '/nas1'
            pt = pt.replace('\\\\nas1', '')
            pt = pt.replace('\\\\nas3', '')
        elif pt.startswith('C:\\Users\\'):
            res = os.environ['HOME']
            pt = pt.replace('C:\\Users\\', '')
            pt = pt[pt.find('\\'):]
        elif pt.startswith('H:\\'):
            res = os.path.join('/nas1/UsersData', get_user().lower())
            pt = pt.replace('H:', '')
        elif pt.startswith('W:\\'):
            res = '/nas1/Work'
            pt = pt.replace('W:', '')
        elif pt.startswith('T:\\'):
            res = '/nas1/Data'
            pt = pt.replace('T:', '')
        elif pt.startswith('U:\\'):
            res = '/nas1/UserData'
            pt = pt.replace('U:', '')
        elif pt.startswith('X:\\'):
            res = '/nas1/Temp'
            pt = pt.replace('X:', '')
        else:
            eprint('not support convertion "%s"' % pt)
            raise NameError('not supported')
        pt = pt.replace('\\', '/')
        res = res + pt
        return res


def fixOS(pt):
    isUnixPath = pt.find('\\') == -1
    if ((os.name != 'nt' and isUnixPath) or (os.name == 'nt' and not(isUnixPath))):
        return pt
    elif (os.name == 'nt'):
        if (pt.startswith('/nas1/Work') or pt.startswith('/server/Work')):
            res = 'W:\\'
            pt = pt.replace('/nas1/Work/', '').replace('/server/Work/', '')
            pt = pt.replace('/', '\\')
            res = res + pt
            return res
        res = 'C:\\USERS\\' + get_user()
        if (pt.startswith('/nas1') or pt.startswith('/server')):
            res = '\\\\nas3'
            pt = pt.replace('/nas1', '').replace('/server', '')
        pt = pt.replace('/', '\\')
        res= res + pt
        return res
    else:
        res = ''
        if pt.startswith('\\\\nas1') or pt.startswith('\\\\nas3') :
            res = '/nas1'
            pt = pt.replace('\\\\nas1', '')
            pt = pt.replace('\\\\nas3', '')
        elif pt.startswith('C:\\Users\\') :
            res = os.environ['HOME']
            pt = pt.replace('C:\\Users\\', '')
            pt = pt[ pt.find('\\'):]
        elif pt.startswith('H:\\'):
            res = os.path.join('/nas1/UsersData', get_user().lower() )
            pt = pt.replace('H:', '')
        elif pt.startswith('W:\\'):
            res = '/nas1/Work'
            pt = pt.replace('W:', '')
        elif pt.startswith('T:\\'):
            res = '/nas1/Data'
            pt = pt.replace('T:', '')
        elif pt.startswith('U:\\'):
            res = '/nas1/UserData'
            pt = pt.replace('U:', '')
        elif pt.startswith('X:\\'):
            res = '/nas1/Temp'
            pt = pt.replace('X:', '')
        else:
            eprint('not support convertion "%s"'%pt)
            raise NameError('not supported')
        pt = pt.replace('\\', '/')
        res= res + pt
        return res


def is_nan(num):
    return num != num


def to_float(value):
    try:
        flt = float(value)
        return flt
    except:
        return np.nan


def replace_spaces(val_ser):
    return val_ser.str.strip().str.replace(' ', '_').str.replace(',', '')


def code_desc_to_dict_df(df, dc_start, stack_cols):
    df = df.assign(defid=range(dc_start, dc_start + df.shape[0]))
    stack_cols.append('defid')
    to_stack = df[stack_cols].set_index('defid', drop=True)
    dict_df = to_stack.stack().to_frame()
    dict_df['defid'] = dict_df.index.get_level_values(0)
    dict_df.rename({0: 'code'}, axis=1, inplace=True)
    dict_df['def'] = 'DEF'
    return dict_df


def get_dict_set_df(repo_path, signal):
    sig_dicts = []
    dict_path = os.path.join(fixOS(repo_path), 'dicts')
    for f in os.listdir(dict_path):
        first_line = read_first_line(os.path.join(dict_path, f))
        if signal in first_line:
            sig_dicts.append(f)
    if len(sig_dicts) == 0:
        return pd.DataFrame()
    all_dicts = pd.DataFrame()
    for dct in sig_dicts:
        dict_df = pd.read_csv(os.path.join(dict_path, dct), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
        all_dicts = all_dicts.append(dict_df, sort=False)
    all_dicts.drop_duplicates(inplace=True)
    def_df = all_dicts[all_dicts['typ'] == 'DEF'].copy()
    def_df_map = def_df.set_index('desc')['codeid']

    set_df = all_dicts[all_dicts['typ'] == 'SET'].copy()
    set_df.rename(columns={'codeid': 'outer', 'desc': 'inner'}, inplace=True)
    set_df.loc[:, 'inner_code'] = set_df['inner'].map(def_df_map)
    def_df = def_df.append(set_df[['outer', 'inner_code']].rename(columns={'outer': 'desc', 'inner_code': 'codeid'}),
                           ignore_index=True, sort=False)
    while not set_df.empty:
        set_df = set_df[['outer', 'inner']].merge(set_df[['outer', 'inner']], how='left', left_on='inner',
                                                  right_on='outer')
        set_df = set_df[set_df['inner_y'].notnull()]
        set_df.loc[:, 'inner_code'] = set_df['inner_y'].map(def_df_map)
        def_df = def_df.append(set_df[['outer_x', 'inner_code']].rename(columns={'outer_x': 'desc', 'inner_code': 'codeid'}),
                               ignore_index=True)
        set_df.rename(columns={'outer_x': 'outer', 'inner_y': 'inner'}, inplace=True)

    return def_df[['codeid', 'desc']]


def get_dict_set_df_new(repo_path, signal):
    sig_dicts = []
    dict_path = os.path.join(fixOS(repo_path), 'dicts')
    for f in os.listdir(dict_path):
        first_line = read_first_line(os.path.join(dict_path, f))
        if signal in first_line:
            sig_dicts.append(f)
    if len(sig_dicts) == 0:
        return pd.DataFrame()
    # sig_dicts = ['dict.icd9dx', 'dict.set_icd9dx']
    print(sig_dicts)
    all_dicts = pd.DataFrame()
    for dct in sig_dicts:
        dict_df = pd.read_csv(os.path.join(dict_path, dct), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
        all_dicts = all_dicts.append(dict_df, sort=False)
    all_dicts.drop_duplicates(inplace=True)
    def_df = all_dicts[all_dicts['typ'] == 'DEF'].copy()
    def_df['codeid'] = def_df['codeid'].astype(int)
    def_df_map = def_df.set_index('desc')['codeid']
    def_df.loc[:, 'outer_code'] = def_df['codeid']
    def_df.rename(columns={'codeid': 'inner_code'}, inplace=True)

    set_df = all_dicts[all_dicts['typ'] == 'SET'].copy()
    # set_df.rename(columns={'codeid': 'outer', 'desc': 'inner'}, inplace=True)
    set_df.loc[:, 'inner_code'] = set_df['desc'].map(def_df_map)
    set_df.loc[:, 'outer_code'] = set_df['codeid'].map(def_df_map)
    def_df = def_df.append(set_df[['inner_code', 'outer_code']], ignore_index=True, sort=False)
    # print(def_df)
    while not set_df.empty:
        set_df = set_df[['outer_code', 'inner_code']].merge(set_df[['outer_code', 'inner_code']], how='left',
                                                            left_on='inner_code',
                                                            right_on='outer_code')
        print(set_df.shape)
        set_df = set_df[set_df['inner_code_y'].notnull()]
        print(set_df.shape)
        # print(set_df)
        # set_df.loc[:, 'inner_code'] = set_df['inner_code_y'].map(def_df_map)
        # set_df.rename(columns = {'inner_code_y': 'inner_code'}, inplace=True )
        # print(set_df)
        set_df.rename(columns={'outer_code_x': 'outer_code', 'inner_code_y': 'inner_code'}, inplace=True)
        def_df = def_df.append(set_df[['outer_code', 'inner_code']], ignore_index=True, sort=False)

    return def_df[['outer_code', 'inner_code']], all_dicts


def desc_to_code(repo_path, signal, descs):
    sig_dicts = []
    dict_path = os.path.join(fixOS(repo_path), 'dicts')
    for f in os.listdir(dict_path):
        first_line = read_first_line(os.path.join(dict_path, f))
        if signal in first_line:
            sig_dicts.append(f)
    if len(sig_dicts) == 0:
        return pd.DataFrame()
    # sig_dicts = ['dict.icd9dx', 'dict.set_icd9dx']
    all_dicts = pd.DataFrame()
    print(sig_dicts)
    for dct in sig_dicts:
        dict_df = pd.read_csv(os.path.join(dict_path, dct), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
        all_dicts = all_dicts.append(dict_df, sort=False)
    all_dicts.drop_duplicates(inplace=True)
    def_df = all_dicts[all_dicts['typ'] == 'DEF'].copy()
    codes = def_df[def_df['desc'].isin(descs)]
    return codes['codeid'].unique().tolist()
