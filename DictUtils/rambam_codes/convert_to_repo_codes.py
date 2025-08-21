import pandas as pd

RAMBAM_DIR = 'dicts'
rambam_diag_dict_file = RAMBAM_DIR + '\\dict.diagnoses'
rambam_proc_dict_file = RAMBAM_DIR + '\\dict.procedures'
ido_diag_dict_file = 'W:\\CancerData\\Repositories\\Rambam\\rambam_nov2018\\dicts\\dict.diagnosiscode'
ido_proc_dict_file = 'W:\\CancerData\\Repositories\\Rambam\\rambam_nov2018\\dicts\\dict.procedurecode'

ido_diag_dict_file_mrg = 'W:\\CancerData\\Repositories\\Rambam\\rambam_nov2018\\dicts\\dict.diagnosiscode_mrg'


def add_fisrt_line(first_line, file):
    with open(file, "r+", encoding="utf8") as f:
        a = f.read()
    with open(file, "w+", encoding="utf8") as f:
        f.write(first_line + a)


def read_and_merge(old_f, new_f, sec):
    new_dict = pd.read_csv(new_f, sep='\t', names=['typ', 'medialid', 'desc'], header=0)
    old_dict = pd.read_csv(old_f,  sep='\t', names=['typ', 'medialid', 'desc'], header=0)

    new_dict['list'] = new_dict['desc'].str.split(':')
    new_dict['code'] = new_dict.apply(lambda row: row['list'][1], axis=1)
    new_dict.drop('list', axis=1, inplace=True)

    if sec == 'DIAGNOSIS':
        old_dict['desc_len'] = old_dict['desc'].str.len()
        old_dict.sort_values(['medialid', 'desc_len'], ascending=[True, True], inplace=True)
        old_dict.drop_duplicates('medialid', inplace=True)
    else:
        old_dict = old_dict[old_dict['desc'].notnull()]
        old_dict = old_dict[old_dict['desc'].str.contains('PROC_ID')]
    old_dict['list'] = old_dict['desc'].str.split(':')
    old_dict['code'] = old_dict.apply(lambda row: row['list'][1], axis=1)
    old_dict.drop('list', axis=1, inplace=True)

    mrgd = new_dict.merge(old_dict, how='left', on='code')
    idmap = mrgd[['medialid_x', 'medialid_y']].drop_duplicates().set_index('medialid_x')['medialid_y']
    new_dict['medialid'] = new_dict['medialid'].map(idmap)

    mrgd_dict = pd.concat([new_dict[['typ', 'medialid', 'desc']], old_dict[['typ', 'medialid', 'desc']]])
    mrgd_dict.sort_values(['medialid', 'desc'], inplace=True)

    mrgd_dict.to_csv(old_f, index=False, header=False, sep='\t')
    first_line = 'SECTION' + '\t' + sec + '\n'
    add_fisrt_line(first_line, old_f)


if __name__ == '__main__':
    read_and_merge(ido_diag_dict_file, rambam_diag_dict_file, 'DIAGNOSIS')
    read_and_merge(ido_proc_dict_file, rambam_proc_dict_file, 'PROCEDURE')
