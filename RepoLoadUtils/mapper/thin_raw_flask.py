from flask import Flask, render_template, request
import os
import sys
import socket
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import is_nan
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.models import Row, GridBox
from staging_connect import get_all_labs_sql, get_data_sql, default_labs
from search_and_save import get_mapped, read_medial_signal,  map_signal_post, map_units_post, get_units_transforms
from search_and_save import TeamForm, MemberForm, UnitsForm, UnitsTeamForm
from plots_and_widgets import plot_compare_dist, plot_compare_units, get_stats_units, get_value_count, get_year_stat, get_month_stat

app = Flask(__name__)
#app.config['SERVER_NAME'] = '*:5000'

df_dict = {}

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

    codes_df = get_data_sql(curr_labs)
    codes_df['year'] = codes_df['date1'].astype(str).str[0:4].astype(int)
    codes_df['month'] = codes_df['date1'].astype(str).str[5:7].astype(int)
    years = codes_df['year'].unique().tolist()
    years.sort()
    curr_year = request.args.get('year')
    if not curr_year:
        curr_year = years[int(len(years) / 2)]
    curr_year = int(curr_year)
    print(curr_year)
    yr_table, plot_list = get_year_stat(codes_df)
    mn_plot_list = get_month_stat(codes_df, curr_year)
    script, div = components(Row(plot_list[0], plot_list[1], plot_list[2]))
    mn_script, mn_div = components(Row(mn_plot_list[0], mn_plot_list[1], mn_plot_list[2]))
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

    codes_df = get_data_sql(curr_labs)
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
    codes_df = get_data_sql(curr_labs)
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

    codes_df = get_data_sql(curr_labs)
    curr_codes_list = request.args.getlist('code')
    if not curr_codes_list:
        curr_codes_list = curr_labs

    plot = plot_compare_dist(codes_df, curr_codes_list, curr_labs)
    script, div = components(plot)
    filter_list = get_code_list(curr_codes_list)

    df1 = codes_df[codes_df['code'].isin(filter_list)]
    vc_table = get_value_count(df1, 'value')
    vc_script, vc_div = components(vc_table)
    print(curr_codes_list)
    html = render_template(
        'main_template.html',
        plot_script=script,
        plot_div=div,
        vc_script=vc_script,
        vc_div=vc_div,
        js_resources=js_resources,
        css_resources=css_resources,
        feature_names=curr_labs, current_feature_name=curr_codes_list,
        lab_list=all_labs)
    return encode_utf8(html)


def read_tsv(file_name, path, names=None, header=1, dtype=None):
    full_file = os.path.join(path, file_name)
    df = pd.read_csv(full_file, sep='\t', names=names, header=header, dtype=dtype)
    return df


def get_map():
    map_df = pd.read_csv('H:\\MR\\Tools\\RepoLoadUtils\\thin1801\\thin_signal_mapping.csv', sep='\t')
    map_df = map_df[(map_df['type'] == 'numeric') & (map_df['source_file'] == 'ahd')]
    return map_df


def get_all_labs():
    map_df = get_map()
    return map_df['signal'].unique().tolist()


def get_data(sig):
    out_folder = 'X:\\Thin_2018_Loading'
    source_path = os.path.join(out_folder, 'ahd_files')
    source_files = os.listdir(source_path)
    thin_map = get_map()
    sig_maps = thin_map[thin_map['signal'] == sig]
    for _, map_dict in sig_maps.iterrows():
        ahdcode = '' if is_nan(map_dict['ahdcode']) else str(int(map_dict['ahdcode']))
        readcode = '' if is_nan(map_dict['readcode']) else map_dict['readcode']
        value_field = map_dict['value_field']
        val_cols = []
        files = [s for s in source_files if readcode in s and ahdcode in s]
        df_list = []
        for file in files:
            try:
                print('  reading file ' + file)
                one_df = read_tsv(file, source_path,
                                  names=['medialid', 'eventdate', 'data1', 'data2', 'data3', 'data4', 'data5',
                                             'data6', 'filename'],
                                  header=None)
                df_list.extend(one_df.to_dict(orient='recoreds'))
            except ValueError as ve:
                print('Error In reading file %s  for signal %s' % (file, map_dict['signal']))
                # traceback.print_exc()
                # raise
        sig_map_df = pd.DataFrame(df_list)
    sig_map_df = sig_map_df[(sig_map_df['eventdate'].notnull()) & (sig_map_df['medialid'].notnull())]
    print(sig_map_df)


global curr_labs
all_labs = get_all_labs()
curr_labs = ['Glucose\tGlucose\t1000']
get_data('Glucose')
hostname = socket.gethostname()
app.run(host=hostname, port=5000, debug=True)