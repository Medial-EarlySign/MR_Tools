import os
import re
import pandas as pd
import traceback
from Configuration import Configuration
from const_and_utils import write_tsv, eprint, fixOS, read_tsv
import time
from split_medical import get_unique_outfile


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
        print(rc + 'Returning the close one with 00 as the end: ' + zerorc[0])
        return zerorc[0]
    return None


def get_close_rc2(rc, all_codes):
    if rc in all_codes['code'].values:
        return [rc]
    rc_list = []
    for i in range(len(rc), 1, -1):
        if rc[:i] in all_codes['short_code'].values:
            rc_list = list(all_codes[all_codes['short_code'] == rc[:i]]['code'].values)
            break
    if len(rc_list) > 0:
        return rc_list
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


# def save_registry(rc_df, cancer_types_df, path):
#     rc_df['eventdate_ts'] = pd.to_datetime(rc_df['eventdate'].astype(str), format='%Y%m%d', errors='coerce')
#     pids = rc_df['medialid'].unique()
#     print(' going over ' + str(len(pids)) + ' pids')
#     fixed_df = pd.DataFrame()
#     cnt = 0
#     time1 = time.time()
#     for pid in pids:
#         cnt = cnt + 1
#         pid_df = rc_df[rc_df['medialid'] == pid].copy()
#         fixed_df = fixed_df.append(fix_cancer_eventdate(pid_df), ignore_index=True)
#         if (cnt % 1000) == 0 or cnt == len(pids):
#             print(' fixed cancer_eventdate for ' + str(cnt) + '(' + str(int((cnt/len(pids)*100)))+') patients in ' + str(time.time()-time1))
#             time1 = time.time()
#             fixed_df['out_field'] = fixed_df.apply(lambda x: translate_cancer_types(x['status'],
#                                                                                     x['type_field'],
#                                                                                     x['organ'],
#                                                                                     cancer_types_df[['in', 'out']]),
#                                                    axis=1)
#             print('Empty fields count = ' + str(fixed_df[fixed_df['out_field'] == ''].shape[0]))
#             fixed_df = fixed_df[fixed_df['out_field'] != '']
#             fixed_df['sig'] = 'Cancer_Location'
#             fixed_df.sort_values(by=['medialid', 'eventdate'], inplace=True)
#             write_tsv(fixed_df[['medialid', 'sig', 'eventdate', 'out_field']], path, 'Cancer_Location')
#             del fixed_df
#             fixed_df = pd.DataFrame()


def save_registry(rc_df, cancer_types_df, path):
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
    write_tsv(fixed_df[['medialid', 'sig', 'eventdate', 'out_field']], path, 'Cancer_Location')


def codes_to_cancer_location():
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    medical_path = os.path.join(out_folder, 'medical_files')

    if not (os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - code_folder don''t exists')
    if not (os.path.exists(medical_path)):
        raise NameError('config error - Numeric don''t exists')

    final_path = os.path.join(out_folder, 'FinalSignals')
    med_staging_files = os.listdir(medical_path)

    codes_2_details_df = read_tsv('thin_cancer_medcodes_20190212.txt', code_folder, header=0,
                                  names=['code', 'nrec', 'npat', 'desc', 'comment', 'status', 'type_field', 'organ'])
    # codes_2_details_df['status'] = codes_2_details_df['status'].str.lower()
    ############
    codes_2_details_df['short_code'] = codes_2_details_df['code'].str[:5].str.replace('.', '')
    cancer_types_df = read_tsv('translate_cancer_types.txt', code_folder,
                               names=['status_in', 'type_in', 'organ_in', 'status_out', 'type_out', 'organ_out'])
    cancer_types_df['in'] = cancer_types_df.apply(lambda x: (x['status_in'], x['type_in'], x['organ_in']), axis=1)
    cancer_types_df['out'] = cancer_types_df.apply(lambda x: (x['status_out'], x['type_out'], x['organ_out']), axis=1)

    #  Work on patients by practices
    id2nr_file = os.path.join(out_folder, 'ID2NR')
    id2nr_df = pd.read_csv(id2nr_file, sep='\t', names=['combid', 'medialid'],
                           dtype={'combid': str, 'medialid': int})
    id2nr_df['medialid'] = id2nr_df['medialid'].astype(int)
    ###
    codes = codes_2_details_df['code'].unique()
    signal_df = pd.DataFrame()
    staging_files_df = pd.DataFrame(med_staging_files, columns=['file'])
    staging_files_df['rc'] = staging_files_df['file'].str[:7]
    staging_files_df['close_rc'] = staging_files_df['rc'].apply(lambda x: get_close_rc(x, codes_2_details_df[['short_code', 'code']]))

    merge_close = staging_files_df.merge(codes_2_details_df, left_on='close_rc', right_on='code')
    #merge_close.to_csv('c:\\Temp\\match_rc.csv')
    #merge_close = merge_close[(merge_close['status'] == 'Anc') &  (merge_close['type_field'] == 'na') & (merge_close['organ'] == 'na')]
    codes_files = merge_close['file'].unique()
    for i, x in merge_close[['file', 'desc', 'organ']].drop_duplicates().iterrows():
        print(x['file'][:7] + ', ' + x['desc'] + ', ' + x['organ'] )
    #close_codes = [get_unique_outfile(x) for x in codes]
    print(' Reading ' + str(len(codes_files)) + ' Readcodes')
    cnt = 1
    for rccd in codes_files:
    #for rccd in ['B339.00']:
        print(str(cnt) + ' reading file ' + rccd)
        cnt+=1
        one_df = read_tsv(rccd, medical_path,
                          names=['medialid', 'eventdate', 'medcode', 'nhsspec', 'source'],
                          header=None)
        signal_df = signal_df.append(one_df, ignore_index=True)

    # splitting to pracs for memory preformance
    pracs = list(filter(lambda f: f.startswith('ahd.'), os.listdir(fixOS(cfg.raw_source_path))))
    pracs = [x[4:] for x in pracs]
    #print(pracs)
    for pr in pracs:
        ids = list(id2nr_df[id2nr_df['combid'].str.startswith(pr)]['medialid'].values)
        signal_df_pr = signal_df[signal_df['medialid'] .isin(ids)]
        print(' Processing parc ' + pr)
        reg_df = signal_df_pr[['medialid', 'eventdate', 'medcode']].merge(merge_close, how='left',
                                                                          left_on='medcode', right_on='rc')
        save_registry(reg_df, cancer_types_df, final_path)

    cols = ['medialid', 'sig', 'eventdate', 'val']
    al_file = read_tsv('Cancer_Location', final_path, names=cols, header=None)
    print(' sorting ' + 'Cancer_Location')
    al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
    print(' saving ' + 'Cancer_Location')
    al_file.to_csv(os.path.join(final_path, 'Cancer_Location'), sep='\t', index=False, header=False, line_terminator='\n')


if __name__ == '__main__':
    codes_to_cancer_location()
