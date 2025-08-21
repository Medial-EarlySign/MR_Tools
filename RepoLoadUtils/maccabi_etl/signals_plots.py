import pandas as pd
import numpy as np
import os
import sys
import io
import time
from math import pi
sys.path.append(os.path.join('/opt/medial/tools/bin', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, read_tsv
import med

from bokeh.layouts import gridplot, row
from bokeh.plotting import figure, show, output_notebook
from bokeh.embed import file_html
from bokeh.resources import CDN

def make_plot(title, hist, edges):
    p = figure(title=title, tools='', background_fill_color='#fafafa')
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
          fill_color='navy', line_color='white', alpha=0.5)
    p.y_range.start = 0
    p.legend.location = 'center_right'
    p.legend.background_fill_color = '#fefefe'
    p.grid.grid_line_color = 'white'
    return p

def make_bar_plot(title, count_ser): # , pdf, cdf):
    vals = list(count_ser.index)
    counts = count_ser.values
    p = figure(x_range=vals, title=title, tools='', background_fill_color="#fafafa", plot_width=1000, plot_height=600)
    p.vbar(x=vals, top=counts, width=0.4)
    #p = figure(x_range=fruits, plot_height=250, title="Fruit Counts",
    #       toolbar_location=None, tools="")

    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    #p.xaxis.axis_label = 'x'
    #p.yaxis.axis_label = 'Pr(x)'
    p.grid.grid_line_color="white"
    p.xaxis.major_label_orientation = pi/4
    return p

def get_histogram(sig, sig_df, val_field):
    print('In  get_histogram')
    val_d = sig_df[val_field].quantile(0.02)
    val_u = sig_df[val_field].quantile(0.98)
    sig_df_cut = sig_df[(sig_df[val_field] >= val_d) & (sig_df[val_field] <= val_u)]
    seg_med = sig_df_cut[val_field].median() 
    range0 = min(0, seg_med - seg_med*2)
    range1 = seg_med*3
    hist, edges = np.histogram(sig_df_cut[val_field], density=True, bins=600, range = (range0,range1))
    plot = make_plot(sig, hist, edges)
    stat = [{'count': sig_df.shape[0], 'mean': sig_df[val_field].mean(), 
         'median': sig_df[val_field].median(), 'std': sig_df[val_field].std(),
         'min': sig_df[val_field].min(), 'max': sig_df[val_field].max()}]
    stat_df = pd.DataFrame(stat)
    return stat_df, plot


def get_year_stat(sig, sig_df, val_field, date_field):
    print('In get_year_stat')
    stat_list = []
    plotlist = []
    sig_df['year'] = sig_df[date_field].astype(str).str[0:4]   
    for yr, yr_df in sig_df.groupby('year'):
        stat = {'year': yr,'count': yr_df.shape[0], 'mean': yr_df[val_field].mean(), 
                 'median': yr_df[val_field].median(), 'std': yr_df[val_field].std(),
                 'min': yr_df[val_field].min(), 'max': yr_df[val_field].max()}
        stat_list.append(stat)
    yr_stat = pd.DataFrame(stat_list)
    yr_stat.set_index('year', inplace=True)

    plotlist.append(make_bar_plot(sig +' ' + ' count', yr_stat['count']))
    plotlist.append(make_bar_plot(sig +' ' + ' mean', yr_stat['mean']))
    plotlist.append(make_bar_plot(sig +' ' + ' median', yr_stat['median']))
    return yr_stat, gridplot(plotlist, ncols=3, plot_width=300, plot_height=300)
    #return yr_stat, row(plotlist[0], plotlist[1], plotlist[2])


def signal_to_file(sig, rep, sig_unit, out_folder):
    print('signal....' + sig)
    out_file = os.path.join(out_folder, sig+'.html')
    if os.path.exists(out_file):
        print('Plot file for signal '+ sig + ' already exists')
        return
    sig_df = rep.get_sig(sig)
    val_field = 'val'
    date_field = 'date'
    if sig == 'Smoking_Status':
        return
    if sig =='BP':
        val_field = 'val1'
    if sig == 'BDATE' or sig == 'DEATH':
        val_field = 'time'
        date_field = 'time'
    sig_stat, sig_hist_plot = get_histogram(sig, sig_df,val_field)
    if date_field in sig_df.columns:
        yaer_stat, year_plot = get_year_stat(sig, sig_df, val_field, date_field)
    else:
        yaer_stat=None
        year_plot=None
    sig_stat.to_html(out_file)
    html_plot1 = file_html(sig_hist_plot, CDN, sig)
    htmlstr_unit = io.StringIO()
    sig_unit.to_html(htmlstr_unit)
    with open(out_file, 'a', encoding='utf-8') as f:
        f.write(htmlstr_unit.getvalue())
        f.write(html_plot1)
        if year_plot:
            html_plot2 = file_html(year_plot, CDN, sig)
            htmlstr = io.StringIO()
            yaer_stat.to_html(htmlstr)
            f.write(html_plot2)
            f.write(htmlstr.getvalue())
        f.close()


def get_signal_units(sig, unit_info, unitTran):
    if sig in unit_info.index:
        if unit_info.loc[sig]['Round'] == '0.5':
            round = 'even'
        elif unit_info.loc[sig]['Round'] == '0.05':
            round = 'even in resultion 1' 
        elif unit_info.loc[sig]['Round'] == '0.2':
            round = 'Duplicates of five'
        else:
            round = unit_info.loc[sig]['Round']
        details_dict = {'Unit': unit_info.loc[sig]['FinalUnit'],
                         'Round': round}
        if sig in unitTran['signal'].values:
            details_dict['Factor'] = unitTran[unitTran['signal'] == sig].iloc[0]['muliplier']
    else:
        details_dict = {}
    det_df = pd.DataFrame([details_dict])
    return det_df

def numeric_plots(map_df, out_folder):
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    macabbi_map_numeric = map_df[(map_df['type'] == 'numeric')]
    numeric_signals = macabbi_map_numeric['signal'].unique().tolist()
    #print(len(numeric_signals))
    maccabi_rep = '/data/Repositories/aug20/maccabi.repository'
    rep = med.PidRepository()
    rep.read_all(maccabi_rep, [], numeric_signals)
    print(med.cerr())
    
    unit_info = pd.read_csv(os.path.join(code_folder, '../common_knowledge/signal_units.txt'), sep='\t')
    unit_info.set_index('Name', inplace=True)
    #print(unit_info)
    unitTran = pd.read_csv(os.path.join(code_folder, 'unitTranslator.txt'), sep='\t', usecols=[0, 2])
    unitTran = unitTran[unitTran['muliplier'] != 1]
    unitTran.drop_duplicates(inplace=True)


    for sig in numeric_signals:
        sig_det = get_signal_units(sig, unit_info, unitTran)
        signal_to_file(sig, rep, sig_det, out_folder)
    

def category_plots(sig_list, out_folder):
    #print(len(numeric_signals))
    maccabi_rep = '/data/Repositories/aug20/maccabi.repository'
    rep = med.PidRepository()
    rep.read_all(maccabi_rep, [], sig_list)
    print(med.cerr())
    
    for sig in sig_list:
        print('to html....' + sig)
        sig_df = rep.get_sig(sig,translate=True)               
        vc = sig_df['val'].value_counts()
        stat = [[sig_df.shape[0], len(vc.index)]]
        stat_df = pd.DataFrame(stat, columns=['count', 'categories'], index=[sig])
        out_file = os.path.join(out_folder, sig + '.html')
        #if os.path.exists(out_file):
        #    print('Plot file for signal '+ sig + ' already exists')
        #    continue
        
        stat_df.to_html(out_file)
    
        plot = make_bar_plot(sig, vc[0:10])
        vc_df = pd.DataFrame(vc)
        vc_df['%'] = round((vc_df['val'] / sig_df.shape[0]) * 100, 2)
        html1 = file_html(plot, CDN, sig)
        htmlstr2 = io.StringIO()
        vc_df.to_html(htmlstr2)
        with open(out_file, 'a', encoding='utf-8') as f:
            f.write(html1)
            f.write(htmlstr2.getvalue())

if __name__ == '__main__':
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    full_map_file = os.path.join(code_folder, 'maccabi_signal_map.csv')
    macabi_map = pd.read_csv(full_map_file, sep='\t')
    
    numeric_plots(macabi_map, out_folder)
    macabbi_map_cat = macabi_map[(macabi_map['type'] == 'category')]
    cat_signals = macabbi_map_cat['signal'].unique().tolist()
    category_plots(cat_signals, out_folder)
    cat_sigs = ['Diabetic_registry', 'Cancer_registry', 'ADMISSION', 'STAY', 'DIAGNOSIS', 'Vaccination', 'Drug', 'Drug_purchase', 'Hospital_diagnosis', 'Smoking_Status']
    category_plots(cat_sigs, out_folder)
 