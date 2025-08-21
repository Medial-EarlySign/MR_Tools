import pandas as pd
import sys, os, io
from math import pi
MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801'))
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801', 'test_and_compare'))
from Configuration import Configuration
from const_and_utils import fixOS
from gets_and_filters import get_new_patients
import numpy as np
import scipy.special
import medpython as med

from bokeh.layouts import gridplot
from bokeh.plotting import figure, show, output_notebook
from bokeh.embed import file_html
from bokeh.resources import CDN


def get_signals_from_file(full_path):
    numeric_sigs = []
    cat_sigs = []
    with open(full_path) as f:
        lines = f.readlines()
    lines = [l for l in lines if not (l.strip().startswith('#') or len(l.strip()) == 0)]
    # print(lines)
    signals = [sig.split('\t')[1] for sig in lines]
    signals = [x for x in signals if x in thin_map.index]
    for s in signals:
        # print(thin_map.loc[s]['type'])
        if thin_map.loc[s]['type'] == 'numeric':
            numeric_sigs.append(s)
        elif thin_map.loc[s]['type'] == 'string':
            cat_sigs.append(s)

    return numeric_sigs, cat_sigs


def make_plot(title, hist, edges): # , pdf, cdf):
    p = figure(title=title, background_fill_color="#fafafa",
               tools="pan, wheel_zoom, box_zoom, reset,previewsave", plot_width=1000, plot_height=400)
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color="navy", line_color="white", alpha=0.5)
    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.grid.grid_line_color = "white"
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


def frange(start, stop, step):
    i = start
    frng = []
    while i < stop:
        frng.append(i)
        i += step
    return frng


def get_sig(rep, signal, ver, repo=True):
    if repo:
        sig = rep.get_sig(signal)
    else:
        sig = pd.read_csv(os.path.join(final_signal_folder, signal), sep='\t', names=['pid', 'eventdate', 'val'],
                          usecols=[0, 2, 3]) #, dtype={'pid': int, 'eventdate': int, 'val': np.float64})
    if 'val' not in sig.columns:
        sig.rename(columns={'val1':'val'}, inplace=True)
    sig['val'] = sig['val'].astype('float64')
    #sig remove 2% from edges
    val_d = sig['val'].quantile(0.02)
    val_u = sig['val'].quantile(0.98)
    sig = sig[(sig['val'] >= val_d) & (sig['val'] <= val_u)]
    print('values from ' + str(val_d) + ' - ' + str(val_u))
    #if np.isnan(unit_info.loc[signal]['FinalRound']):
    #    rnd = unit_info.loc[signal]['Round']
    #else:
    #    rnd = unit_info.loc[signal]['FinalRound']
    #step = float(1/pow(10, rnd))
    rng = sig['val'].max() * 1.1
    if rng > 100:
        step = 10
    if rng > 10 and rng <= 100:
        step = 1
    if rng <= 10 and rng > 1:
        step = 0.1
    if rng <= 1:
        step = 0.01
    print(rng, step)
    hist, edges = np.histogram(sig['val'], density=False, bins=frange(0, rng, step), range=(0, rng))
    #print(str(hist))
    #print(edges)
    plot = make_plot(signal + ver, hist, edges)
    return sig, plot


def print_new_signal(rep, signal, det_df, repo18=True):
    sig_18, plot_18 = get_sig(rep, signal, '_18', repo18)
    stat = [[sig_18.shape[0], sig_18['val'].mean(), sig_18['val'].std(), sig_18['val'].median(), sig_18['val'].min(),
             sig_18['val'].max()]]
    stat_df = pd.DataFrame(stat, columns=['count', 'mean', 'std', 'median', 'min', 'max'], index=[18])
    print(stat_df)

    out_file = os.path.join(out_folder, signal + '.html')
    print('to html....' + out_file)
    stat_df.to_html(out_file)
    html18 = file_html(plot_18, CDN, signal + '_18')
    htmlstr = io.StringIO()
    det_df.to_html(htmlstr)
    with open(out_file, 'a') as f:
        f.write(html18)
        f.write(htmlstr.getvalue())


def get_sig_cat(rep, signal,  repo=True):
    if repo:
        sig = rep.get_sig(signal)
    else:
        sig = pd.read_csv(os.path.join(final_signal_folder, signal), sep='\t', names=['pid', 'eventdate', 'val'],
                          usecols=[0, 2, 3])
    if 'val' not in sig.columns:
        return pd.DataFrame(), None
    #sig.drop_duplicates(subset=['pid', 'date','val'], inplace=True)
    if 'val' not in sig.columns:
        return sig, pd.Series()
    vc = sig['val'].value_counts()
    return sig, vc


def print_new_signal_cat(rep_18, signal, repo18=True):
    sig_18, vc_18 = get_sig_cat(rep_18, signal, repo18)
    stat = [[sig_18.shape[0], len(vc_18.index), sig_18[sig_18['val'] == 'EMPTY_THIN_FIELD'].shape[0]]]
    stat_df = pd.DataFrame(stat, columns=['count', 'categories', 'empty count'], index=[18])
    out_file = os.path.join(out_folder, signal + '.html')
    print('to html....' + out_file)
    stat_df.to_html(out_file)
    print(' 18 count: ' + str(sig_18.shape[0]) + ' in ' + str(len(sig_18['pid'].unique())) + ' pids')
    plot_18 = make_bar_plot(signal + '_18', vc_18)
    vc_18_df = pd.DataFrame(vc_18)
    vc_18_df['%'] = round((vc_18_df['val'] / sig_18.shape[0]) * 100, 2)
    html18 = file_html(plot_18, CDN, signal + '_18')
    htmlstr2 = io.StringIO()
    vc_18_df.to_html(htmlstr2)
    with open(out_file, 'a') as f:
        f.write(html18)
        f.write(htmlstr2.getvalue())


def comp_signal_cat(signal, rep_17, rep_18, signals_old, repo17=True, repo18=True):
    if signal == 'PRAC':
        return
    if signal not in signals_old:
        print(' Signal "' + signal + '" is new ')
        print_new_signal_cat(rep_18, signal, repo18=True)
        return

    sig_17, vc_17 = get_sig_cat(rep_17, signal, repo17)
    sig_18, vc_18 = get_sig_cat(rep_18, signal, repo18)
    stat = [[sig_17.shape[0], len(vc_17.index), sig_17[sig_17['val'] == 'EMPTY_THIN_FIELD'].shape[0]],
            [sig_18.shape[0], len(vc_18.index), sig_18[sig_18['val'] == 'EMPTY_THIN_FIELD'].shape[0]]]
    stat_df = pd.DataFrame(stat, columns=['count', 'categories', 'empty count'], index=[17, 18])

    out_file = os.path.join(out_folder, signal + '.html')
    print('to html....' + out_file)
    stat_df.to_html(out_file)

    print(' 17 count: ' + str(sig_17.shape[0]) + ' in '+str(len(sig_17['pid'].unique())) +' pids')
    print(' 18 count: ' + str(sig_18.shape[0]) + ' in '+str(len(sig_18['pid'].unique())) +' pids')
    plot_17 = make_bar_plot(signal +'_17', vc_17)
    plot_18 = make_bar_plot(signal +'_18', vc_18)
    #hist_list = [hist_dict[x] for x in hist_dict.keys()]
    vc_17_df = pd.DataFrame(vc_17)
    vc_17_df['%'] = round((vc_17_df['val'] / sig_17.shape[0])*100, 2)
    vc_18_df = pd.DataFrame(vc_18)
    vc_18_df['%'] = round((vc_18_df['val'] / sig_18.shape[0])*100, 2)
    html17 = file_html(plot_17, CDN, signal + '_17')
    html18 = file_html(plot_18, CDN, signal + '_18')
    htmlstr1 = io.StringIO()
    vc_17_df.to_html(htmlstr1)
    htmlstr2 = io.StringIO()
    vc_18_df.to_html(htmlstr2)
    with open(out_file, 'a') as f:
        f.write(html17)
        f.write(html18)
        f.write(htmlstr1.getvalue())
        f.write(htmlstr2.getvalue())


def comp_signal(signal, rep_17, rep_18, det_df, signals_old, repo17=True, repo18=True):
    if signal not in signals_old and signal != 'Temperature':
        print_new_signal(rep_18, signal, det_df, repo18=True)
        return
    if signal == 'Temperature':
        sig_17, plot_17 = get_sig(rep_17, 'TEMP', '_17', repo17)
    else:
        sig_17, plot_17 = get_sig(rep_17, signal, '_17', repo17)
    sig_18, plot_18 = get_sig(rep_18, signal, '_18', repo18)
    stat = [[sig_17.shape[0], sig_17['val'].mean(), sig_17['val'].std(), sig_17['val'].median(), sig_17['val'].min(), sig_17['val'].max()],
            [sig_18.shape[0], sig_18['val'].mean(), sig_18['val'].std(), sig_18['val'].median(), sig_18['val'].min(), sig_18['val'].max()]]
    stat_df = pd.DataFrame(stat, columns=['count', 'mean', 'std', 'median', 'min', 'max'], index=[17,18])
    print(stat_df)

    #hist_list = [hist_dict[x] for x in hist_dict.keys()]
    #show(gridplot([plot_17, plot_18], ncols=3, plot_width=480, plot_height=200, toolbar_location=None))
    out_file = os.path.join(out_folder, signal+'.html')
    print('to html....' + out_file)
    stat_df.to_html(out_file)
    html17 = file_html(plot_17, CDN, signal+'_17')
    html18 = file_html(plot_18, CDN, signal + '_18')
    htmlstr = io.StringIO()
    det_df.to_html(htmlstr)
    with open(out_file, 'a') as f:
        f.write(html17)
        f.write(html18)
        f.write(htmlstr.getvalue())


def plot_category(old_rep_path, new_rep_path):
    numeric_signals_17, cat_signals_17 = get_signals_from_file(os.path.join(old_rep_path, 'thin.signals'))
    print(len(numeric_signals_17), len(cat_signals_17))

    numeric_signals_18, cat_signals_18 = get_signals_from_file(os.path.join(new_rep_path, 'thin.signals'))
    print(len(numeric_signals_18), len(cat_signals_18))
    cat_signals_17.remove('Drug')
    cat_signals_18.remove('Drug')
    # new_pids = get_new_patients()
    cat_signals_17 = ['Cancer_Location']
    cat_signals_18 = ['Cancer_Location']
    rep_17 = med.PidRepository()
    rep_17.read_all(os.path.join(rep_17_path, 'thin.repository'), [], cat_signals_17)
    print(med.cerr())

    rep_18 = med.PidRepository()
    rep_18.read_all(os.path.join(rep_18_path, 'thin.repository'), [], cat_signals_18)
    print(med.cerr())

    for signal in cat_signals_18:
        print('===== ' + signal + ' =======')
        comp_signal_cat(signal, rep_17, rep_18, cat_signals_17, repo17=True, repo18=True)


def plot_numeric(old_rep_path, new_rep_path):
    numeric_signals_17, cat_signals_17 = get_signals_from_file(os.path.join(old_rep_path, 'thin.signals'))
    print(len(numeric_signals_17), len(cat_signals_17))

    numeric_signals_18, cat_signals_18 = get_signals_from_file(os.path.join(new_rep_path, 'thin.signals'))
    print(len(numeric_signals_18), len(cat_signals_18))

    # new_pids = get_new_patients()
    #numeric_signals_17 = ['PFR']
    #numeric_signals_18 = ['PFR']
    rep_17 = med.PidRepository()
    rep_17.read_all(os.path.join(rep_17_path, 'thin.repository'), [], numeric_signals_17)

    print(med.cerr())

    rep_18 = med.PidRepository()
    print(os.path.join(rep_18_path, 'thin.repository'))
    rep_18.read_all(os.path.join(rep_18_path, 'thin.repository'), [], numeric_signals_18)

    print(med.cerr())
    for signal in numeric_signals_18:
        print('===== ' + signal + ' =======')
        if signal in unit_info.index:
            details_dict = {'Unit': [unit_info.loc[signal]['FinalUnit']],
                            'Round': [unit_info.loc[signal]['Round']],
                            'FinalRound': [unit_info.loc[signal]['FinalRound']]}
            if signal in unitTran['signal'].values:
                details_dict['Factor'] = [unitTran[unitTran['signal'] == signal].iloc[0]['muliplier']]
        else:
            details_dict = {}
        print(details_dict)
        det_df = pd.DataFrame.from_dict(details_dict)
        comp_signal(signal,rep_17, rep_18, det_df, numeric_signals_17, repo17=True, repo18=True)


cfg = Configuration()
code_folder = fixOS(cfg.code_folder)
out_folder = os.path.join(fixOS(cfg.work_path), 'compare')
final_signal_folder = os.path.join(fixOS(cfg.work_path), 'FinalSignals')
full_file = os.path.join(code_folder, 'thin_signal_mapping.csv')
thin_map = pd.read_csv(full_file, sep='\t')
thin_map.drop_duplicates(subset='signal', inplace=True)
thin_map.set_index('signal', inplace=True)

unit_info = pd.read_csv(os.path.join(code_folder, '../common_knowledge/signal_units.txt'), sep='\t')
unit_info.set_index('Name', inplace=True)

unitTran = pd.read_csv(os.path.join(code_folder, 'unitTranslator.txt'), sep='\t', usecols=[0, 2])
unitTran = unitTran[unitTran['muliplier'] != 1]
unitTran.drop_duplicates(inplace=True)

rep_17_path = '/server/Work/CancerData/Repositories/THIN/thin_jun2017/'
rep_18_path = '/server/Work/CancerData/Repositories/THIN/thin_2018/'
#plot_numeric(rep_17_path, rep_18_path)
plot_category(rep_17_path, rep_18_path)
