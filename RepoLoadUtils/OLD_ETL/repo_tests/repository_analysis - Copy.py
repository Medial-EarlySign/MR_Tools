import argparse
import os
import sys
import io
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from signals_plots import numeric_plots, category_plots
from plots_utils import get_histogram, get_year_stat, get_year_count, make_bar_plot, get_signal_units
from utils import fixOS
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.layouts import row
import medpython as med


def read_signal_file(sig_file):
    f = open(sig_file)
    lines = f.readlines()
    sigs = []
    for ln in lines:
        cells = ln.split('\t')
        if cells[0] != 'SIGNAL':
            continue
        if len(cells) < 6:
            print('Missing type ' + str(cells))
            cells.append('0')
        types = str(cells[5]).replace('\n', '').replace('\r', '')
        for dg, i in zip(types, range(0, len(types))):
            sigs.append({'signal': cells[1], 'sigid': cells[2], 'loc': i, 'type': dg})
    sigs_df = pd.DataFrame(sigs)
    return sigs_df


def is_date(col, tp):
    if tp == '1':
        return False
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


def summary_table_to_html(df, outpath, file_name):
    if df.empty:
        print('summary table is empty')
        return

    new_cols = ['pid_count', 'filed']
    cols = [x for x in df.columns if x not in new_cols]
    for col in new_cols:
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
    html = df[cols].to_html(float_format='%10.2f', escape=False)
    full_file_name = os.path.join(outpath, file_name)
    text_file = open(full_file_name, "w")
    text_file.write('<H1>'+file_name.split('.')[0]+'</H1>')
    text_file.write(html)
    text_file.close()
    print('table written to ' + full_file_name)


def check_vc(sig, sig_df, val_name, vc_file_name, typ):
    dct = {'signal': sig}
    if typ == '3':
        return dct
    if typ == '2':
        sig_df['year'] = (sig_df[val_name]/10000).astype(int)
        val_name = 'year'
    vc_df = pd.concat([sig_df[val_name].value_counts(dropna=False).rename('count'),
                       sig_df[val_name].value_counts(dropna=False, normalize=True).rename('%')],
                      axis=1, sort=False)

    vc_df = vc_df.reset_index().rename(columns={'index': val_name})

    if pd.api.types.is_numeric_dtype(vc_df[val_name]):
        vc_df.sort_values(by=val_name, inplace=True)
        mean_meadin_diff = abs(sig_df[val_name].median() - sig_df[val_name].mean()) / sig_df[val_name].mean() * 100
        if 50 < mean_meadin_diff < 100:
            dct['mean_meadin_diff'] = mean_meadin_diff
    # Save to file
    vc_df.to_html(vc_file_name, index=False)

    # Check integrity
    vc_df_cut = vc_df[(vc_df['%'] >= 0.001)].copy()

    gap = (vc_df_cut['count'].shift() - vc_df_cut['count']) >= 0
    gap = gap.replace(True, 1)
    gap = gap.replace(False, 0)
    gap_diff = gap.diff()
    #vc_df_cut['gap'] = gap
    #vc_df_cut['diff'] = gap_diff
    # the minimum change between the count in prev and next bin
    change = pd.concat([vc_df_cut['count'].pct_change(1).abs(), vc_df_cut['count'].pct_change(-1).abs()], axis=1).min(
        axis=1).round(2) < 0.1
    gap_diff = gap_diff.where(change==False, 0)
    diffs = gap_diff.abs().sum()
    if diffs > 5:
        dct['trends_changes'] = diffs
    vc_df_cut.loc[:, 'local_max'] = vc_df_cut['count'].rolling(11, center=True).max()
    vc_df_cut.loc[:, 'peaks'] = (vc_df_cut['local_max'] == vc_df_cut['count'])
    peaks = vc_df_cut[vc_df_cut['peaks'] == True].shape[0]
    if peaks > 1:
        dct['peeks'] = peaks
    return dct


def summary_tables(rep, sig_info_df, sigs, output_path):
    dsc_numeric_list = []
    dsc_category_list = []
    dsc_date_list = []
    dsc_yes_no_list = []
    dsc_empty_list = []
    for sig in sigs:

        if sig.startswith('RC'):
            continue
        sdf = rep.get_sig(sig)
        print(sig)
        if sdf.shape[0] == 0:
            dict1 = pd.Series({'pid_count': 0, 'filed': '', 'count': 0}, name=sig)
            dsc_empty_list.append(dict1)
            print('signal ' + sig + ' is empty')
            continue
        vals = [v for v in sdf.columns if 'val' in v or 'time' in v]
        for i, r in sig_info_df[sig_info_df['signal'] == sig].iterrows():
            vfield = vals[r['loc']]
            print(sig, vfield)
            dict1 = pd.Series({'pid_count':  sdf['pid'].nunique(), 'filed': vfield}, name=sig)
            if is_date(sdf[vfield], r['type']):
                dict1 = dict1.append(pd.Series({'count': sdf.shape[0], 'min': sdf[vfield].min(), 'max': sdf[vfield].max()}))
                dict1.rename(sig, inplace=True)
                dsc_date_list.append(dict1)
                sig_info_df.loc[(sig_info_df['signal'] == sig) & (sig_info_df['loc'] == r['loc']), 'type'] = '2'
            else:
                if is_yes_no(sdf[vfield]):
                    dict1 = dict1.append(sdf[vfield].astype(str).describe())
                    dict1.rename(sig, inplace=True)
                    dsc_yes_no_list.append(dict1)
                    sig_info_df.loc[sig_info_df['signal'] == sig, 'type'] = '3'
                    sig_info_df.loc[(sig_info_df['signal'] == sig) & (sig_info_df['loc'] == r['loc']), 'type'] = '3'
                else:
                    dict1 = dict1.append(sdf[vfield].describe())
                    dict1.rename(sig, inplace=True)
                    if r['type'] == '0':
                        dsc_numeric_list.append(dict1)
                    else:
                        dsc_category_list.append(dict1)
        del sdf

    summary_table_to_html(pd.DataFrame(dsc_numeric_list), output_path,  "numeric_summary.html")
    summary_table_to_html(pd.DataFrame(dsc_category_list), output_path, "category_summary.html")
    summary_table_to_html(pd.DataFrame(dsc_date_list), output_path, "dates_summary.html")
    summary_table_to_html(pd.DataFrame(dsc_empty_list), output_path, "empty_summary.html")
    summary_table_to_html(pd.DataFrame(dsc_yes_no_list), output_path, "yes_no_summary.html")
    return sig_info_df


def get_fixed_type(rep, sig_info_df, sig):
    sdf = rep.get_sig(sig)
    if sdf.shape[0] == 0:
        print('signal ' + sig + ' is empty')
        return sig_info_df
    vals = [v for v in sdf.columns if 'val' in v or 'time' in v]
    for i, r in sig_info_df[sig_info_df['signal'] == sig].iterrows():
        vfield = vals[r['loc']]
        print(sig, vfield)
        if is_date(sdf[vfield], r['type']):
            sig_info_df.loc[(sig_info_df['signal'] == sig) & (sig_info_df['loc'] == r['loc']), 'type'] = '2'
        else:
            if is_yes_no(sdf[vfield]):
                sig_info_df.loc[(sig_info_df['signal'] == sig) & (sig_info_df['loc'] == r['loc']), 'type'] = '3'
    del sdf
    return sig_info_df


def get_sig_stat(title, df, val_name, typ):
    if typ == '0':
        sig_stat, sig_hist_plot = get_histogram(title, df, val_name)
    elif typ == '1' or typ == '3':
        stat = [[df.shape[0], df['pid'].nunique(), df[val_name].nunique()]]
        sig_stat = pd.DataFrame(stat, columns=['count', 'pid_count', 'categories'], index=[title])
        if typ == '1' or df.shape[0] > 100000000:
            vc_top = df[val_name].value_counts(dropna=False, normalize=True)[0:10]
        else:
            vc_top = df[val_name].astype(str).value_counts(dropna=False, normalize=True)[0:10]
        sig_hist_plot = make_bar_plot(title,  vc_top)
    else:  # type == 2 --> date field
        df['year'] = (df[val_name]/10000).astype(int)
        sig_stat, sig_hist_plot = get_histogram(title, df, 'year')
    return sig_stat, sig_hist_plot


def get_sig_years(title, df, val_name, dates_list, typ):
    if len(dates_list) == 0:
        return None, None
    if typ == '0':
        year_stat, year_plot = get_year_stat(title, df, val_name, dates_list[0])
    else:
        year_stat, year_plot = get_year_count(title, df, val_name, dates_list[0])

    year_stat.reset_index(inplace=True)
    return year_stat, year_plot


def plot_single_signal(rep, sig, sig_info_df, output_path):
    print('plot_single_signal')
    sig_info = sig_info_df[sig_info_df['signal'] == sig]
    sig_hist_plots = []
    sig_stats = pd.DataFrame()
    year_plots = []
    year_stats = []
    sdf = rep.get_sig(sig)
    if sdf.shape[0] == 0:
        return {'signal': sig}
    vals = [v for v in sdf.columns if 'val' in v or 'time' in v]
    dates = [v for v in sdf.columns if 'date' in v]
    urlstr = io.StringIO()
    for i, r in sig_info.iterrows():
        vfield = vals[r['loc']]
        print(sig, vfield)
        sig_stat, sig_hist_plot = get_sig_stat(sig+'_'+vfield, sdf, vfield, r['type'])
        sig_stats = sig_stats.append(sig_stat)
        sig_hist_plots.append(sig_hist_plot)

        year_stat, year_plot = get_sig_years(sig+'_'+vfield, sdf, vfield, dates, r['type'])
        year_stats.append(year_stat)
        year_plots.append(year_plot)

        vc_file = sig+'_' + vfield + '_vc.html'
        vc_file = vc_file.replace('#', 'No')
        err_dict = check_vc(sig, sdf, vfield, os.path.join(output_path, vc_file), r['type'])
        link = '<a href="'+vc_file+'">' + vfield + ' - Value Counts list <br></a>'
        urlstr.write(link)

    out_file = os.path.join(output_path, sig + '.html')
    out_file = out_file.replace('#', 'No')
    sig_stats.to_html(out_file)
    plots = row(sig_hist_plots)
    html_plot1 = file_html(plots, CDN, sig)

    with open(out_file, 'a', encoding='utf-8') as f:
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
    return err_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', help="the repository file")
    parser.add_argument('--f_output',  help="output path")
    parser.add_argument('--f_signal', help="Signal name to create plots", default='All')
    parser.add_argument('--f_overwrite', action='store_true', help="Create new output files, default is to add if not exists")
    parser.add_argument('--f_only_summary', action='store_true', help="Create only summery tables")

    args = parser.parse_args()

    if not args.repository:
        raise Exception('no repository file supplied. Please supply one using --repository')
    if not args.f_output:
        raise Exception('no output ptah supplied. Please supply one using --f_output')
    else:
        if not os.path.exists(args.f_output):
            os.makedirs(args.f_output)

    rep_file = args.repository
    rep_path = os.path.dirname(rep_file)
    sigs_file = os.path.join(rep_path, os.path.basename(rep_file).split('.')[0]+'.signals')
    sigs_df = read_signal_file(sigs_file)

    rep = med.PidRepository()
    print(sigs_df.shape[0])
    rep.read_all(rep_file, [], ['GENDER'])
    print(med.cerr())
    exst = os.listdir(args.f_output)

    if args.f_signal == 'All':
        sigs = sigs_df['signal'].unique().tolist()
        # sigs = ['BDATE', 'ALKP', 'ALT', 'B12', 'Bands#', 'ETHNICITY', 'Urine_RBC', 'MALE_PARTNER_YN']
        fixed_sigs_df = summary_tables(rep, sigs_df, sigs, args.f_output)
    else:
        sigs = [args.f_signal]
        fixed_sigs_df = get_fixed_type(rep, sigs_df, args.f_signal)

    err_list = []
    if args.f_only_summary:
        exit()

    for sig in sigs:
        print(sig)
        if (args.f_overwrite==False) and sig+'.html' in exst:
            print('summary files for signal ' + sig + ' already exist')
            continue
        #if sig.startswith('RC') or sig.startswith('Drug'):
        #    print('Skipping too big signals' + sig)
        #    continue
        err_dct = plot_single_signal(rep, sig, fixed_sigs_df,  args.f_output)
        print(err_dct)
        err_list.append(err_dct)
    if args.f_signal == 'All':
        #errors_df = pd.concat([errors_df, pd.DataFrame(err_list).set_index('signal')], axis=1, sort=False)
        errors_df = pd.DataFrame(err_list).set_index('signal')
        errors_df.dropna(how='all', inplace=True)
        table_to_html(errors_df, args.f_output, 'problems_list.html')
    print('DONE')
