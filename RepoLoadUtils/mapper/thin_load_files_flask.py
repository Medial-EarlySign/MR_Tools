from flask import Flask, render_template, request
import os
import sys
import socket
import pandas as pd
from math import pi
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import is_nan
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.models import Row, GridBox, ColumnDataSource
from search_and_save import get_mapped, read_medial_signal,  map_signal_post, map_units_post, get_units_transforms
from search_and_save import TeamForm, MemberForm, UnitsForm, UnitsTeamForm
from plots_and_widgets import plot_compare_dist, plot_compare_units, get_stats_units, get_value_count
from bokeh.models.widgets import MultiSelect, TableColumn, DataTable, NumberFormatter


app = Flask(__name__)
#app.config['SERVER_NAME'] = '*:5000'

df_dict = {}

def make_bar_plot(title, count_ser, color='blue',  plot_width=1000, plot_height=600): # , pdf, cdf):
    vals = list(count_ser.index.astype(str))
    counts = count_ser.values
    p = figure(x_range=vals, title=title, tools="pan,wheel_zoom,box_zoom,reset", background_fill_color="#fafafa",
               plot_width=plot_width, plot_height=plot_height)
    p.vbar(x=vals, top=counts, width=0.4, color=color)
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    if p.legend:
        p.legend.location = "center_right"
        p.legend.background_fill_color = "#fefefe"
    #p.xaxis.axis_label = 'x'
    #p.yaxis.axis_label = 'Pr(x)'
    p.grid.grid_line_color="white"
    p.xaxis.major_label_orientation = pi/4
    return p


def get_dist_plot(sig, sig_df):
    vc_df = pd.concat([sig_df['value'].value_counts(dropna=False).rename('count'),
                       sig_df['value'].value_counts(dropna=False, normalize=True).rename('per')],
                      axis=1, sort=False)
    vc_df['per'] = (vc_df['per'] * 100).round(2)
    vc_df = vc_df.reset_index() #.rename(columns={'index': channel})
    vc_df.sort_values(by='index', inplace=True)
    first = vc_df[vc_df['per'] >= 0.1].index[0]
    last = vc_df[vc_df['per'] >= 0.1].index[-1]
    vc_df_cut = vc_df.loc[first:last]
    sig_hist_plot = make_bar_plot(sig, vc_df_cut['count'])
    return sig_hist_plot


def get_year_plot(sig, sdf):
    #sdf['year'] = (sdf['date1'].astype(int) / 10000).astype(int)
    #sdf['year'] = (sdf['date1'].str[0:4].astype(int) / 10000).astype(int)
    stat_list = []
    for yr, yr_df in sdf.groupby('year'):
        stat = {'year': yr, 'count': yr_df.shape[0], 'pid_count': yr_df['pid'].nunique()}
        stat['mean'] = yr_df['value'].mean()
        stat['median'] = yr_df['value'].median()
        stat['std'] = yr_df['value'].std()
        stat['min'] = yr_df['value'].min()
        stat['max'] = yr_df['value'].max()
        stat_list.append(stat)

    year_stat = pd.DataFrame(stat_list)
    year_stat.set_index('year', inplace=True)
    plotlist = []
    plotlist.append(make_bar_plot(sig + ' ' + ' count', year_stat['count'], color='steelblue',  plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot(sig + ' ' + ' count per pid', year_stat['count'] / year_stat['pid_count'],  color='steelblue', plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot(sig + ' ' + ' mean', year_stat['mean'],  color='steelblue', plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot(sig + ' ' + ' median', year_stat['median'],  color='steelblue', plot_width=300, plot_height=300))

    print(year_stat)
    source = ColumnDataSource(year_stat)

    columns = [
        TableColumn(field="year", title="Year"),
        TableColumn(field="count", title="Count"),
        TableColumn(field="pid_count", title="Pid count"),
        TableColumn(field="mean", title="Mean"),
        TableColumn(field="50%", title="Median"),
        TableColumn(field="std", title="std"),
        TableColumn(field="min", title="Min"),
        TableColumn(field="max", title="Max"),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=280)
    # year_stat.reset_index(inplace=True)
    return data_table, plotlist


def get_month_plots(df, yr):
    print('In get_month_stat')
    stat_list = []
    plotlist = []
    yr_df = df[df['year'] == yr]
    #yr_df['month'] = yr_df['date1'].str[6:8]
    for mn, mn_df in yr_df.groupby('month'):
        val_ser = mn_df['value']
        stat = {'month': mn, 'count': mn_df.shape[0],'pid_count': len(mn_df['pid'].unique()), 'mean': val_ser.mean(),
                 'median': val_ser.median(), 'std': val_ser.std(),
                 'min': val_ser.min(), 'max': val_ser.max()}
        stat_list.append(stat)
    mn_stat = pd.DataFrame(stat_list)
    mn_stat.set_index('month', inplace=True)

    plotlist.append(make_bar_plot('count per month for year ' + str(yr), mn_stat['count'], color='firebrick', plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot('count per month pid for year ' + str(yr), mn_stat['count'] / mn_stat['pid_count'], color='firebrick', plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot('mean for year=' + str(yr), mn_stat['mean'], color='firebrick', plot_width=300, plot_height=300))
    plotlist.append(make_bar_plot('median for year=' + str(yr), mn_stat['median'], color='firebrick', plot_width=300, plot_height=300))
    return plotlist


def get_data_files(sig):
    if sig in df_dict.keys():
        df = df_dict[sig]
    else:
        df = get_data(sig)
        # remove outliers and nulls
        df['value'] = pd.to_numeric(df['value'], errors='coerse')
        df = df[df['value'].notnull()]
        df = df[(df['value'] > df['value'].quantile(0.01)) & (df['value'] < df['value'].quantile(0.99))]
        df_dict[sig] = df.copy()  # save in mem to improve performance
    #df['unit'] = all_df['unit'].fillna('NaN')
    return df


def get_code_list(full_name_list):
    cd_list = []
    for cd_dsc in full_name_list:
        cd = cd_dsc.split('\t')[0]
        cd_list.append(cd)
    return cd_list


@app.route("/by_year")
def by_year():
    global curr_labs
    print(curr_labs)
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    curr_lab = curr_labs[0]
    codes_df = get_data_files(curr_lab)
    codes_df['year'] = codes_df['date1'].astype(str).str[0:4].astype(int)
    codes_df['month'] = codes_df['date1'].astype(str).str[5:7].astype(int)
    years = codes_df['year'].unique().tolist()
    years.sort()
    curr_year = request.args.get('year')
    if not curr_year:
        curr_year = years[int(len(years) / 2)]
    curr_year = int(curr_year)
    print(curr_year)
    yr_table, plot_list = get_year_plot(curr_lab, codes_df)
    mn_plot_list = get_month_plots(codes_df, curr_year)
    script, div = components(Row(plot_list[0], plot_list[1], plot_list[2], plot_list[3]))
    mn_script, mn_div = components(Row(mn_plot_list[0], mn_plot_list[1], mn_plot_list[2], mn_plot_list[3]))
    t_script, t_div = components(yr_table)
    html = render_template(
        'years_template.html',
        plot_script=script,
        plot_div=div,
        table_script=t_script,
        table_div=t_div,
        mn_script=mn_script,
        mn_div=mn_div,
        js_resources=js_resources,
        css_resources=css_resources,
        curr_year=curr_year, years=years)
    return encode_utf8(html)


@app.route("/units")
def units():
    global curr_labs
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    codes_df = get_data_files(curr_labs)
    units = codes_df['unit'].unique().tolist()
    print(units)
    unit_stat_table = get_stats_units(codes_df, units)
    curr_units = request.args.getlist('unit')
    if not curr_units:
        curr_units = units
    plot = plot_compare_units(codes_df, curr_units, units)
    df1 = codes_df[codes_df['unit'].isin(curr_units)]
    vc_table = get_value_count(df1, 'value')

    #script, div = components(Column(plot, unit_stat_table))
    gb = GridBox(children=[(plot, 1, 1), (vc_table, 1, 2), (unit_stat_table, 2, 1)], spacing=5)
    script, div = components(gb)
    html = render_template(
        'unit_template.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
        curr_units=curr_units, units=units,
        lab_list=curr_labs)
    return encode_utf8(html)


@app.route('/mapping', methods=['GET', 'POST'])
def mapping():
    global curr_labs
    codes_df = get_data_files(curr_labs)
    sigs_units = read_medial_signal()

    sigs_units_map = sigs_units.set_index('Name')['FinalUnit']
    sigs_units_map.set_value('Select', 'Unknown')
    signal = 'Select'

    if request.method == 'POST':
        dct = request.form.to_dict()
        if 'edit' in dct.keys():
            signal = map_signal_post(dct)
        if 'unit_map' in dct.keys():
            unit_map = map_units_post(dct)

    teamform = TeamForm()
    teamform.title.data = "Labs"  # change the field's data
    mapped = get_mapped()
    mapping_map = mapped.set_index('code')['signal']
    for lb in curr_labs:
        splt = lb.split('\t')
        lab_form = MemberForm()
        lab_form.code = splt[0]
        lab_form.desc = splt[1]
        lab_form.count = splt[2]
        if lab_form.code in mapping_map.index:
            signal = mapping_map[lab_form.code]
            teamform.signal.default = signal
            teamform.process()

        teamform.labs_members.append_entry(lab_form)
    teamform.unit = sigs_units_map[signal]
    #if request.method != 'POST':
    unit_map = get_units_transforms(signal)
    unit_map.set_index('unit', inplace=True)
    unittaemform = UnitsTeamForm()
    for un in codes_df['unit'].unique():
        unit_form = UnitsForm()
        x = codes_df[codes_df['unit'] == un]['value']
        stat = x.describe()
        unit_form.signal = signal
        unit_form.unit = un
        unit_form.count = stat['count']
        unit_form.mean = stat['mean']
        unit_form.median = stat['50%']
        unit_form.std = stat['std']
        unit_form.min = stat['min']
        unit_form.max = stat['max']
        if un in unit_map.index:
            unit_form.muliplier = unit_map.loc[un]['muliplier']
            unit_form.addition = unit_map.loc[un]['addition']
            unit_form.round = unit_map.loc[un]['round']
            if is_nan(unit_map.loc[un]['final_round']):
                unit_form.final_round = None
            else:
                unit_form.final_round = unit_map.loc[un]['final_round']
        else:
            unit_form.muliplier = 1
            unit_form.addition = 0
            unit_form.round = 0.01
            unit_form.final_round = None
        unittaemform.units_members.append_entry(unit_form)

    return render_template('mapping_template.html', teamform=teamform, unitform=unittaemform)



@app.route('/', methods=['GET', 'POST'])
def index():
    global curr_labs
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    #if request.method == 'POST':
    req_labs = request.args.getlist('Labs')
    if req_labs:
        curr_labs = req_labs
    if request.args.get('Map') == 'Map':
        html = mapping()
        return encode_utf8(html)


    print(curr_labs)
    curr_lab = curr_labs[0]
    codes_df = get_data_files(curr_lab)
    #curr_codes_list = request.args.getlist('code')
    #if not curr_codes_list:
    #    curr_codes_list = curr_labs

    #plot = plot_compare_dist(codes_df, curr_codes_list, curr_labs)
    plot = get_dist_plot(curr_lab, codes_df)
    script, div = components(plot)
    #filter_list = get_code_list(curr_codes_list)

    #df1 = codes_df[codes_df['code'].isin(filter_list)]
    vc_table = get_value_count(codes_df, 'value')
    vc_script, vc_div = components(vc_table)
    #print(curr_codes_list)
    html = render_template(
        'main_template.html',
        plot_script=script,
        plot_div=div,
        vc_script=vc_script,
        vc_div=vc_div,
        js_resources=js_resources,
        css_resources=css_resources,
        feature_names=curr_labs, current_feature_name=curr_labs,
        lab_list=all_labs)
    return encode_utf8(html)


def read_tsv(file_name, path, names=None, header=1, dtype=None):
    full_file = os.path.join(path, file_name)
    df = pd.read_csv(full_file, sep='\t', names=names, header=header, dtype=dtype)
    return df


def get_map():
    map_df = pd.read_csv('H:\\MR\\Tools\\RepoLoadUtils\\thin20_etl\\thin_signal_mapping.csv', sep='\t')
    map_df = map_df[(map_df['type'] == 'numeric') & (map_df['source'] == 'thinlabs')]
    return map_df


def get_all_labs():
    map_df = get_map()
    return map_df['signal'].unique().tolist()


def get_data(sig):
    out_folder = 'W:\\Users\\Tamar\\thin20_load'
    source_path = os.path.join(out_folder, 'FinalSignals')
    source_files = os.listdir(source_path)
    sig_files = [x for x in source_files if x.startswith(sig+'_thinlabs')]
    all_sig = pd.DataFrame()
    for f in sig_files:
        ff = os.path.join(source_path,f)
        df = pd.read_csv(ff, sep='\t', usecols=[0, 2, 3], names=['pid', 'date1', 'value'])
        all_sig = all_sig.append(df)
        break
    return all_sig


global curr_labs
all_labs = get_all_labs()
curr_labs = ['BMI']
#get_data(curr_labs)
hostname = socket.gethostname()
app.run(host=hostname, port=5000, debug=True)