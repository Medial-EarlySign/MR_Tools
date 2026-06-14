import pandas as pd
import numpy as np
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from plot_graph import plot_graph

def calc_kld(df1, df2, bin_by, p_name, eps=1e-8):
    x=df1.set_index(bin_by).join(df2.set_index(bin_by), how='outer', rsuffix='_r').reset_index()
    alt_name = '%s_r'%(p_name)
    x.loc[x[p_name].isnull() , p_name] = 0
    x.loc[x[alt_name].isnull(), alt_name] = 0

    
    selected_ind = x[p_name]>0
    entropy_p = -x.loc[selected_ind, p_name] * np.log(x.loc[selected_ind, p_name])
    entropy_p = entropy_p.sum()
    kld_res_d = x.loc[selected_ind, p_name] * (np.log(x.loc[selected_ind, p_name]))
    kld_res_d -= x.loc[selected_ind, p_name] * math.log(1.0/len(x[selected_ind]))
    kld_res_d = kld_res_d.sum()
    kld_res = x.loc[selected_ind, p_name] * ( np.log(x.loc[selected_ind, p_name]))
    x.loc[x[alt_name] < eps, alt_name] = eps
    kld_res -= x.loc[selected_ind, p_name] * np.log(x.loc[selected_ind, alt_name])
    kld_res = kld_res.sum()

    return len(x), kld_res, kld_res_d, entropy_p

def calc_distribution_distance(df1: pd.DataFrame, df2: pd.DataFrame, bin_by:str, p_name: str , eps:float =1e-8):
    x=df1.set_index(bin_by).join(df2.set_index(bin_by), how='outer', rsuffix='_r').reset_index()
    alt_name = '%s_r'%(p_name)
    combine_name = '%s_combined'%(p_name)
    x.loc[x[p_name].isnull() , p_name] = 0
    x.loc[x[alt_name].isnull(), alt_name] = 0

    x[combine_name] = (x[p_name] + x[alt_name]) / 2
    #Normalize combine_name is already normalized to 1

    #Let's measure abs distance:
    distances = np.abs(x[p_name] - x[alt_name])
    weighed_diff_in_hist = (distances).sum()
    len_bins = len(distances)

    return len_bins, weighed_diff_in_hist
    


def Test(df: pd.DataFrame, si, codedir: str, workdir: str):   
    if len(df)==0:
        return True
    
    fail=False
    sig_name=df['signal'].iloc[0]
    #Test for additional columns for signal
    skip_cols=set(['pid','signal'])
    additional_cols=list(filter(lambda x: x not in skip_cols and not(x.startswith('time_')) and not(x.startswith('value_')) ,df.columns))
    if len(additional_cols)==0:
        print(f'No additional columns for signal {sig_name} - can\'t test unit source statistics')
        return True
    
    first_tm=True
    grp_name='GROUP_COLS'
    for col in additional_cols:
        if first_tm:
            df[grp_name]=f'{col}:'+ df[col].astype(str)
        else:
            df[grp_name]=df[grp_name] + f'|{col}:'+ df[col].astype(str)
        first_tm=False
    diff_grps=sorted(list(set(df[grp_name])))
    
    if len(diff_grps)==1: #There is only 1 source,unit
        df.drop(columns=[grp_name], inplace=True)
        return True
    
    if len(diff_grps)>=100: #There are too many groups, seems like bug
        print('Error in test lab units - it seems like there are too many units/sources, please check file format additional columns')
        return False
    
    hist_all=df[['value_0', 'pid']].groupby('value_0').count().reset_index().rename(columns={'pid':'cnt'})
    hist_all['p']=hist_all['cnt']/len(df)
    
    for i,source in enumerate(diff_grps):
        tot_grp_cnt=len(df[df[grp_name]==source])
        if tot_grp_cnt > 100:
            current_hist=df[df[grp_name]==source][['value_0', 'pid']].reset_index(drop=True).groupby('value_0').count().reset_index().rename(columns={'pid':'cnt'})
            current_hist['p']=current_hist['cnt']/tot_grp_cnt
            bins_sz,kld_res,kld_uniform,entropy_p=calc_kld(hist_all,current_hist ,'value_0', 'p')
            print('%s || KLD (%d)= %f, KLD_to_Uniform=%f, entory_p=%f, grp_cnt=%d, group_counts=%d/%d'%(source, bins_sz, kld_res, kld_uniform, entropy_p, tot_grp_cnt, i,len(diff_grps)))
            if (kld_res>1):
                graphs=dict()
                graphs['All'] = hist_all[['value_0', 'p']].copy()
                graphs['Other'] = current_hist[['value_0', 'p']].copy()
                os.makedirs(os.path.join(workdir, 'outputs', sig_name), exist_ok=True)
                js_path = os.path.join('..', 'js', 'plotly.js')
                plot_graph(graphs, os.path.join(workdir, 'outputs', sig_name, 'Source_Units_%d.html'%i), \
                           f'Compared dist of {source}', javascript_path = js_path)
    df.drop(columns=[grp_name], inplace=True)
    return not(fail)


