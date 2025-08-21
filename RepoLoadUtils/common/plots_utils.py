import pandas as pd
import numpy as np
import os
import io
from math import pi

from bokeh.layouts import gridplot, row
from bokeh.plotting import figure, show, output_notebook
from bokeh.embed import file_html
from bokeh.resources import CDN


def make_plot(title, hist, edges):
    p = figure(title=title, tools="pan,wheel_zoom,box_zoom,reset", background_fill_color='#fafafa')
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
          fill_color='navy', line_color='white', alpha=0.5)
    p.y_range.start = 0
    if p.legend:
        p.legend.location = 'center_right'
        p.legend.background_fill_color = '#fefefe'
    p.grid.grid_line_color = 'white'
    return p


def make_bar_plot(title, count_ser, color='Blue'): # , pdf, cdf):
    vals = list(count_ser.index.astype(str))
    counts = count_ser.values
    p = figure(x_range=vals, title=title, tools="pan,wheel_zoom,box_zoom,reset", background_fill_color="#fafafa", plot_width=1000, plot_height=600)
    p.vbar(x=vals, top=counts, width=0.4, color=color)
    #p = figure(x_range=fruits, plot_height=250, title="Fruit Counts",
    #       toolbar_location=None, tools="")

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


def get_histogram(sig, sig_df, val_field):
    val_d = sig_df[val_field].quantile(0.02)
    val_u = sig_df[val_field].quantile(0.98)
    sig_df_cut = sig_df[(sig_df[val_field] >= val_d) & (sig_df[val_field] <= val_u)]
    bins = len(sig_df_cut[val_field].unique())
    hist, edges = np.histogram(sig_df_cut[val_field], density=True, bins=bins)
    plot = make_plot(sig, hist, edges)
    stat = sig_df[val_field].describe()
    stat['pid_count'] = len(sig_df_cut['pid'].unique())
    stat_df = pd.DataFrame([stat])
    return stat_df, plot


def get_year_stat(sig, sig_df, val_field, date_field):
    stat_list = []
    plotlist = []
    #sig_df['year'] = sig_df[date_field].astype(str).str[0:4]
    sig_df['year'] = (sig_df[date_field] / 10000).astype('int').astype('category')

    #for yr, yr_df in sig_df.groupby('year'):
    for yr in sig_df['year'].unique():
        yr_df = sig_df[sig_df['year'] == yr]
        stat = {'year': yr, 'count': yr_df.shape[0], 'pid_count': yr_df['pid'].nunique(),
                'mean': yr_df[val_field].mean(), 'median': yr_df[val_field].median(), 'std': yr_df[val_field].std(),
                'min': yr_df[val_field].min(), 'max': yr_df[val_field].max()}
        stat_list.append(stat)
    yr_stat = pd.DataFrame(stat_list)
    yr_stat.set_index('year', inplace=True)

    plotlist.append(make_bar_plot(sig +' ' + ' count', yr_stat['count']))
    plotlist.append(make_bar_plot(sig + ' ' + ' count per pid', yr_stat['count']/yr_stat['pid_count']))
    plotlist.append(make_bar_plot(sig +' ' + ' mean', yr_stat['mean']))
    plotlist.append(make_bar_plot(sig +' ' + ' median', yr_stat['median']))
    return yr_stat, gridplot(plotlist, ncols=4, plot_width=300, plot_height=300)
    #return yr_stat, row(plotlist[0], plotlist[1], plotlist[2])


def get_year_count(sig, sig_df, val_field, date_field):
    print('In get_year_count')
    stat_list = []
    plotlist = []
    #sig_df['year'] = sig_df[date_field].astype(str).str[0:4]
    sig_df['year'] = (sig_df[date_field] / 10000).astype('int').astype('category')
    #for yr, yr_df in sig_df.groupby('year'):
    for yr in sig_df['year'].unique():
        yr_df = sig_df[sig_df['year'] == yr]
        stat = {'year': yr, 'count': yr_df.shape[0], 'pid_count': yr_df['pid'].nunique()}
        if yr_df[val_field].nunique() == 2:
            for vl in yr_df[val_field].unique():
                stat['value ' + str(vl)] = round((yr_df[yr_df[val_field] == vl].shape[0] / yr_df.shape[0])*100, 2)
        stat_list.append(stat)
    yr_stat = pd.DataFrame(stat_list)
    yr_stat.set_index('year', inplace=True)
    plotlist.append(make_bar_plot(sig + ' ' + ' count', yr_stat['count']))
    plotlist.append(make_bar_plot(sig + ' ' + ' count per pid', yr_stat['count']/yr_stat['pid_count']))
    #plotlist.append(make_bar_plot(sig +' ' + ' pid_count', yr_stat['pid_count']))
    return yr_stat, gridplot(plotlist, ncols=2, plot_width=300, plot_height=300)


def get_signal_units(sig, unit_info, unitTran):
    if sig in unit_info.index:
        round = unit_info.loc[sig]['Round']
        details_dict = {'Unit': unit_info.loc[sig]['FinalUnit'],
                         'Round': round}
        if sig in unitTran['signal'].values:
            details_dict['Factor'] = unitTran[unitTran['signal'] == sig].iloc[0]['muliplier']
    else:
        details_dict = {}
    det_df = pd.DataFrame([details_dict])
    return det_df

