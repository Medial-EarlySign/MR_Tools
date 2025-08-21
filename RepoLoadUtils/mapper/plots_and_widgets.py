from bokeh.plotting import figure
from bokeh.models.widgets import MultiSelect, TableColumn, DataTable, NumberFormatter
from bokeh.models import ColumnDataSource
from bokeh.transform import dodge
from bokeh.core.properties import value
import numpy as np
import pandas as pd
from plots_utils import get_histogram
from math import pi


colors = ['red', 'blue', 'green', 'maroon', 'teal',  'darkorange', 'mediumvioletred', 'turquoise', 'olive', 'orange',
          'slateblue', 'seagreen', 'magenta', 'indigo']


def plot_compare_dist(df, code_list, all_codes):
    real_codes = [x.split('\t')[0] for x in code_list]
    ren_dict = {x.split('\t')[0]:x for x in code_list}
    df1 = df[df['code'].isin(real_codes)].copy()
    df1['code'].replace(ren_dict, inplace=True)
    p = plot_compare(df1, 'code', 'value')

    # p = figure(title='Results distribution', tools="pan,wheel_zoom,box_zoom,reset,save", background_fill_color='#fafafa',
    #            plot_width=1000, plot_height=500, )
    # for cd_dsc in code_list:
    #     color_index = all_codes.index(cd_dsc)
    #     cd = cd_dsc.split('\t')[0]
    #     x = df[df['code'] == cd]['value']
    #     lable = cd_dsc.split('\t')[1] + '_' + cd_dsc.split('\t')[0] + '(' + cd_dsc.split('\t')[2] + ')'
    #     bins = len(x.unique())
    #     color = colors[color_index]
    #     hist, edges = np.histogram(x, density=False, bins=bins)
    #     p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
    #            fill_color=color, line_color='white', alpha=0.5, legend=str(lable))
    #
    # p.y_range.start = 0
    # p.legend.location = 'top_right'
    # p.legend.background_fill_color = '#fefefe'
    # p.grid.grid_line_color = 'white'
    return p


def plot_compare_dist(df, sig):

    p = plot_compare(df1, 'code', 'value')

    # p = figure(title='Results distribution', tools="pan,wheel_zoom,box_zoom,reset,save", background_fill_color='#fafafa',
    #            plot_width=1000, plot_height=500, )
    # for cd_dsc in code_list:
    #     color_index = all_codes.index(cd_dsc)
    #     cd = cd_dsc.split('\t')[0]
    #     x = df[df['code'] == cd]['value']
    #     lable = cd_dsc.split('\t')[1] + '_' + cd_dsc.split('\t')[0] + '(' + cd_dsc.split('\t')[2] + ')'
    #     bins = len(x.unique())
    #     color = colors[color_index]
    #     hist, edges = np.histogram(x, density=False, bins=bins)
    #     p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
    #            fill_color=color, line_color='white', alpha=0.5, legend=str(lable))
    #
    # p.y_range.start = 0
    # p.legend.location = 'top_right'
    # p.legend.background_fill_color = '#fefefe'
    # p.grid.grid_line_color = 'white'
    return p


def is_categorial(ser):
    if len(ser.unique()) == 2:  # yes/no
        return True
    if ser.dtype not in [pd.np.dtype('float64'), pd.np.dtype('float32'), pd.np.dtype('int16')]:
        return True
    return False


def plot_signal_dist(sig, df):
    res_dict = {}
    vals_cols = [x for x in df.columns if 'val' in x]
    for value_filed in vals_cols:
        if is_categorial(df[value_filed]):
            res_dict[value_filed] = plot_cat_dict(sig, df, value_filed)
        else:
            res_dict[value_filed] = plot_numeric_dist(sig, df, value_filed)
    return res_dict


def plot_cat_dict(sig, df, value_field):
    vc = df[value_field].value_counts()
    sig_hist_plot = make_bar_plot(sig, vc, 'seagreen')
    stat = {'count': df.shape[0], 'pid_count': len(df['pid'].unique()), 'cat_count': len(vc.index)}
    sig_stat = pd.DataFrame([stat])
    source = ColumnDataSource(sig_stat)

    columns = [
        TableColumn(field="count", title="Count"),
        TableColumn(field="pid_count", title="PIDs Count"),
        TableColumn(field="cat_count", title="# categories"),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=80)
    return sig_hist_plot, data_table


def plot_numeric_dist(sig, df, value_filed):
    sig_stat, sig_hist_plot = get_histogram(sig+'='+value_filed, df, value_filed)
    sig_stat['signal'] = sig
    data_table = get_describe_num_table(sig_stat, 'signal')
    return sig_hist_plot, data_table


def plot_comp_cat(df, filed_name, value_field, sub_list=[]):
    df[filed_name] = df[filed_name].astype(str)
    if len(sub_list) != 0:
        sub_list = [str(s) for s in sub_list]
        df = df[df[filed_name].isin(sub_list)]
    grp = pd.pivot_table(df, values='pid', index=[value_field], columns=[filed_name], aggfunc=len)
    grp.fillna(0, inplace=True)
    y_cols = grp.columns.values.tolist()

    source = ColumnDataSource(grp)
    all_vals = grp.index.tolist()[0:10]
    if len(all_vals) == 1:
        all_vals.append(all_vals[0]+1)

    p = figure(x_range=all_vals,  title='Results distribution by  ' + filed_name,
               tools="pan,wheel_zoom,box_zoom,reset,save",
               background_fill_color='#fafafa',
               plot_width=1000, plot_height=500)

    bars = int(len(y_cols) / 2)
    offset = (len(y_cols) % 2 - 1) /10
    width = round(1/(len(y_cols)+1),2)
    print(len(all_vals), len(y_cols), bars, offset, width)
    for g, i in zip(y_cols, range(0, len(y_cols))):
        loc = (i-bars)*width + offset
        p.vbar(x=dodge(value_field, loc, range=p.x_range), top=g, width=width, source=source,
               color=colors[i], legend=value(g))
    p.y_range.start = 0
    p.legend.orientation = "horizontal"
    p.xaxis.major_label_orientation = pi / 4
    return p


def get_quad(sr, p, all_list):
    print(sr)
    lable = sr.name
    ind = all_list.index(lable)
    sr = sr[(sr > sr.quantile(0.01)) & (sr < sr.quantile(0.99))]
    bins = sr.nunique()
    if bins <= 0:
        return
    hist, edges = np.histogram(sr, density=False, bins=bins)
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color=colors[ind], line_color='white', alpha=0.5, legend=str(lable))


def plot_compare_num(df, filed_name, value_field, sub_list=[]):
    p = figure(title='Results distribution by  ' + filed_name, tools="pan,wheel_zoom,box_zoom,reset,save",
               background_fill_color='#fafafa',
               plot_width=1000, plot_height=500, )
    all_list = df[filed_name].unique().tolist()
    #all_list.sort()
    if len(sub_list) == 0:
        sub_list = all_list
    else:
        df = df[df[filed_name].isin(sub_list)].copy()
    #sub_list.sort()
    print(df.columns)
    print(filed_name)
    print(value_field)
    #xx = df.groupby(filed_name)[value_field]
    #hist_list = xx.apply(lambda x: get_quad(x, p, all_list))
    # print(hist_list)
    # for yr in sub_list:
    #     ind = all_list.index(yr)
    #     lable = yr
    #     x = df[df[filed_name] == yr][value_field]
    #     x = x[(x > x.quantile(0.01)) & (x < x.quantile(0.99))]
    #     if x.shape[0] == 0:
    #         continue
    #     color = colors[ind]
    #     bins = len(x.unique())
    #     hist, edges = np.histogram(x, density=False, bins=bins)
    #     p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
    #            fill_color=color, line_color='white', alpha=0.5, legend=str(lable))

    p.y_range.start = 0
    p.legend.location = 'top_right'
    p.legend.background_fill_color = '#fefefe'
    p.grid.grid_line_color = 'white'
    return p


def plot_compare(df, filed_name, value_field, sub_list=[]):
    if is_categorial(df[value_field]):
        return plot_comp_cat(df, filed_name, value_field, sub_list)
    else:
        return plot_compare_num(df, filed_name, value_field, sub_list)


def plot_compare_units(df, unit_list, all_units):
    p = figure(title='Results distribution', tools="pan,wheel_zoom,box_zoom,reset,save", background_fill_color='#fafafa',
               plot_width=1000, plot_height=500, )
    for unit in unit_list:
        un_index = all_units.index(unit) + 3
        lable = unit
        x = df[df['unit'] == unit]['value']
        color = colors[un_index]
        bins = len(x.unique())
        hist, edges = np.histogram(x, density=False, bins=bins)
        p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
               fill_color=color, line_color='white', alpha=0.5, legend=str(lable))

    p.y_range.start = 0
    p.legend.location = 'top_right'
    p.legend.background_fill_color = '#fefefe'
    p.grid.grid_line_color = 'white'
    return p


def get_stats_units(df, unit_list):
    stat_list = []
    for unit, color in zip(unit_list, colors[3:]):
        x = df[df['unit'] == unit]['value']
        stat = x.describe()
        stat['Unit'] = unit
        stat_list.append(stat)

    u_stat = pd.DataFrame(stat_list)
    u_stat.sort_values(by='count', ascending=False, inplace=True)
    source = ColumnDataSource(u_stat)

    columns = [
        TableColumn(field="Unit", title="Unit"),
        TableColumn(field="count", title="Count"),
        TableColumn(field="mean", title="Mean"),
        TableColumn(field="50%", title="Median"),
        TableColumn(field="std", title="std"),
        TableColumn(field="min", title="Min"),
        TableColumn(field="max", title="Max"),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=280)

    return data_table


def get_multi_select(lab_list):
    input_labs = MultiSelect(title='Select labs:', options=lab_list, size=15)
    return input_labs


def get_sig_value_count(df):
    res_vc = {}
    vals_cols = [x for x in df.columns if 'val' in x]
    for value_filed in vals_cols:
        res_vc[value_filed] = get_value_count(df, value_filed)
    return res_vc


def get_value_count(df, count_filed):
    vc = df[count_filed].value_counts(dropna=False).reset_index()
    vc['%'] = round((vc[count_filed] / vc[count_filed].sum())*100, 2)
    vc.sort_values(by='index', inplace=True)
    data_source = ColumnDataSource(vc)

    columns = [
        TableColumn(field="index", title=count_filed, formatter=NumberFormatter(format='(0.00)')),
        TableColumn(field=count_filed, title="count"),
        TableColumn(field='%', title="%"),
    ]
    vc_table = DataTable(source=data_source, columns=columns, width=400, height=280)
    return vc_table


def make_bar_plot(title, count_ser, color):
    plot_width = 500
    if count_ser.index.shape[0] > 20:
        count_ser = count_ser[0:20]
        plot_width = 1000
    vals = list(count_ser.index.astype(str))

    plot_height = 300
    if len(max(vals, key=len)) > 20:
        plot_height = 300 + 400
    counts = count_ser.values
    p = figure(x_range=vals, title=title, tools="pan,wheel_zoom,box_zoom,reset", background_fill_color="#fafafa", plot_width=plot_width, plot_height=plot_height)
    p.vbar(x=vals, top=counts, width=0.4, color=color)
    p.xgrid.grid_line_color = None
    #p.y_range.start = 0
    #p.legend.location = "center_right"
    #p.legend.background_fill_color = "#fefefe"
    p.xaxis.major_label_orientation = pi / 4
    #p.yaxis.major_label_orientation = "vertical"
    #p.xaxis.axis_label = 'x'
    #p.yaxis.axis_label = 'Pr(x)'
    p.grid.grid_line_color = "white"
    return p


# def get_describe_df(df, value_name, value_field='value', pid_field='orig_pid'):
#     stat_list = []
#     for g, g_df in df.groupby(value_name):
#         stat = g_df[value_field].describe()
#         stat[value_name] = g
#         stat['pid_count'] = len(g_df[pid_field].unique())
#         stat_list.append(stat)
#     g_stat = pd.DataFrame(stat_list)
#
#     g_stat.set_index(value_name, inplace=True)
#     return g_stat


def get_describe_df(df, value_name, value_field='value'):
    df_out = df.groupby(value_name)[value_field].describe()
    return df_out


def get_describe_cat_table(stat_df, field_name):
    source = ColumnDataSource(stat_df)

    columns = [
        TableColumn(field=field_name, title=field_name),
        TableColumn(field="count", title="Count"),
        TableColumn(field="unique", title="Unique"),
        TableColumn(field="top", title="Top"),
        TableColumn(field="freq", title="freq"),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=280)
    return data_table


def get_describe_num_table(stat_df, field_name):
    source = ColumnDataSource(stat_df)

    columns = [
        TableColumn(field=field_name, title=field_name),
        TableColumn(field="count", title="Count"),
        TableColumn(field="mean", title="Mean", formatter=NumberFormatter(format='(0.00)')),
        TableColumn(field="50%", title="Median", formatter=NumberFormatter(format='(0.00)')),
        TableColumn(field="std", title="std", formatter=NumberFormatter(format='(0.00)')),
        TableColumn(field="min", title="Min", formatter=NumberFormatter(format='(0.00)')),
        TableColumn(field="max", title="Max", formatter=NumberFormatter(format='(0.00)')),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=280)
    return data_table


def get_describe_table(stat_df, field_name):
    if 'mean' in stat_df.columns.tolist():
        return get_describe_num_table(stat_df, field_name)
    else:
        return get_describe_cat_table(stat_df, field_name)


def get_stat_3_plots(stat_df, color):
    plotlist = []
    plotlist.append(make_bar_plot('count', stat_df['count'], color))
    if 'mean' in stat_df.columns.tolist():
        plotlist.append(make_bar_plot('mean', stat_df['mean'], color))
        plotlist.append(make_bar_plot('median', stat_df['50%'], color))
    return plotlist


def get_year_stat(df):
    print('In get_year_stat')
    stat_list = []
    plotlist = []
    for yr, yr_df in df.groupby('year'):
        stat = yr_df['value'].describe()
        stat['year'] = yr
        stat['pid_count'] = len(yr_df['orig_pid'].unique())
        stat_list.append(stat)
    yr_stat = pd.DataFrame(stat_list)
    yr_stat['year'] = yr_stat['year'].astype(int)
    yr_stat.sort_values(by='year', inplace=True)

    yr_stat.set_index('year', inplace=True)
    print(yr_stat)
    source = ColumnDataSource(yr_stat)

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

    plotlist.append(make_bar_plot('count', yr_stat['count'], 'steelblue'))
    plotlist.append(make_bar_plot('mean', yr_stat['mean'], 'steelblue'))
    plotlist.append(make_bar_plot('median', yr_stat['50%'], 'steelblue'))
    return data_table, plotlist




