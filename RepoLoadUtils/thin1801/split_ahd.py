import os
import re
import traceback
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv
from load_patient import get_id2nr_map


#  get different file name for RC with lower letter as Windows FS is case insensative
def get_unique_outfile(rc, ahdcode):
    lower = [l for l in rc if l.islower()]
    file_name = rc + '-' + ahdcode
    if len(lower) > 0:
        file_name = file_name + '-' + ''.join(lower)
    return file_name


def save_one_rc(codes_tup, vals_df, path_to_save):
    cols = ['medialid', 'eventdate', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'full_ahd_name']
    test_dt = vals_df.copy()
    test_dt['full_ahd_name'] = codes_tup[0] + '-' + str(codes_tup[1])
    out_file = get_unique_outfile(codes_tup[0], str(codes_tup[1]))
    write_tsv(test_dt[cols], path_to_save, out_file)
    del test_dt


def save_ahd_readcodes(signals, thin_map, rc_df, path_to_save, source_file):
    cols = ['medialid', 'sig', 'eventdate', 'medcode']
    rc_df['eventdate'] = rc_df['eventdate'].astype(int)
    rc_df = rc_df[rc_df['eventdate'] >= 19000101]
    prac_pref = source_file.split('.')[1][0]
    for sig in signals:
        sig_maps = thin_map[thin_map['signal'] == sig]
        for _, map1 in sig_maps.iterrows():
            sig_df = rc_df[rc_df['medcode'].str.contains(map1['regex'])].copy()
            sig_df['sig'] = sig
            sig_df['file'] = source_file
            sig_df.sort_values(['medialid', 'eventdate'], inplace=True)
            if sig == 'RC' or sig == 'RC_Diagnostic_Procedures':  # Very big files
                write_tsv(sig_df[cols], path_to_save, sig + '_' + prac_pref)
            else:
                write_tsv(sig_df[cols], path_to_save, sig)
    return


def ahd_rc_to_mem(vals_df, path_to_save, df_dict):
    cols = ['medialid', 'eventdate', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6']
    for medcode, df_medcode in vals_df.groupby(by=['medcode', 'ahdcode']):
        if medcode in df_dict.keys():
            df_dict[medcode] = df_dict[medcode].append(df_medcode[cols])
        else:
            df_dict[medcode] = df_medcode[cols]
        if df_dict[medcode].shape[0] >= 1000000:
            to_svae_df = df_dict.pop(medcode)
            print(' going to save ' + str(to_svae_df.shape[0]) + ' recoreds to file ' + str(medcode))
            time3 = time.time()
            save_one_rc(medcode, to_svae_df, path_to_save)
            print(' saved ' + str(time.time() - time3))
    return vals_df.shape[0]


def save_remains(df_dict, path_to_save):
    for k, v in df_dict.items():
        save_one_rc(k, v, path_to_save)


# regex is readcode to search for in ahd.*
def load_ahd_files(signalRegex='.'):
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = fixOS(cfg.work_path)
    final_path = os.path.join(out_folder, 'FinalSignals_ahd')
    if not(os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not(os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not(os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not(os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')
    stats_name = os.path.join(out_folder, 'Stats')
    ahd_fld = os.path.join(out_folder, 'ahd_files_tmp')
    thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)
    # convert all value_field to lists (even for length of one) for simpler code
    thin_map = thin_map[(thin_map['signal'].str.contains('RC')) & (thin_map['source_file'] == 'ahd')]
    rc_signals = thin_map['signal'].unique()

    sigRe = re.compile(signalRegex)
    in_file_names = list(filter(lambda f: f.startswith('ahd.'), os.listdir(data_path)))
    # in_file_names = [x for x in in_file_names if 'ahd.j' in x]
    #in_file_names = ['ahd.a6702']
    start_file = 'ahd.a1111'
    stat_df = pd.DataFrame()
    id2nr = get_id2nr_map()
    data_cols = ['data1', 'data2', 'data3', 'data4', 'data5', 'data6']
    eprint("about to process", len(in_file_names), "files")
    cnt = 0
    df_dict = {}
    for in_file_name in in_file_names:
        cnt = cnt+1
        pracid = in_file_name[-5:]
        print(str(cnt) + ") reading from " + in_file_name)
        if in_file_name < start_file:
            print(in_file_name + ' already loaded')
            continue
        stats = {'prac': pracid}
        time1 = time.time()
        ahd_df = read_fwf('ahd', data_path, in_file_name)
        time2 = time.time()
        # next 2 line to handle corrupted lines
        ahd_df = ahd_df[ahd_df['medcode'].notnull()]
        ahd_df['ahdcode'] = ahd_df['ahdcode'].astype(int)
        print('    load ahd file ' + str(ahd_df.shape[0]) + ' records in ' + str(time2 - time1))
        # ahd_df = ahd_df[ahd_df['medcode'].str.contains(sigRe)]
        ahd_df['combid'] = pracid + ahd_df['patid']
        ahd_df['medialid'] = ahd_df['combid'].map(id2nr)
        try:
            # Count and remove rows with bad status and Unknown pids
            stats["read"] = ahd_df.shape[0]
            stats["invalid_ahdflag"] = ahd_df[ahd_df['ahdflag'] != 'Y'].shape[0]
            stats["unknown_id"] = ahd_df[ahd_df['medialid'].isnull()].shape[0]
            ahd_df = ahd_df[(ahd_df['ahdflag'] == 'Y') & (ahd_df['medialid'].notnull())]
            ahd_df['medialid'] = ahd_df['medialid'].astype(int)
            # Count and remove rows with no data
            # stats["no_data"] = ahd_df[ahd_df[data_cols].isnull().all(1)].shape[0]
            # ahd_df = ahd_df[ahd_df[data_cols].notnull().any(1)]

            time3 = time.time()
            print('   merged process ahd file in ' + str(time3 - time2))
            stats["wrote_readcodes"] = ahd_rc_to_mem(ahd_df, ahd_fld, df_dict)
            save_ahd_readcodes(rc_signals, thin_map, ahd_df, final_path, in_file_name)
            print('   process ahd file in ' + str(time.time() - time3))
            stat_df = stat_df.append(stats, ignore_index=True)
        except:
            eprint('Error In File %s' % in_file_name)
            traceback.print_exc()
            raise

        del ahd_df
    save_remains(df_dict, ahd_fld)
    write_tsv(stat_df, stats_name, 'ahd_split_stats.log', headers=True)


if __name__ == '__main__':
    load_ahd_files('.')
