import os
import re
import pandas as pd
import traceback
from Configuration import Configuration
from const_and_utils import write_tsv, eprint, fixOS, read_tsv, read_fwf
import time
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))

from staging_config import ThinReadcodes
from generate_id2nr import get_id2nr_map
from tqdm import tqdm, trange
import regex as re

import argparse
import time

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_close_rc(rc, all_codes):
    if rc in all_codes['code'].values:
        return rc
    rc_list = []
    for i in range(len(rc), 1, -1):
        if rc[:i] in all_codes['short_code'].values:
            rc_list = list(all_codes[all_codes['short_code'] == rc[:i]]['code'].values)
            break
    if len(rc_list) > 0:
        if len(rc_list) == 1:
            return rc_list[0]
        # need to find the best match--> 00 in the end
        zerorc = [x for x in rc_list if x[-2:] == '00']
        assert len(zerorc) == 1, rc + ' MISSING 00 MATCH'
        print(rc + ' :: Returning the close one with 00 as the end: ' + zerorc[0])
        return zerorc[0]
    return None

def fix_cancer_eventdate(pid_df):
    if 'cancer' not in pid_df['status'].str.lower().values:
        return pid_df
    if 'anc' not in pid_df['status'].values and 'morph' not in pid_df['status'].values:
        return pid_df
    # there status == cancer and status in ["anc", "morph"] - check if need to update cancer date
    try:
        pid_df.sort_values('eventdate_ts', inplace=True)
        pid_df['timediff'] = (pid_df['eventdate_ts'] - pid_df['eventdate_ts'].shift(1)).astype('timedelta64[D]')

        pid_df['prev'] = pid_df.shift(1)['status'].str.lower.isin(['morph', 'anc'])
        pid_df['tofix'] = (pid_df['status'].str.lower.contains('cancer')) & (pid_df['prev']) & (pid_df['timediff'] < 62)
        pid_df['eventdate'] = pid_df['eventdate'].where(~pid_df['tofix'], pid_df['eventdate'].shift(1))
        pid_df['to_drop'] = pid_df['tofix'].shift(-1)
        pid_df.drop(pid_df[pid_df['to_drop'] == True].index, inplace=True)
    except:
        eprint('Error por pid %s' % pid_df.iloc[0]['medialid'])
        traceback.print_exc()
        raise

    return pid_df

def translate_cancer_types(stat, typef, organ, translate_cancer_types_table):
    if type(stat) is not str:
        print('stat is not str stat = ' + str(stat) + 'typef = ' + str(typef) + ' organ = ' + str(organ))
        return ''
    if 'cancer' not in stat.lower() or typef == 'na':
        return stat + ',' + typef + ',' + organ

    in_tuple = (stat, typef, organ)
    for _, r in translate_cancer_types_table.iterrows():
        m = [re.match(r["in"][i], in_tuple[i], re.IGNORECASE) for i in range(len(in_tuple))]
        if all(m):
            return str(r["out"][0]) + ',' + str(r["out"][1]) + ',' + str(r["out"][2])
    return stat + ',' + typef + ',' + organ

def save_registry(rc_df, cancer_types_df, path, index):

    if rc_df.shape[0] == 0:
        return
    rc_df['eventdate_ts'] = pd.to_datetime(rc_df['eventdate'].astype(str), format='%Y%m%d', errors='coerce')
    pids = rc_df['medialid'].unique()
    print(' going over ' + str(len(pids)) + ' pids')
    fixed_df = pd.DataFrame()
    time1 = time.time()
    for pid, pid_df in rc_df.groupby('medialid'):
        fixed_df = fixed_df.append(fix_cancer_eventdate(pid_df), ignore_index=True)
    time2 = time.time()
    print('   fixed cancer_eventdate for ' + str(len(pids)) + ' patients in ' + str(time2 - time1))
    fixed_df['out_field'] = fixed_df.apply(lambda x: translate_cancer_types(x['status'],
                                                                            x['type_field'],
                                                                            x['organ'],
                                                                            cancer_types_df[['in', 'out']]), axis=1)
    if fixed_df[fixed_df['out_field'] == ''].shape[0] > 0:
        print('   Empty fields count = ' + str(fixed_df[fixed_df['out_field'] == ''].shape[0]))
    print('   build out tuples in ' + str(time.time() - time2))
    fixed_df = fixed_df[fixed_df['out_field'] != '']
    fixed_df['sig'] = 'Cancer_Location'
    fixed_df.sort_values(by=['medialid', 'eventdate'], inplace=True)
    write_tsv(fixed_df[['medialid', 'sig', 'eventdate', 'out_field']], path, f'Cancer_Location_{index}')

def codes_to_cancer_location(stage_def,merge_close_file,index):

    start_time = time.time()

    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    id2nr_map = get_id2nr_map()
    if not (os.path.exists(raw_path) and os.path.exists(out_folder) and os.path.exists(code_folder)):
        raise NameError(f'At least one of {raw_path} , {out_folder} and {code_folder} does not exist')

    final_path = os.path.join(out_folder, 'FinalSignals')

    ############
    #cancer_types_df = read_tsv('translate_cancer_types.txt', code_folder,
    #                           names=['status_in', 'type_in', 'organ_in', 'status_out', 'type_out', 'organ_out'])
    #cancer_types_df['in'] = cancer_types_df.apply(lambda x: (x['status_in'], x['type_in'], x['organ_in']), axis=1)
    #cancer_types_df['out'] = cancer_types_df.apply(lambda x: (x['status_out'], x['type_out'], x['organ_out']),axis=1)
    #eprint(f'Read translation table of {len(cancer_types_df)} lines')

    ############
    if (merge_close_file is not None and os.path.exists(merge_close_file)):
        merge_close = pd.read_csv(merge_close_file)
        eprint(f'Read merge_close table with {len(merge_close)} lines')
    else:
        codes_2_details_df = read_tsv('thin_cancer_medcodes_20190212.txt', code_folder, header=0,
                                      names=['code', 'nrec', 'npat', 'desc', 'comment', 'status', 'type_field',
                                             'organ'])
        codes_2_details_df['short_code'] = codes_2_details_df['code'].str[:5].str.replace('.', '')
        eprint(f'Read cancer medcodes table of {len(codes_2_details_df)} lines')

        ############
        codes = codes_2_details_df['code'].unique()
        signal_df = pd.DataFrame()
        read_codes = read_fwf('Readcodes', raw_path)
        read_codes['close_rc'] = read_codes['medcode'].apply(
            lambda x: get_close_rc(x, codes_2_details_df[['short_code', 'code']]))
        eprint(f'Read Readcodes table of {len(read_codes)} lines')

        ############
        merge_close = read_codes.merge(codes_2_details_df, left_on='close_rc', right_on='code')
        if (merge_close_file is not None):
            merge_close.to_csv(merge_close_file)

    rcs = merge_close['medcode'].unique()
    eprint('Found ' + str(len(rcs)) + ' Readcodes')
    current_time = time.time()
    eprint(f'Preparation time = {current_time-start_time}')

    ############
    start_time = time.time()
    file_name = os.path.join(final_path,f'RC_{index}')
    eprint(f'Working on file : {file_name}')

    rc = pd.read_csv(file_name, header=None, sep='\t', names=['medialid', 'rc', 'eventdate', 'medcode', 'source'])
    eprint(f'Read {len(rc)} lines')
    current_time = time.time()
    eprint(f'Read time = {current_time-start_time}')

    start_time = time.time()
    crc = rc.loc[rc.medcode.isin(rcs)]
    eprint(f'Found {len(crc)} cancer related lines')
    reg_df = crc[['medialid', 'eventdate', 'medcode']].merge(merge_close, how='left', on='medcode')

    outFile = os.path.join(final_path,f'Cancer_Location_{index}')
    reg_df.to_csv(outFile)
    #save_registry(reg_df, cancer_types_df, final_path,index)

    current_time = time.time()
    eprint(f'Registry time = {current_time-start_time}')

    ############
    '''
    RC_files = [file for file in os.listdir(final_path) if re.match(r'RC_\d+',file)]
    eprint(f'Working on {len(RC_files)} RC_ files')

    for idx,name in enumerate(RC_files):
        file_name = os.path.join(final_path,name)
        eprint(f'Working on file {idx}/{len(RC_files)} : {file_name}')

        rc = pd.read_csv(file_name,header=None,sep='\t',names=['medialid','rc','eventdate','medcode','source'])
        eprint(f'Read {len(rc)} lines')
        crc = rc.loc[rc.medcode.isin(rcs)]
        eprint(f'Found {len(crc)} cancer related lines')
        reg_df = crc[['medialid', 'eventdate', 'medcode']].merge(merge_close, how='left', on='medcode')
        save_registry(reg_df, cancer_types_df, final_path)

    # Re-read and sort
    cols = ['medialid', 'sig', 'eventdate', 'val']
    al_file = read_tsv('Cancer_Location', final_path, names=cols, header=None)
    print(' sorting ' + 'Cancer_Location')
    al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
    print(' saving ' + 'Cancer_Location')
    al_file.to_csv(os.path.join(final_path, 'Cancer_Location'), sep='\t', index=False, header=False, line_terminator='\n')
    '''
###############################################################################
if __name__ == '__main__':

    #  Read command arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, required=True, help='RC index')
    parser.add_argument('--merge_close', type=str, required=False, help='merge-close file')

    FLAGS, unparsed = parser.parse_known_args()

    if (unparsed):
        eprint("Left with unparsed arguments:")
        eprint(unparsed)
        exit(0)


    eprint(f'Running on index = {FLAGS.index}')
    codes_to_cancer_location(ThinReadcodes,FLAGS.merge_close,FLAGS.index)
