import argparse
import os
import sys
import pandas as pd
import datetime as dt
import gc
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from summary_to_html import summary_tables, plot_single_signal, table_to_html, get_summary_df, calc_outliers, fixOS
from index_page import index_to_html
import medpython as med

pd.set_option('display.max_colwidth', -1)
time_unit = 'DAY'

# When times are in minuts need to translate min since 1900 to date
# Max time delta is too shirt to calc dates in mimic so a loop of max timedelta is needed
def fix_ts_m1900(ser1):
    max_delta = 150000000
    real_time = dt.datetime(1900, 1, 1)
    while ser1.max()>0:
        mod = ser1.where(ser1<max_delta, max_delta)
        real_time = real_time + pd.TimedeltaIndex(mod , unit='m')
        ser1 = ser1-max_delta
        ser1 = ser1.where(ser1>0, 0)
    return real_time


def read_signal_file(sig_file):
    f = open(sig_file)
    lines = f.readlines()
    sigs = []
    for ln in lines:
        cells = ln.split('\t')
        if cells[0] != 'SIGNAL':
            continue
        if len(cells) >= 6:
            sigs.append({'signal': cells[1], 'sigid': cells[2]})
    sigs_df = pd.DataFrame(sigs)
    return sigs_df


def set_time_unit(rep_file):
    f = open(rep_file)
    lines = f.readlines()
    for ln in lines:
        cells = ln.split('\t')
        if cells[0].strip() == 'TIMEUNIT' and cells[1].strip() == '6':
            return 'MIN'
    return 'DAY'


def is_date(col):
    bool_ser = (col > 17000000) & (col < 30000000)
    if bool_ser.all():
        return True
    else:
        return False


def is_yes_no(col):
    unq = col.unique()
    if unq.shape[0] == 2 and 0 in unq and 1 in unq:
        return True
    else:
        return False


def get_channel_type(chan):
    if chan.dtype.name == 'category':
        return 'c'
    elif is_date(chan):
        return 'd'
    elif is_yes_no(chan):
        return 'y'
    else:
        return 'n'


def save_chanel(ser, sig, channel, output_path):
    vc_df = pd.concat([ser.value_counts(dropna=False).rename('count'),
                       ser.value_counts(dropna=False, normalize=True).rename('%')],
                      axis=1, sort=False)
    vc_df['%'] = (vc_df['%']*100).round(2)
    vc_df = vc_df.reset_index().rename(columns={'index': channel})
    if pd.api.types.is_numeric_dtype(ser):
        vc_df.sort_values(by=channel, inplace=True)
    vc_file_csv = sig + '_' + channel + '_vc.csv'
    vc_file_csv = vc_file_csv.replace('#', 'No')
    cols = [channel, 'count', '%']
    vc_df[cols].to_csv(os.path.join(output_path, vc_file_csv), sep='\t', index=False)
    return vc_file_csv


def save_year_stat(sig, sdf, date_cols, output_path):
    if len(date_cols) == 0:
        return
    sdf['year'] = (sdf[date_cols[0]] / 10000).astype(int)
    stat_list = []
    for yr, yr_df in sdf.groupby('year'):
        for vfield in sdf.columns:
            stat = {'year': yr, 'count': yr_df.shape[0], 'pid_count': yr_df['pid'].nunique()}
            typ = get_channel_type(sdf[vfield])
            #print(sig, yr, vfield, typ)
            if vfield == 'pid' or vfield == 'year' or typ == 'd':
                continue
            stat['channel'] = vfield
            stat['type'] = typ
            if typ == 'n':
                stat['mean'] = yr_df[vfield].mean()
                stat['median'] = yr_df[vfield].median()
                stat['std'] = yr_df[vfield].std()
                stat['min'] = yr_df[vfield].min()
                stat['max'] = yr_df[vfield].max()
            elif typ == 'c':
                most = yr_df[vfield].mode().iloc[0]
                stat['most_freq'] = most
                stat['% freq'] = round((yr_df[yr_df[vfield] == most].shape[0] / yr_df.shape[0]) * 100,2)
            elif typ == 'y':
                for vl in yr_df[vfield].unique():
                    stat['value ' + str(vl)] = round((yr_df[yr_df[vfield] == vl].shape[0] / yr_df.shape[0]) * 100, 2)
            stat_list.append(stat)
    if len(stat_list) > 0:
        yr_stat = pd.DataFrame(stat_list)
        yr_file_csv = sig + '_years.csv'
        yr_file_csv = yr_file_csv.replace('#', 'No')
        yr_stat.to_csv(os.path.join(output_path, yr_file_csv), sep='\t', index=False)
    return


def fix_time(x):
    real_date = dt.datetime(1900, 1, 1) + dt.timedelta(minutes=x)
    return int(str(real_date.year) + str(real_date.month).zfill(2) + str(real_date.day).zfill(2))


def save_signal(rep, sig, output_path):
    try:
        sdf = rep.get_sig(sig)
        print(sdf.shape)
    except MemoryError as se:
        print('Memory error Except')
        return []
    sig_dsc_list = []
    if sdf.shape[0] == 0:
        dict1 = pd.Series({'signal': sig, 'pid_count': 0, 'channel': '-', 'count': 0, 'type': 'e'}, name=sig)
        sig_dsc_list.append(dict1)
        return sig_dsc_list
    date_cols = [x for x in sdf.columns if 'date' in x or 'time' in x]
    if time_unit != 'DAY':
        for dt1 in date_cols:
            sdf[dt1] = sdf[dt1].apply(lambda x: fix_time(x))
    for vfield in sdf.columns:
        if vfield == 'pid':
            continue
        typ = get_channel_type(sdf[vfield])
        print(sig, vfield, typ)
        dict1 = pd.Series({'signal': sig, 'pid_count': sdf['pid'].nunique(), 'channel': vfield, 'type': typ}, name=sig)
        if typ == 'd':
            sdf['year'] = (sdf[vfield] / 10000).astype(int)
            dict1 = dict1.append(sdf['year'].describe())
            file_name = save_chanel(sdf['year'], sig, vfield, output_path)
        else:
            dict1 = dict1.append(sdf[vfield].describe())
            file_name = save_chanel(sdf[vfield], sig, vfield, output_path)
        dict1['file_name'] = file_name
        sig_dsc_list.append(dict1)
    save_year_stat(sig, sdf, date_cols, output_path)
    del sdf
    gc.collect()
    return sig_dsc_list


def save_all_summary(rep, sigs, output_path, overwrite=False):
    sum_file = os.path.join(output_path, 'signals_summary.csv')
    if os.path.exists(sum_file):
        sum_df = pd.read_csv(sum_file, sep='\t')
        ext_sigs = sum_df['signal'].unique()
    else:
        sum_df = pd.DataFrame()
        ext_sigs = []
    cnt = 0
    ext_files = os.listdir(output_path)
    dsc_list = []
    for sig in sigs:
        sig_files = [x for x in ext_files if x.startswith(sig+'_')]
        cnt += 1
        print(sig + ' (' + str(cnt) + '/' + str(len(sigs)) + ')')
        if sig.startswith('RC') or sig.startswith('Drug'):
            print('skipping ' + sig)
            continue
        if sig in ext_sigs and not overwrite:
            print('Summary for ' + sig + ' already exists')
            continue
        elif not sum_df.empty:
            sum_df = sum_df[sum_df['signal'] != sig]
        dsc_list.extend(save_signal(rep, sig, output_path))
    sum_df = sum_df.append(pd.DataFrame(dsc_list))
    #print(sum_df)
    sum_df.to_csv(sum_file, sep='\t', index=False)
    return sum_df[sum_df['type'] != 'e']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', help="the repository file")
    parser.add_argument('--f_output',  help="output path")
    parser.add_argument('--f_signal', help="Signal name to create plots", default='All')
    parser.add_argument('--f_overwrite', action='store_true', help="Create new output files, default is to add if not exists")
    parser.add_argument('--f_only_html', action='store_true', help="Create only html summery tables")
    parser.add_argument('--f_only_index', action='store_true', help="Create only html summery tables")

    args = parser.parse_args()

    if not args.repository:
        raise Exception('no repository file supplied. Please supply one using --repository')
    if not args.f_output:
        raise Exception('no output ptah supplied. Please supply one using --f_output')
    else:
        if not os.path.exists(args.f_output):
            os.makedirs(args.f_output)

    rep_file = fixOS(args.repository)
    rep_path = os.path.dirname(rep_file)
    sigs_file = os.path.join(rep_path, os.path.basename(rep_file).split('.')[0]+'.signals')
    sigs_df = read_signal_file(sigs_file)
    time_unit = set_time_unit(rep_file)
    print(time_unit)
    rep = med.PidRepository()
    print(sigs_df.shape[0])
    rep.read_all(rep_file, [], ['GENDER'])
    print(med.cerr())
    exst = os.listdir(args.f_output)
    if args.f_signal == 'All':
        sigs = sigs_df['signal'].unique().tolist()
    else:
        sigs = [args.f_signal]
    if not args.f_only_html and not args.f_only_index:
        sum_df = save_all_summary(rep, sigs, args.f_output, args.f_overwrite)
    else:
        sum_df = get_summary_df(fixOS(args.f_output))
    if args.f_only_index:
        index_to_html(sum_df, args.repository, args.f_output)
        exit
    sum_df = calc_outliers(sum_df, fixOS(args.f_output))
    summary_tables(sum_df, args.f_output)
    sigs = sum_df[sum_df['type'] != 'e']['signal'].unique()
    err_list = []
    cnt=0
    for sig in sigs:
        cnt += 1
        print(sig + ' (' + str(cnt) + '/' + str(len(sigs)) + ')')
        if sig.startswith('RC') or sig.startswith('Drug'):
            print('skipping ' + sig)
            continue
        sig_sum_df = sum_df[sum_df['signal'] == sig].copy()
        if sig_sum_df.shape[0] > 0:
            sig_err_list = plot_single_signal(sig, sig_sum_df, fixOS(args.f_output))
            print(sig_err_list)
            err_list.extend(sig_err_list)
    if len(err_list) > 0:
        errors_df = pd.DataFrame(err_list).set_index(['signal', 'chanel'])
        errors_df.dropna(how='all', inplace=True)
        table_to_html(errors_df, args.f_output, 'problems_list.html')
    index_to_html(sum_df, args.repository, args.f_output)
    print('DONE')
