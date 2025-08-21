import os
import re
import pandas as pd
import traceback
from Configuration import Configuration
from const_and_utils import write_tsv, eprint, fixOS, read_tsv
import time
from sql_utils import get_sql_engine
from generate_id2nr import get_id2nr_map

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
        print(rc + ' Returning the close one with 00 as the end: ' + zerorc[0])
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
        pid_df.sort_values('date1', inplace=True)
        pid_df['timediff'] = (pid_df['date1'] - pid_df['date1'].shift(1)).astype('timedelta64[D]')

        pid_df['prev'] = pid_df.shift(1)['status'].str.lower.isin(['morph', 'anc'])
        pid_df['tofix'] = (pid_df['status'].str.lower.contains('cancer')) & (pid_df['prev']) & (pid_df['timediff'] < 62)
        pid_df['date1'] = pid_df['date1'].where(~pid_df['tofix'], pid_df['date1'].shift(1))
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
    #rc_df['eventdate_ts'] = pd.to_datetime(rc_df['eventdate'].astype(str), format='%Y%m%d', errors='coerce')
    npids = rc_df['medialid'].unique()
    print(' going over ' + str(npids) + ' pids')
    fixed_df = pd.DataFrame()
    time1 = time.time()
    for pid, pid_df in rc_df.groupby('medialid'):
        fixed_df = fixed_df.append(fix_cancer_eventdate(pid_df), ignore_index=True)
    time2 = time.time()
    print('   fixed cancer_eventdate for ' + str(npids) + ' patients in ' + str(time2 - time1))
    fixed_df['out_field'] = fixed_df.apply(lambda x: translate_cancer_types(x['status'],
                                                                            x['type_field'],
                                                                            x['organ'],
                                                                            cancer_types_df[['in', 'out']]), axis=1)
    if fixed_df[fixed_df['out_field'] == ''].shape[0] > 0:
        print('   Empty fields count = ' + str(fixed_df[fixed_df['out_field'] == ''].shape[0]))
    print('   build out tuples in ' + str(time.time() - time2))
    fixed_df = fixed_df[fixed_df['out_field'] != '']
    fixed_df['sig'] = 'Cancer_Location'
    fixed_df.sort_values(by=['medialid', 'date1'], inplace=True)
    write_tsv(fixed_df[['medialid', 'sig', 'date1', 'out_field']], path, 'Cancer_Location')


def codes_to_cancer_location(th_def):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - code_folder don''t exists')



    codes_2_details_df = read_tsv('thin_cancer_medcodes_20190212.txt', code_folder, header=0,
                                  names=['code', 'nrec', 'npat', 'desc', 'comment', 'status', 'type_field', 'organ'])
    codes_2_details_df['short_code'] = codes_2_details_df['code'].str[:5].str.replace('.', '')
    cancer_types_df = read_tsv('translate_cancer_types.txt', code_folder,
                               names=['status_in', 'type_in', 'organ_in', 'status_out', 'type_out', 'organ_out'])
    cancer_types_df['in'] = cancer_types_df.apply(lambda x: (x['status_in'], x['type_in'], x['organ_in']), axis=1)
    cancer_types_df['out'] = cancer_types_df.apply(lambda x: (x['status_out'], x['type_out'], x['organ_out']), axis=1)

    #  Work on patients by practices
    id2nr_df = get_id2nr_map()
    ###

    db_engine = get_sql_engine(th_def.DBTYPE, th_def.DBNAME, th_def.username, th_def.password)
    sql_query = "SELECT DISTINCT(code) as rc FROM " + th_def.TABLE
    staging_files_df = pd.read_sql_query(sql_query, db_engine)
    staging_files_df['close_rc'] = staging_files_df['rc'].apply(lambda x: get_close_rc(x, codes_2_details_df[['short_code', 'code']]))

    merge_close = staging_files_df.merge(codes_2_details_df, left_on='close_rc', right_on='code')

    codes_files = merge_close['rc'].unique()
    for i, x in merge_close[['rc', 'desc', 'organ']].drop_duplicates().iterrows():
        print(x['rc'] + ', ' + x['desc'] + ', ' + x['organ'] )
    #close_codes = [get_unique_outfile(x) for x in codes]
    print(' Querying ' + str(len(codes_files)) + ' Readcodes')
    cnt = 1
    signal_df = pd.DataFrame()
    for rccd in codes_files:

        print(str(cnt) + ' query for RC ' + rccd)
        cnt+=1
        sql_query = "SELECT * FROM " + th_def.TABLE + " WHERE code = '" + rccd + "'"
        one_df = pd.read_sql_query(sql_query, db_engine)
        #one_df = read_tsv(rccd, medical_path,
        #                  names=['medialid', 'eventdate', 'medcode', 'nhsspec', 'source'],
        #                  header=None)
        signal_df = signal_df.append(one_df, ignore_index=True)

    # splitting to pracs for memory preformance
    pracs = list(filter(lambda f: f.startswith('ahd.'), os.listdir(fixOS(cfg.raw_source_path))))
    pracs = [x[4:] for x in pracs]
    #print(pracs)
    signal_df['medialid'] = signal_df['orig_pid'].astype(str).map(id2nr_df)
    signal_df['prac'] = signal_df['orig_pid'].str[0:5]
    for pr in pracs:
        #ids = list(id2nr_df[id2nr_df['combid'].str.startswith(pr)]['medialid'].values)
        signal_df_pr = signal_df[signal_df['prac'] == pr]
        print(' Processing parc ' + pr)
        reg_df = signal_df_pr[['medialid', 'date1', 'value']].merge(merge_close, how='left',
                                                                    left_on='value', right_on='rc')
        save_registry(reg_df, cancer_types_df, out_folder)

    cols = ['medialid', 'sig', 'eventdate', 'val']
    al_file = read_tsv('Cancer_Location', out_folder, names=cols, header=None)
    print(' sorting ' + 'Cancer_Location')
    al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
    print(' saving ' + 'Cancer_Location')
    al_file.to_csv(os.path.join(out_folder, 'Cancer_Location'), sep='\t', index=False, header=False, line_terminator='\n')


