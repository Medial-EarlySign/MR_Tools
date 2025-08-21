import os
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name, rc_map
from load_patient import get_id2nr_map
from split_ahd import save_ahd_readcodes


def get_unique_outfile(rc):
    lower = [l for l in rc if l.islower()]
    file_name = rc
    if len(lower) > 0:
        file_name = file_name + '-' + ''.join(lower)
    return file_name


def save_one_rc(rc, df_dict, path_to_save):
    file_name = get_unique_outfile(rc)
    write_tsv(df_dict[rc], path_to_save, file_name)
    #del df_dict[rc]


def save_medical_rc_parallel(df_dict, path_to_save):
    rcs = df_dict.keys()
    print('    Files to write: ' + str(len(rcs)))
    for rc in rcs:
        save_one_rc(rc, df_dict, path_to_save)


def one_rc_to_mem(rc, vals_df, df_dict):
    cols = ['medialid', 'eventdate', 'medcode', 'nhsspec', 'source']
    rc_df = vals_df[vals_df['medcode'].str.contains(rc, case=True, regex=False)]
    if rc in df_dict.keys():
        df_dict[rc] = df_dict[rc].append(rc_df[cols])
    else:
        df_dict[rc] = rc_df[cols]


def medical_rc_to_mem(vals_df, df_dict):
    cols = ['medialid', 'eventdate', 'medcode', 'nhsspec', 'source']
    for medcode, df_medcode in vals_df.groupby('medcode'):
        if medcode in df_dict.keys():
            df_dict[medcode] = df_dict[medcode].append(df_medcode[cols])
        else:
            df_dict[medcode] = df_medcode[cols]
    return vals_df.shape[0]


def load_medical():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    final_path = os.path.join(out_folder, 'FinalSignals')

    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')

    thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)
    thin_map = thin_map[(thin_map['signal'].str.contains('RC')) & (thin_map['source_file'] == 'medical')]
    rc_signals = thin_map['signal'].unique()

    medical_fld = os.path.join(out_folder, 'medical_files_temp')
    stat_df = pd.DataFrame()
    id2nr = get_id2nr_map()
    in_file_names = list(filter(lambda f: f.startswith('medical.'), os.listdir(data_path)))
    start_file = 'medical.a1111'
    eprint("about to process", len(in_file_names), "files")
    df_dict = {}
    cnt = 0
    for in_file_name in in_file_names:
        cnt = cnt + 1
        pracid = in_file_name[-5:]
        print(str(cnt) + ") reading from " + in_file_name)
        if in_file_name < start_file:
            print(in_file_name + ' already loaded')
            continue

        stats = {'prac': pracid}
        time1 = time.time()
        med_df = read_fwf('medical', data_path, in_file_name)
        time2 = time.time()
        print('    load medical file ' + str(med_df.shape[0]) + ' records in ' + str(time2 - time1))
        med_df['combid'] = pracid + med_df['patid']
        med_df['medialid'] = med_df['combid'].map(id2nr)
        stats["read"] = med_df.shape[0]
        stats["invalid_medflag"] = med_df[~med_df['medflag'].isin(['R', 'S'])].shape[0]
        stats["unknown_id"] = med_df[med_df['medialid'].isnull()].shape[0]
        med_df = med_df[(med_df['medflag'].isin(['R', 'S'])) & (med_df['medialid'].notnull())]
        med_df['medialid'] = med_df['medialid'].astype(int)
        med_df.sort_values(by=['combid', 'eventdate'], inplace=True)

        # med_df['saved'] = save_medical_rc_parallel(med_df, medical_fld)
        med_df['saved'] = medical_rc_to_mem(med_df, df_dict)
        save_ahd_readcodes(rc_signals, thin_map, med_df, final_path, in_file_name)
        time3 = time.time()
        print('   process medical file in ' + str(time3 - time2))
        if (cnt % 50) == 0:
            print(' going to save to files')
            save_medical_rc_parallel(df_dict, medical_fld)
            print('   saving medical files ' + str(time.time() - time3))
            #del df_dict
            df_dict = {}
        stat_df = stat_df.append(stats, ignore_index=True)
    print(' going to save the rest of the files')
    save_medical_rc_parallel(df_dict, medical_fld)
    write_tsv(stat_df, medical_fld, 'medical_split_stats.log', headers=True)


if __name__ == '__main__':
    load_medical()
