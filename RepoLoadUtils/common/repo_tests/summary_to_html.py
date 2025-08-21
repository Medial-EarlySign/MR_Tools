import pandas as pd
import os
import sys
import io
from math import sqrt
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import fixOS
from plots_utils import make_bar_plot
from bokeh.layouts import gridplot, row
from bokeh.embed import components
from bokeh.embed import file_html
from bokeh.resources import CDN
pd.set_option('display.max_colwidth', -1)


file_types = {'n': 'numeric_summary.html',
              'c': 'category_summary.html',
              'd': 'dates_summary.html',
              'y': 'yes_no_summary.html',
              'e': 'empty_summary.html'}


def summary_table_to_html(df, outpath, file_name):
    if df.empty:
        print('summary table is empty')
        return

    # to fix the columns order
    non_dsc_cols = ['pid_count', 'channel', 'signal']
    rem_cols = ['file_name', 'type']
    cols = [x for x in df.columns if x not in non_dsc_cols+rem_cols]
    for col in non_dsc_cols:
        cols.insert(0, col)
    table_to_html(df[cols], outpath, file_name)


def table_to_html(df, outpath, file_name):
    if df.empty:
        print('table is empty')
        return
    if 'signal' not in df.columns:
        df.reset_index(inplace=True)
        df = df.rename(columns={'index': 'signal'})
    else:
        df.reset_index(inplace=True, drop=True)
    df.loc[:, 'ref_str'] = '<a href="AAAAAA.html" target="_blank">AAAAAA </a>'
    df.loc[:, 'signal'] = df.apply(lambda x: x['ref_str'].replace('AAAAAA', x['signal']).replace('#.html', 'No.html'), axis=1)
    #df = df.set_index('signal')
    df.drop(columns=['ref_str'], inplace=True)
    cols = df.columns.tolist()
    cols.remove('signal')
    cols.insert(0, 'signal')
    pd.set_option('display.max_colwidth', -1)
    html = df[cols].to_html(float_format='%10.2f', escape=False)
    full_file_name = os.path.join(outpath, file_name)
    text_file = open(full_file_name, "w")
    text_file.write('<H1>'+file_name.split('.')[0]+'</H1>')
    text_file.write(html)
    text_file.close()
    print('table written to ' + full_file_name)


def get_summary_df(output_path):
    sum_file = os.path.join(output_path, 'signals_summary.csv')
    if os.path.exists(sum_file):
        sum_df = pd.read_csv(sum_file, sep='\t')
    else:
        sum_df = pd.DataFrame()
    return sum_df


def get_vc_file_name(signal, channel, suff, outpath=None):
    file_name = signal+'_'+channel+'_vc.' + suff
    if outpath:
        return os.path.join(outpath, file_name)
    else:
        return file_name


def summary_tables(sum_df, output_path):
    sigs_with_vals = sum_df[sum_df['type'] != 'd']['signal']
    sum_df = sum_df[(sum_df['type'] != 'd') | ((sum_df['type'] == 'd') & (~sum_df['signal'].isin(sigs_with_vals)))]
    for typ, typ_df in sum_df.groupby('type'):
        typ_df.dropna(axis=1, inplace=True)
        summary_table_to_html(typ_df, output_path, file_types[typ])
    return


def calc_outliers(sum_df, output_path):
    mult = 7
    #out_list = []
    for i, inf in sum_df.iterrows():
        outliers_cnt = 0
        #vfield = inf['channel']
        sig = inf['signal']
        if inf['type'] != 'n':
            #out_list.append({'signal': sig, 'channel': vfield, 'outliers':  None})
            continue
        vfield = inf['channel']
        #sig_std = inf['std'] * mult
        vc_file = get_vc_file_name(sig, vfield, 'csv', output_path)
        vc_df = pd.read_csv(vc_file.replace('#', 'No'), sep='\t')
        ren_cols = {x: x.replace('%', 'per') for x in vc_df.columns}
        vc_df.rename(columns=ren_cols, inplace=True)
        curr_outl = 100
        curr_vc = vc_df.copy()
        while curr_outl > 0:
            crur_mean = (curr_vc[vfield]*curr_vc['count']).sum() / curr_vc['count'].sum()
            curr_std = sqrt(((curr_vc[vfield] - crur_mean).pow(2) * curr_vc['count']).sum() / curr_vc['count'].sum())
            sig_std = curr_std * mult
            new_curr_vc = curr_vc[(curr_vc[vfield] > crur_mean - sig_std) & (curr_vc[vfield] < crur_mean + sig_std)]
            out_std_df = curr_vc[(curr_vc[vfield] <= crur_mean - sig_std) | (curr_vc[vfield] >= crur_mean + sig_std)]
            curr_outl = out_std_df.shape[0]
            curr_vc = new_curr_vc.copy()
            outliers_cnt += curr_outl
        #out_list.append({'signal': sig, 'channel': vfield, 'outliers': outliers_cnt})
        sum_df.loc[i, 'outliers'] = outliers_cnt
    return sum_df


def check_vc(sig, chan_sum, vc_df, vc_file_name, typ):
    dct = {'signal': sig}
    table_html = vc_df.to_html()
    with open(vc_file_name, 'w', encoding='utf-8') as f:
        f.write(table_html)
        f.close()
    # vc_df.to_html(vc_file_name, index=False)

    if typ == 'y':
        return dct
    if typ == 'n':
        mean_meadin_diff = abs(chan_sum['50per'] - chan_sum['mean']) / chan_sum['mean']* 100
        if 50 < mean_meadin_diff < 100:
            dct['mean_meadin_diff'] = mean_meadin_diff
    # Save to html file

    # Check integrity
    if vc_df[vc_df['per'] >= 0.1].shape[0] > 0:
        first = vc_df[vc_df['per'] >= 0.1].index[0]
        last = vc_df[vc_df['per'] >= 0.1].index[-1]
    else:
        first = vc_df.index[0]
        last = vc_df.index[-1]
    vc_df_cut = vc_df.loc[first:last]

    if vc_df_cut.shape[0]/vc_df.shape[0] <= 0.2:  # many values with small count - long tail?
        #dct['tail_size'] = round((vc_df_cut.shape[0]/vc_df.shape[0])*100, 2)
        if vc_df_cut.shape[0] == 0:
            return dct
    if (chan_sum['outliers'] / vc_df['count'].sum())*100 > 1:
        dct['tail_size'] = round((chan_sum['outliers'] / vc_df['count'].sum())*100, 2)
    vc_df_cut['smoth'] = vc_df_cut['count'].rolling(11, center=True).mean()

    #gap = (vc_df_cut['count'].shift() - vc_df_cut['count']) >= 0
    gap = (vc_df_cut['smoth'].shift() - vc_df_cut['smoth']) >= 0
    gap = gap.replace(True, 1)
    gap = gap.replace(False, 0)
    gap_diff = gap.diff()
    #change = pd.concat([vc_df_cut['count'].pct_change(1).abs(), vc_df_cut['count'].pct_change(-1).abs()], axis=1).min(
    #    axis=1).round(2) < 0.1
    #gap_diff = gap_diff.where(change==False, 0)
    diffs = gap_diff.abs().sum()
    if diffs > 5:
        dct['trends_changes'] = diffs
    vc_df_cut.loc[:, 'local_max'] = vc_df_cut['count'].rolling(11, center=True).max()
    vc_df_cut.loc[:, 'peaks'] = (vc_df_cut['local_max'] == vc_df_cut['count'])
    peaks = vc_df_cut[vc_df_cut['peaks'] == True].shape[0]
    if peaks > 1:
        dct['peeks'] = peaks
    return dct


def get_sig_years(title, yr_df, channel, typ):
    year_stat = yr_df[yr_df['channel'] == channel].dropna(axis=1, how='all')
    year_stat.set_index('year', inplace=True)
    plotlist = []
    if typ == 'n':
        plotlist.append(make_bar_plot(title + ' ' + ' count', year_stat['count']))
        plotlist.append(make_bar_plot(title + ' ' + ' count per pid', year_stat['count'] / year_stat['pid_count']))
        plotlist.append(make_bar_plot(title + ' ' + ' mean', year_stat['mean']))
        plotlist.append(make_bar_plot(title + ' ' + ' median', year_stat['median']))
        year_plot = gridplot(plotlist, ncols=4, plot_width=300, plot_height=300)
    else:
        plotlist.append(make_bar_plot(title + ' ' + ' count', year_stat['count']))
        plotlist.append(make_bar_plot(title + ' ' + ' count per pid', year_stat['count'] / year_stat['pid_count']))
        year_plot = gridplot(plotlist, ncols=2, plot_width=300, plot_height=300)
    year_stat.reset_index(inplace=True)
    return year_stat, year_plot


def get_sig_stat(title, vc_df, typ):
    if typ == 'n' or typ == 'd':
        if vc_df[vc_df['per'] >= 0.1].shape[0] > 0:
            first = vc_df[vc_df['per'] >= 0.1].index[0]
            last = vc_df[vc_df['per'] >= 0.1].index[-1]
        else:
            first = vc_df.index[0]
            last = vc_df.index[-1]
        vc_df_cut = vc_df.loc[first:last]
        sig_hist_plot = make_bar_plot(title, vc_df_cut['count'])
    elif typ == 'c' or typ == 'y':
        if not pd.api.types.is_numeric_dtype(vc_df.index.dtype):
            vc_df.index = vc_df.index.str[0:30]
        sig_hist_plot = make_bar_plot(title,  vc_df[0:20]['count'])

    return sig_hist_plot


def plot_single_signal(sig, sig_sum_df, output_path):
    print('plot_single_signal')
    sig_hist_plots = []
    year_plots = []
    year_stats = []
    ren_cols = {x: x.replace('%', 'per') for x in sig_sum_df.columns}
    sig_sum_df.rename(columns=ren_cols, inplace=True)
    #sig_sum_df = sum_df[sum_df['signal'] == sig].copy()
    if sig_sum_df.empty:
        return {'signal': sig}
    #sig_sum_df.dropna(axis=1, inplace=True)
    problem_list = []
    cols = ['signal', 'channel']
    rem_cols = ['type', 'file_name']
    cols = cols + [x for x in sig_sum_df.columns if x not in cols and x not in rem_cols]
    sig_stats = sig_sum_df[cols]
    #only_date = len([x for x in sig_stats['channel'].values if 'val' in x]) == 0
    only_date = len([x for x in sig_sum_df['type'].values if x != 'd']) == 0
    urlstr = io.StringIO()
    for i, r in sig_sum_df.iterrows():
        vfield = r['channel']
        typ = r['type']
        print(sig, vfield, typ)
        vc_file = get_vc_file_name(sig, vfield, 'csv', output_path)
        vc_df = pd.read_csv(vc_file.replace('#', 'No'), sep='\t')
        ren_cols = {x: x.replace('%', 'per') for x in vc_df.columns}
        vc_df.rename(columns=ren_cols, inplace=True)
        if typ != 'd' or only_date:
            if typ == 'n':
                vc_df[vfield] = vc_df[vfield].round(2)
            sig_hist_plot = get_sig_stat(sig+'_'+vfield, vc_df.set_index(vfield), typ)
            sig_hist_plots.append(sig_hist_plot)
            year_file = os.path.join(output_path, sig.replace('#', 'No') + '_years.csv')
            if os.path.exists(year_file):
                yr_df = pd.read_csv(year_file, sep='\t')
                yr_df.rename(columns={x: x.replace('%', 'per') for x in yr_df.columns}, inplace=True)
                year_stat, year_plot = get_sig_years(sig+'_'+vfield, yr_df, vfield, typ)
                year_stats.append(year_stat)
                year_plots.append(year_plot)

        html_vc_file = get_vc_file_name(sig.replace('#', 'No'), vfield, 'html', output_path)
        err_dict = check_vc(sig, r, vc_df,  html_vc_file, typ)
        err_dict['chanel'] = vfield
        problem_list.append(err_dict)
        link = '<a href="'+os.path.basename(html_vc_file)+'">' + vfield + ' - Value Counts list <br></a>'
        urlstr.write(link)

    out_file = os.path.join(output_path, sig + '.html')
    out_file = out_file.replace('#', 'No')
    table_html = sig_stats.to_html()
    # sig_stats.to_html(out_file)
    #plots = row(sig_hist_plots)
    plots = gridplot(sig_hist_plots, ncols=4, plot_width=700, plot_height=450)

    html_plot1 = file_html(plots, CDN, sig)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(table_html)
        f.write(html_plot1)
        f.write(urlstr.getvalue())
        for pl, st in zip(year_plots, year_stats):
            if pl:
                html_plot2 = file_html(pl, CDN, sig)
                htmlstr = io.StringIO()
                st.to_html(htmlstr, index=False)
                f.write(html_plot2)
                f.write(htmlstr.getvalue())
        f.close()
    return problem_list


import datetime as dt
def fix_ts_m1900(ser1):
    max_delta = 150000000
    real_time = dt.datetime(1900, 1, 1)
    while ser1.max()>0:
        mod = ser1.where(ser1<max_delta, max_delta)
        real_time = real_time + pd.TimedeltaIndex(mod , unit='m')
        ser1 = ser1-max_delta
        ser1 = ser1.where(ser1>0, 0)
    return real_time


if __name__ == '__main__':
    output_path = fixOS('/nas1/Work/Users/Tamar/mimic_load/output/')
    #times = pd.read_csv(os.path.join(output_path,'ADMISSION_time0_vc.csv'), sep='\t', usecols=[0])
    #fix_ts_m1900(times['time0'])
    sum_df = get_summary_df(output_path)
    #sum_df = calc_outliers(sum_df, output_path)
    #summary_tables(sum_df, output_path)

    err_list = []
    sigs = ['Vent_No']  # ['BDATE', 'ALKP', 'ALT', 'B12', 'Bands#', 'ETHNICITY', 'Urine_RBC', 'MALE_PARTNER_YN']
    cnt = 0
    for sig in sigs:
        cnt += 1
        print(sig + ' (' + str(cnt) + '/' + str(len(sigs)) + ')')
        sig_sum_df = sum_df[sum_df['signal'] == sig].copy()
        sig_err_list = plot_single_signal(sig, sig_sum_df, output_path)
        print(sig_err_list)
        err_list.extend(sig_err_list)
    # errors_df = pd.concat([errors_df, pd.DataFrame(err_list).set_index('signal')], axis=1, sort=False)
    errors_df = pd.DataFrame(err_list).set_index(['signal', 'chanel'])
    errors_df.dropna(how='all', inplace=True)
    table_to_html(errors_df, output_path, 'problems_list.html')
