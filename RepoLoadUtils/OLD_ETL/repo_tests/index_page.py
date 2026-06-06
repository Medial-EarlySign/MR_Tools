import argparse
import os
import sys
import io
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import fixOS
from summary_to_html import get_summary_df, calc_outliers, table_to_html, file_types
from statistics import mode

# num_file = 'numeric_summary.html'
# cat_file = 'category_summary.html'
# time_file = 'dates_summary.html'
# yn_file = 'yes_no_summary.html'
# empty_file = 'empty_summary.html'

prop_file = 'problems_list.html'
yr_prob_file = 'years_problems.html'


def find_year_range(df):
    start = df['year'].min()
    end = df['year'].max()
    for i, r in df.iterrows():
        if r['count'] > df['count'].median() * 0.5:
            start = r['year']
            break
    if df.iloc[-1]['count'] < df['count'].mean() * 0.8:
        end = df.iloc[-2]['year']
    return start, end


def index_to_html(summry_df, rep_loc, outpath):
    num_df = summry_df[summry_df['type'] == 'n']
    cat_df = summry_df[summry_df['type'] == 'c']
    start_range = []
    end_range = []
    # Get patient number by from GENDER sugnal
    tot_pid_count = summry_df[summry_df['signal'] == 'GENDER'].iloc[0]['pid_count']
    errror_list = []
    for sig in num_df['signal'].values:
        #for sig in ['BMI']:
        dct = {'signal': sig}
        year_file = os.path.join(outpath, sig.replace('#', 'No') + '_years.csv')
        if not os.path.exists(year_file):
            continue
        year_df = pd.read_csv(year_file, sep='\t')
        start_year, end_year = find_year_range(year_df)
        print(sig, start_year, end_year)
        start_range.append(start_year)
        end_range.append(end_year)

        year_df_full = year_df[(year_df['year']>= start_year) & (year_df['year'] <= end_year)].copy()
        year_df_full['norm_count'] = year_df_full['count']/year_df_full['pid_count']
        thhold = 0.2
        year_df_full['count_diff'] = (year_df_full['norm_count']-year_df_full['norm_count'].mean()).abs()/year_df_full['norm_count'].mean() < thhold
        year_df_full['mean_diff'] = (year_df_full['mean']-year_df_full['mean'].mean()).abs()/year_df_full['mean'].mean() < thhold
        year_df_full['median_diff'] = (year_df_full['median']-year_df_full['median'].mean()).abs()/year_df_full['median'].mean() < thhold
        if not year_df_full['count_diff'].all():
            dct['count problem'] = 1
        if not year_df_full['mean_diff'].all():
            dct['mean problem'] = 1
        if not year_df_full['median_diff'].all():
            dct['meadin problem'] = 1
        errror_list.append(dct)
        print(dct)

    for sig in cat_df['signal'].values:
        # for sig in ['Spo2']:
        dct = {'signal': sig}
        year_file = os.path.join(outpath, sig.replace('#', 'No') + '_years.csv')
        if not os.path.exists(year_file):
            continue
        year_df = pd.read_csv(year_file, sep='\t')
        start_year, end_year = find_year_range(year_df)
        print(sig, start_year, end_year)
        start_range.append(start_year)
        end_range.append(end_year)
        year_df_full = year_df[(year_df['year'] >= start_year) & (year_df['year'] <= end_year)].copy()
        year_df_full['norm_count'] = year_df_full['count'] / year_df_full['pid_count']
        thhold = 0.2
        year_df_full['count_diff'] = (year_df_full['norm_count'] - year_df_full['norm_count'].mean()).abs() / year_df_full['norm_count'].mean() < thhold

        if not year_df_full['count_diff'].all():
            dct['count problem'] = 1

        errror_list.append(dct)
        print(dct)

    errors_df = pd.DataFrame(errror_list)
    subset = errors_df.columns.tolist()
    subset.remove('signal')
    errors_df.dropna(subset=subset, how='all', inplace=True)
    table_to_html(errors_df, outpath, yr_prob_file)

    sig_num = summry_df['signal'].nunique()
    lines = ['<H2> Repository: ' + rep_loc + '</H2>']
    lines.append('<H3> Number of patients: ' + str(tot_pid_count) + '</H3>')
    lines.append('<H3> Number of Signals: ' + str(sig_num) + '</H3>')
    lines.append('<H3> Years: ' + str(mode(start_range)) + '-' + str(mode(end_range)) + '</H3>')
    lines.append('<ul style = "list-style-type:square;" >')
    lines.append('<li><a href="' + file_types['n'] + '" target="_blank">Numeric Signals</li>')
    lines.append('<li><a href="' + file_types['c'] + '" target="_blank">Categories Signals</li>')
    lines.append('<li><a href="' + file_types['d'] + '" target="_blank">Time Signals</li>')
    lines.append('<li><a href="' + file_types['y'] + '" target="_blank">yes/no Signals</li>')
    lines.append('<li><a href="' + file_types['e'] + '" target="_blank">empty Signals</li>')
    lines.append('<li></li>')
    lines.append('<li><a href="' + prop_file + '" target="_blank">Problems Summary</li>')
    lines.append('<li><a href="' + yr_prob_file + '" target="_blank">Years related problems summary</li>')
    lines.append('</ul>')
    htmlstr = io.StringIO()
    for ln in lines:
        htmlstr.write(ln)

    with open(os.path.join(outpath, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(htmlstr.getvalue())
    f.close()
    print(sig_num)


if __name__ == '__main__':
    output_path = fixOS('/nas1/Work/Users/Tamar/kpnw_load/outputs/')
    rep_loc = fixOS('/home/Repositories/KPNW/kpnw_apr20/')
    sum_df = get_summary_df(output_path)
    #sum_df = calc_outliers(sum_df, output_path)
    index_to_html(sum_df,rep_loc, output_path)
