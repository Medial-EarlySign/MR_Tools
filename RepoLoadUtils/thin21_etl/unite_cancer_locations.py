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

def save_registry(rc_df, cancer_types_df, path):

    if rc_df.shape[0] == 0:
        return
    rc_df['eventdate_ts'] = pd.to_datetime(rc_df['eventdate'].astype(str), format='%Y%m%d', errors='coerce')
    pids = rc_df['medialid'].unique()
    #print(' going over ' + str(len(pids)) + ' pids')
    #fixed_df = pd.DataFrame()
    time1 = time.time()
    #for pid, pid_df in rc_df.groupby('medialid'):
    #    fixed_df = fixed_df.append(fix_cancer_eventdate(pid_df), ignore_index=True)

    nFix = 1
    while (nFix>0):
        rc_df.sort_values(['medialid', 'eventdate_ts'], inplace=True)
        rc_df['timediff'] = (rc_df['eventdate_ts'] - rc_df['eventdate_ts'].shift(1)).astype('timedelta64[D]')
        rc_df['prev'] = rc_df.shift(1)['status'].str.lower().isin(['morph', 'anc'])
        rc_df['same_id'] = (rc_df['medialid'] == rc_df['medialid'].shift(1))
        rc_df['tofix'] = (rc_df['same_id']) & (rc_df['status'].str.lower().str.contains('cancer')) & (rc_df['prev']) & (
                    rc_df['timediff'] < 62)
        nFix = rc_df.tofix.astype(int).sum()
        eprint(f'Done identifying {nFix} lines to fix')
        rc_df['eventdate'] = rc_df['eventdate'].where(~rc_df['tofix'], rc_df['eventdate'].shift(1))
        eprint('Done fixing dates')
        rc_df['to_drop'] = rc_df['tofix'].shift(-1)
        rc_df.drop(rc_df[rc_df['to_drop'] == True].index, inplace=True)
        eprint('Done droping redundant lines')


    time2 = time.time()
    eprint('fixed cancer_eventdate for ' + str(len(pids)) + ' patients in ' + str(time2 - time1))
    rc_df['out_field'] = rc_df.apply(lambda x: translate_cancer_types(x['status'],x['type_field'],x['organ'],cancer_types_df[['in', 'out']]), axis=1)
    if rc_df[rc_df['out_field'] == ''].shape[0] > 0:
        print('   Empty fields count = ' + str(rc_df[rc_df['out_field'] == ''].shape[0]))
    eprint('build out tuples in ' + str(time.time() - time2))
    fixed_df = rc_df[rc_df['out_field'] != '']
    fixed_df['sig'] = 'Cancer_Location'
    fixed_df.sort_values(by=['medialid', 'eventdate'], inplace=True)
    write_tsv(fixed_df[['medialid', 'sig', 'eventdate', 'out_field']], path, 'Cancer_Location')

def files_to_cancer_location():

    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    final_path = os.path.join(out_folder, 'FinalSignals')
    if not (os.path.exists(final_path)):
        raise NameError(f'{final_path} does not exist')

    code_folder = fixOS(cfg.code_folder)
    if not (os.path.exists(code_folder)):
        raise NameError(f'{code_folder} does not exist')

    ############
    cancer_types_df = read_tsv('translate_cancer_types.txt', code_folder,
                               names=['status_in', 'type_in', 'organ_in', 'status_out', 'type_out', 'organ_out'])
    cancer_types_df['in'] = cancer_types_df.apply(lambda x: (x['status_in'], x['type_in'], x['organ_in']), axis=1)
    cancer_types_df['out'] = cancer_types_df.apply(lambda x: (x['status_out'], x['type_out'], x['organ_out']),axis=1)
    eprint(f'Read translation table of {len(cancer_types_df)} lines')

    cancer_location_files = [file for file in os.listdir(final_path) if re.match(r'Cancer_Location_\d+',file)]
    eprint(f'Working on {len(cancer_location_files)} RC_ files')

    for idx,name in enumerate(cancer_location_files):
        file_name = os.path.join(final_path,name)
        eprint(f'Working on file {idx}/{len(cancer_location_files)} : {file_name}')
        reg_df = pd.read_csv(file_name,index_col=0)
        olen = len(reg_df)
        reg_df.drop_duplicates(inplace=True,ignore_index=True)
        eprint(f'Working on {len(reg_df)} lines ({olen} with duplications)')
        save_registry(reg_df, cancer_types_df, final_path)

    # Re-read and sort
    cols = ['medialid', 'sig', 'eventdate', 'val']
    al_file = read_tsv('Cancer_Location', final_path, names=cols, header=None)
    print(' sorting ' + 'Cancer_Location')
    al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
    print(' saving ' + 'Cancer_Location')
    al_file.to_csv(os.path.join(final_path, 'Cancer_Location'), sep='\t', index=False, header=False, line_terminator='\n')

###############################################################################
if __name__ == '__main__':
    files_to_cancer_location()
