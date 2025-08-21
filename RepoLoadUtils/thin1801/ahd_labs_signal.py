import os
import traceback
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv
from load_patient import get_id2nr_map


def load_ahd_labs():
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = fixOS(cfg.work_path)
    final_path = os.path.join(out_folder, 'FinalSignals')
    if not(os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not(os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not(os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not(os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')
    stats_name = os.path.join(out_folder, 'Stats')
    ahd_fld = os.path.join(out_folder, 'ahd_files3')
    thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)
    # convert all value_field to lists (even for length of one) for simpler code
    thin_map = thin_map[thin_map['source_file'] == 'ahd']
    mapped_rcs = thin_map['readcode'].unique()
    mapped_ahdcodes = thin_map['ahdcode'].unique()

    ahd_lookup = read_fwf('AHDlookups', raw_path)
    lookups = ahd_lookup['lookup'].unique()
    in_file_names = list(filter(lambda f: f.startswith('ahd.'), os.listdir(data_path)))
    prf = 'j'
    in_file_names = [x for x in in_file_names if 'ahd.' + prf in x]
    # in_file_names = ['ahd.g9974']
    start_file = 'ahd.a1111'
    stat_df = pd.DataFrame()
    id2nr = get_id2nr_map()
    cols = ['medialid', 'sig', 'eventdate', 'medcode', 'data2', 'source']
    eprint("about to process", len(in_file_names), "files")
    cnt = 0
    sig = 'Labs'
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
        print('    load ahd file ' + str(ahd_df.shape[0]) + ' records in ' + str(time2 - time1))
        ahd_df = ahd_df[ahd_df['medcode'].notnull()]
        labs_df = ahd_df[(~ahd_df['medcode'].isin(mapped_rcs)) &
                         (~ahd_df['ahdcode'].isin(mapped_ahdcodes)) &
                         (ahd_df['data3'].isin(lookups))]
        del ahd_df
        labs_df['numeric'] = pd.to_numeric(labs_df['data2'], errors='coerce')
        labs_df = labs_df[labs_df['numeric'].notnull()]

        labs_df['combid'] = pracid + labs_df['patid']
        labs_df['medialid'] = labs_df['combid'].map(id2nr)
        labs_df['source'] = in_file_name
        try:
            # Count and remove rows with bad status and Unknown pids
            stats["read"] = labs_df.shape[0]
            stats["invalid_ahdflag"] = labs_df[labs_df['ahdflag'] != 'Y'].shape[0]
            stats["unknown_id"] = labs_df[labs_df['medialid'].isnull()].shape[0]
            labs_df = labs_df[(labs_df['ahdflag'] == 'Y') & (labs_df['medialid'].notnull())]
            labs_df['medialid'] = labs_df['medialid'].astype(int)
            labs_df['sig'] = sig
            time3 = time.time()
            print('   merged process ahd file in ' + str(time3 - time2))
            write_tsv(labs_df[cols], final_path, sig+'_'+prf)
            print('   process ahd file in ' + str(time.time() - time3))
            stat_df = stat_df.append(stats, ignore_index=True)
        except:
            eprint('Error In File %s' % in_file_name)
            traceback.print_exc()
            raise

    write_tsv(stat_df, stats_name, prf+'_ahd_labs_stats.log', headers=True)


def sort_outputs():
    cfg = Configuration()
    data_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    final_path = os.path.join(out_folder, 'FinalSignals')
    labs_file_names = list(filter(lambda f: f.startswith('Labs_'), os.listdir(final_path)))
    for f in labs_file_names:
        full_file = os.path.join(final_path, f)
        print('Raeding file ' + f)
        df = pd.read_csv(full_file, sep='\t', names=['pid', 'sig', 'date', 'rc', 'res', 'source'], header=None)
        print('sorting file ' + f)
        df.sort_values(by=['pid', 'date'], inplace=True)
        print('Saving file ' + f)
        df.to_csv(full_file, sep='\t', index=False, header=False, mode='w', line_terminator='\n')
        print('Done file ' + f)


if __name__ == '__main__':
    #load_ahd_labs()
    sort_outputs()
