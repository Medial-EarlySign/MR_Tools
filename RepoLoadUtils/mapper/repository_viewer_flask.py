from flask import Flask, render_template, request
import os
import sys
import socket
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.models import Row, GridBox, Column
from repository_connect import get_all_signals, default_sig, get_signal
from plots_and_widgets import plot_compare, get_value_count, get_describe_table, get_describe_df, get_stat_3_plots, get_sig_value_count, plot_signal_dist
app = Flask(__name__)


def get_grid_box(plot1, vc_table, plot_list):
    cols = len(plot_list)
    tups = [(plot1, 1, 1), (vc_table, 1, 2)]
    for i, plt in zip(range(0, cols), plot_list):
        tups.append((plot_list[i], 2, i+1))
    gb = GridBox(children=tups, spacing=5)

    return gb


def get_code_list(full_name_list):
    cd_list = []
    for cd_dsc in full_name_list:
        cd = cd_dsc.split('\t')[0]
        cd_list.append(cd)
    return cd_list


def get_age_group_map(groups):
    age_group_map = {}
    for j in range(1, len(groups)):
        for i in range(groups[j - 1], groups[j]):
            age_group_map[i] = str(groups[j - 1]) + '-' + str(groups[j])
    age_group_map = pd.Series(age_group_map)
    last = age_group_map.iloc[-1]
    age_group_map.replace({last: str(groups[-2]) + '+'}, inplace=True)
    return age_group_map


@app.route("/by_age")
def by_age():
    global curr_sig
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    sig_df, unit = get_signal(curr_sig)
    print(sig_df.columns)
    dob_df, _ = get_signal('BDATE')
    dob_df.rename(columns={'date': 'dob'}, inplace=True)
    sig_df = sig_df.merge(dob_df, on='pid', how='left')
    print(sig_df.columns)
    sig_df['year'] = (sig_df['date'] / 10000).astype(int)
    sig_df['byear'] = (sig_df['dob'] / 10000).astype(int)
    sig_df['age'] = sig_df['year'] - sig_df['byear']
    # more accurate but takes too lon...
    #sig_df['date'] = pd.to_datetime(sig_df['date'], format='%Y%M%d')
    #sig_df['dob'] = pd.to_datetime(sig_df['dob'], format='%Y%M%d')
    #sig_df['age'] = round((sig_df['date'] - sig_df['dob']).dt.days / 365, 0)
    vals_cols = [x for x in sig_df.columns if 'val' in x]
    val = vals_cols[0]
    age_map = get_age_group_map([0, 5, 18, 65, 150])
    sig_df['age_group'] = sig_df['age'].map(age_map)
    groups = age_map.unique().tolist()
    curr_ag = request.args.get('age_group')
    if not curr_ag:
        curr_ag = groups[0]
    stat_df = get_describe_df(sig_df, 'age_group', val)
    yr_table = get_describe_table(stat_df, 'age_group')
    plot_list = get_stat_3_plots(stat_df, 'purple')
    comp_plot = plot_compare(sig_df, 'age_group', val)
    vc_table = get_value_count(sig_df, val)

    gb = get_grid_box(comp_plot, vc_table, plot_list)
    script, div = components(gb)
    ag_comp_plot = plot_compare(sig_df, 'age_group',  val, [curr_ag])
    vc_table = get_value_count(sig_df[sig_df['age_group'] == curr_ag], val)
    ag_script, ag_div = components(Column(ag_comp_plot, vc_table))
    t_script, t_div = components(yr_table)

    html = render_template(
        'rep_age_template.html',
        plot_script=script,
        plot_div=div,
        curr_sig=curr_sig,
        table_script=t_script,
        table_div=t_div,
        ag_script=ag_script,
        ag_div=ag_div,
        js_resources=js_resources,
        css_resources=css_resources,
        curr_ag=curr_ag, groups=groups)

    return encode_utf8(html)


@app.route("/by_gender")
def by_gender():
    global curr_sig
    print(curr_sig)
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    sig_df, unit = get_signal(curr_sig)
    gender_df, _ = get_signal('GENDER')
    gender_df.rename(columns={'val0': 'gender'}, inplace=True)
    gender_df['gender'].cat.remove_unused_categories(inplace=True)
    sig_df = sig_df.merge(gender_df, on='pid', how='left')
    vals_cols = [x for x in sig_df.columns if 'val' in x]
    val = vals_cols[0]
    stat_df = get_describe_df(sig_df, 'gender', val)
    yr_table = get_describe_table(stat_df, 'gender')
    plot_list = get_stat_3_plots(stat_df, 'green')
    comp_plot = plot_compare(sig_df, 'gender', val)
    vc_table = get_value_count(sig_df, val)
    gb = get_grid_box(comp_plot, vc_table, plot_list)
    script, div = components(gb)

    # mn_script, mn_div = components(Row(mn_plot_list[0], mn_plot_list[1], mn_plot_list[2]))
    t_script, t_div = components(yr_table)
    html = render_template(
        'rep_gender_template.html',
        plot_script=script,
        plot_div=div,
        curr_sig=curr_sig,
        table_script=t_script,
        table_div=t_div,
        js_resources=js_resources,
        css_resources=css_resources)
    return encode_utf8(html)


@app.route("/by_year")
def by_year():
    global curr_sig
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    sig_df, unit = get_signal(curr_sig)
    sig_df['year'] = (sig_df['date']/10000).astype(int)
    sig_df['month'] = ((sig_df['date'] - sig_df['year']*10000)/100).astype(int)
    years = sig_df['year'].unique().tolist()
    years.sort()
    curr_year = request.args.get('year')
    if not curr_year:
        curr_year = years[int(len(years) / 2)]
    curr_year = int(curr_year)
    vals_cols = [x for x in sig_df.columns if 'val' in x]
    val = vals_cols[0]
    #for val in vals_cols:
    stat_df = get_describe_df(sig_df, 'year', val)
    yr_table = get_describe_table(stat_df, 'year')
    plot_list = get_stat_3_plots(stat_df, 'blue')
    comp_plot = plot_compare(sig_df, 'year', val)
    vc_table = get_value_count(sig_df, val)
    gb = get_grid_box(comp_plot, vc_table, plot_list)
    script, div = components(gb)

    mn_stat_df = get_describe_df(sig_df, 'month', val)
    mn_plot_list = get_stat_3_plots(mn_stat_df, 'red')
    yr_comp_plot = plot_compare(sig_df, 'year', val, [curr_year])
    vc_table = get_value_count(sig_df[sig_df['year'] == curr_year], val)
    gb = get_grid_box(yr_comp_plot, vc_table, mn_plot_list)
    mn_script, mn_div = components(gb)

    t_script, t_div = components(yr_table)
    html = render_template(
        'rep_years_template.html',
        plot_script=script,
        plot_div=div,
        curr_sig=curr_sig,
        table_script=t_script,
        table_div=t_div,
        mn_script=mn_script,
        mn_div=mn_div,
        js_resources=js_resources,
        css_resources=css_resources,
        curr_year=curr_year, years=years)
    return encode_utf8(html)


@app.route('/', methods=['GET', 'POST'])
def index():
    global curr_sig
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    #if request.method == 'POST':
    req_sig = request.args.get('Signals')
    if req_sig:
        curr_sig = req_sig
    print(curr_sig)

    sig_df, unit = get_signal(curr_sig)
    print(sig_df)
    res_vc_table = get_sig_value_count(sig_df)
    res_dict = plot_signal_dist(curr_sig, sig_df)
    print('num of cols=' + str(len(res_dict.keys())))
    cols = len(res_dict.keys())
    tups = []
    for i, key in zip(range(1, cols+1), res_dict.keys()):
        tups.append((res_dict[key][1], 1, i))
        tups.append((res_dict[key][0], 2, i))
        tups.append((res_vc_table[key], 3, i))
    gb = GridBox(children=tups, spacing=5)
    script, div = components(gb)

    html = render_template(
        'rep_main_template.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
        curr_sig=curr_sig,
        sig_list=all_signals,
        sig_unit=unit)
    return encode_utf8(html)


global curr_sig
all_signals = get_all_signals()
print(all_signals)
curr_sig = default_sig
print(curr_sig)
hostname = socket.gethostname()
app.run(host=hostname, port=5001, debug=True)
