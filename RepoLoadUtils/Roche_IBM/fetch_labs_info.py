#!/usr/bin/python
from basic_loader import read_table_united, read_column_united
from Configuration import Configuration
import os, sys
from datetime import datetime
import pandas as pd
import plotly.graph_objs as go
from load_data import *

def proceed():
    ans=input('Approved (Y/N)? ').upper()
    while ans!='Y' and ans != 'N':
        ans=input('Approved (Y/N)? ').upper()
    return ans=='Y'

def get_histogram(unit_df, prctiles=[0,5,10,20,25,35,50,65,75,80,90,95,100]):
    #has 'val', 'cnt'
    prc=pd.DataFrame({'p': prctiles})
    c=unit_df.copy()
    c['cumsum']= c.cnt.cumsum()
    tot=c.cnt.sum()
    c=c.merge(prc, how='cross')
    prc_cnts=c[c['cumsum']>=c.p*tot/100].groupby('p').first().reset_index()
    return prc_cnts[['p','val']]

def fetch_sig_stats(cfg, all_df, sig, min_th):
    os.makedirs(os.path.join(cfg.work_dir, 'outputs'), exist_ok=True)
    os.makedirs(os.path.join(cfg.work_dir, 'outputs', sig), exist_ok=True)
    
    all_df=process_sig(all_df)
    
    #Unconverted values:
    val_txt_dist=all_df[(all_df['val']!=all_df['val_conv'])][['pid', 'val_txt']].groupby('val_txt').count().reset_index().sort_values('pid', ascending=False)
    val_txt_dist.rename(columns={'pid': 'cnt'}, inplace=True)
    val_txt_dist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'val_conversion.dist'), sep='\t', index=False)
    plot_graph(val_txt_dist.val_txt, val_txt_dist.cnt, 'bar', os.path.join(cfg.work_dir, 'outputs', sig, 'val_conversion.dist.html'))
    val_txt_dist=all_df[(all_df['val']!=all_df['val_conv'])][['pid', 'val_txt', 'val']].groupby(['val_txt', 'val'], dropna=False).count().reset_index().sort_values('pid', ascending=False).rename(columns={'pid': 'cnt'})
    val_txt_dist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'val_val_txt_conversion.dist'), sep='\t', index=False)
    #val_txt_dist=all_df[(all_df['val']!=all_df['val_conv'])][['pid', 'val']].groupby('val').count().reset_index().sort_values('pid', ascending=False)
    #val_txt_dist.rename(columns={'pid': 'cnt'}, inplace=True)
    #val_txt_dist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'val_conversion.val.dist'), sep='\t', index=False)
    #If approved - move to next step:
    print('Reffer to file %s'%(os.path.join(cfg.work_dir, 'outputs', sig, 'val_conversion.dist')), flush=True)
    #if not(proceed()):
    #    sys.exit(0)
    all_df=all_df[all_df['val']==all_df['val_conv']][['pid', 'signal', 'date', 'val', 'unit', 'source']].reset_index(drop=True)
    out_range=len(all_df[all_df['val']<min_th])
    if (len(all_df)==0):
        print('Got Empty Signal %s'%(sig))
        return
    print('has %d(%2.4f%%) records below %f - removing for %s'%(out_range, out_range/(len(all_df)*100.0), min_th, sig), flush=True)
    all_df=all_df[all_df['val']>=min_th].reset_index(drop=True)

    tmp=all_df[['pid', 'source']].groupby('source').count().reset_index().rename(columns={'pid':'cnt'}).sort_values('cnt', ascending=False)
    tmp.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'source.dist'), sep='\t', index=False)
    plot_graph(tmp.source, tmp.cnt, 'bar', os.path.join(cfg.work_dir, 'outputs', sig, 'source.dist.html'))
    unit_dist=all_df[['pid', 'unit']].groupby('unit', dropna=False).count().reset_index().rename(columns={'pid':'cnt'}).sort_values('cnt', ascending=False)
    unit_dist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'units.dist'), sep='\t', index=False)
    plot_graph(unit_dist.unit, unit_dist.cnt, 'bar', os.path.join(cfg.work_dir, 'outputs', sig, 'unit.dist.html'))

    units_hist=all_df[['unit', 'val', 'pid']].groupby(['unit', 'val'], dropna=False).count().reset_index().rename(columns={'pid':'cnt'}).sort_values(['unit', 'val'], ascending=[True,True])
    units_hist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'units_vals.dist'), sep='\t', index=False)
    summary_hist=None
    for unit in units_hist['unit'].drop_duplicates():
        unit_df=units_hist[units_hist['unit']==unit][['val', 'cnt']]
        u_hist=get_histogram(unit_df)
        u_hist['unit']=unit
        if summary_hist is None:
            summary_hist=u_hist
        else:
            summary_hist=summary_hist.append(u_hist, ignore_index=True)
    summary_hist.to_csv(os.path.join(cfg.work_dir, 'outputs', sig, 'units_vals_sum.dist'), sep='\t', index=False)
    x_dict=dict()
    y_dict=dict()
    all_units=summary_hist.unit.copy().drop_duplicates()
    all_vals=len(all_df)
    to_sort_u=[]
    for u in all_units:
        u_cnt=unit_dist[unit_dist['unit']==u].cnt.iloc[0]
        perc_cnt=u_cnt*100.0/all_vals
        gname='%s(%d - %2.2f%%)'%(u, u_cnt, perc_cnt)
        to_sort_u.append([gname, u_cnt])
        x_dict[gname]=summary_hist[summary_hist['unit']==u].p
        y_dict[gname]=summary_hist[summary_hist['unit']==u].val
    to_sort_u=list(map(lambda x: x[0], sorted(to_sort_u, key=lambda x: x[1], reverse=True)))
    plot_graph(x_dict, y_dict, 'markers+lines', os.path.join(cfg.work_dir, 'outputs', sig, 'units_vals_sum.dist.html'), to_sort_u)
    for u in all_units:
        u_cnt=unit_dist[unit_dist['unit']==u].cnt.iloc[0]
        perc_cnt=u_cnt*100.0/all_vals
        gname='%s(%d - %2.2f%%)'%(u, u_cnt, perc_cnt)
        x_dict[gname]=summary_hist[(summary_hist['unit']==u) & (summary_hist['p']>0) & (summary_hist['p']<100)].p
        y_dict[gname]=summary_hist[(summary_hist['unit']==u) & (summary_hist['p']>0) & (summary_hist['p']<100)].val
    plot_graph(x_dict, y_dict, 'markers+lines', os.path.join(cfg.work_dir, 'outputs', sig, 'units_vals_sum.dist.clean.html'), to_sort_u)

def fetch_signals(cfg):
    sig_map=pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'map.tsv'), sep='\t')
    sigs=list(sig_map['Map_to'].copy().drop_duplicates())
    return sigs

def plot_graph(x_data, y_data, mode='markers+lines', save_path='/tmp/1.html', order_names=None):
    fig=go.Figure()
    amode=mode
    if type(x_data) == dict:
        if order_names is None:
            for g_name, x_d in x_data.items():
                if mode=='bar':
                    fig.add_trace(go.Bar(x=x_d, y=y_data[g_name], name=g_name))
                else:
                    fig.add_trace(go.Scatter(x=x_d, y=y_data[g_name], mode=amode, name=g_name))
        else:
            for g_name in order_names:
                if mode=='bar':
                    fig.add_trace(go.Bar(x=x_data[g_name], y=y_data[g_name], name=g_name))
                else:
                    fig.add_trace(go.Scatter(x=x_data[g_name], y=y_data[g_name], mode=amode, name=g_name))
    else:
        if mode=='bar':
            fig.add_trace(go.Bar(x=x_data, y=y_data, name='trace_1'))
        else:
            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode=amode, name='trace_1'))
    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title='X')
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title='Y')
    fig.layout.plot_bgcolor='white'
    fig.layout.title='Plot'
    fig.write_html(save_path, include_plotlyjs='https://cdn.plot.ly/plotly-2.4.2.min.js')

cfg=Configuration()

all_sigs=fetch_signals(cfg)
batch_size=10
#start_pos=0
start_pos=40
sample_random=5
min_th=0
all_sigs=all_sigs[start_pos:]
if batch_size <=0:
    batch_size=len(all_sigs)
for batch_idx in range(0,len(all_sigs), batch_size):
    fetch_sigs=all_sigs[batch_idx:batch_idx+batch_size]
    print('%s :: Processing new batch, starts from %d, has %d signals in batch. total %d'%(datetime.now(), batch_idx, len(fetch_sigs), len(all_sigs)))
    sig=fetch_sigs[0]
    all_df = read_sig_from_pre(cfg, sig, fetch_sigs, sample_random)
    all_df.loc[all_df['unit'].isnull(), 'unit']='<NULL>'
    for s in fetch_sigs:
        print('%s :: Processing %s'%(datetime.now(), s), flush=True)
        fetch_sig_stats(cfg, all_df[all_df['signal']==s].reset_index(drop=True), s,min_th)


