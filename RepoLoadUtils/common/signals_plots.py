import pandas as pd
import numpy as np
import os
import io
import sys
from math import pi
sys.path.insert(0,'/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/Release/medial-python36')
#import med

from  plots_utils import get_histogram, get_year_stat, get_year_count, make_bar_plot, get_signal_units
from bokeh.embed import file_html
from bokeh.resources import CDN


def signal_to_file(sig, rep, sig_unit, out_folder):
    print('signal....' + sig)
    out_file = os.path.join(out_folder, sig+'.html')
    if os.path.exists(out_file):
        print('Plot file for signal '+ sig + ' already exists')
        return
    sig_df = rep.get_sig(sig)
    val_field = 'val'
    date_field = 'date'
    if sig == 'Smoking_quantity':
        val_field = 'val2'
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


def numeric_plots(rep, numeric_signals, code_folder, out_folder):
    unit_info = pd.read_csv(os.path.join(code_folder, '../common_knowledge/signal_units.txt'), sep='\t')
    unit_info.set_index('Name', inplace=True)
    #print(unit_info)
    unitTran = pd.read_csv(os.path.join(code_folder, 'unitTranslator.txt'), sep='\t', usecols=[0, 2])
    unitTran = unitTran[unitTran['muliplier'] != 1]
    unitTran.drop_duplicates(inplace=True)

    for sig in numeric_signals:
        sig_det = get_signal_units(sig, unit_info, unitTran)
        signal_to_file(sig, rep, sig_det, out_folder)
    

def category_plots(rep, cat_signals, out_folder):
    for sig in cat_signals:
        print('to html....' + sig)
        sig_df = rep.get_sig(sig,translate=True)               
        vc = sig_df['val'].value_counts()
        stat = [[sig_df.shape[0], len(vc.index)]]
        stat_df = pd.DataFrame(stat, columns=['count', 'categories'], index=[sig])
        out_file = os.path.join(out_folder, sig + '.html')
        #if os.path.exists(out_file):
        #    print('Plot file for signal '+ sig + ' already exists')
        #    continue
        val_field = 'val'
        date_field = 'date'
        if sig == 'ADMISSION':
            date_field = 'date_start'
        yaer_stat, year_plot = get_year_count(sig, sig_df, val_field, date_field)


        stat_df.to_html(out_file)
    
        plot = make_bar_plot(sig, vc[0:10])
        vc_df = pd.DataFrame(vc)
        vc_df['%'] = round((vc_df['val'] / sig_df.shape[0]) * 100, 2)
        html1 = file_html(plot, CDN, sig)
        htmlstr2 = io.StringIO()
        vc_df.to_html(htmlstr2)
        with open(out_file, 'a', encoding='utf-8') as f:
            html_plot2 = file_html(year_plot, CDN, sig)
            htmlstr = io.StringIO()
            yaer_stat.to_html(htmlstr)
            f.write(html1)
            f.write(html_plot2)
            f.write(htmlstr.getvalue())
            f.write(htmlstr2.getvalue())


