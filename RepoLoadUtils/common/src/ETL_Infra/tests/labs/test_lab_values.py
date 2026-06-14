import pandas as pd
import numpy as np

def Test(df: pd.DataFrame, si, codedir: str, workdir: str):
    
    if len(df)==0:
        return True
    
    q_diff=0.1
    sig_name=df['signal'].iloc[0]
    cfg_file=pd.read_csv('rep_signals/signals_prctile.cfg', sep='\t')
    cfg_file=cfg_file[cfg_file['signal']==sig_name].reset_index(drop=True)[['q', 'value_0']].rename(columns={'value_0':'reference'})
    if len(cfg_file)==0: #no test for this lab
        print(f'WARN no test for signal "{sig_name}" values')
        return True
    
    # calc prctile for this lab:
    q_list = [0.001,0.01,0.1,0.5,0.9,0.99,0.999]
    res = pd.DataFrame(pd.to_numeric(df['value_0'], errors='coerce').quantile(q_list).reset_index()).rename(columns={'index':'q'})
    
    # Compare res with cfg:
    res = res.set_index('q').join(cfg_file.set_index('q')).reset_index()
    
    res['ratio1'] = res['value_0'] / res['reference']
    res['ratio2'] = res['reference'] /res['value_0']
    res['ratio'] = res[['ratio1', 'ratio2']].max(axis=1)
    
    high_ref=res[res['q']==0.999]['reference'].iloc[0]
    min_ref=res[res['q']==0.01]['reference'].iloc[0]
    
    low_range =  res[(res['q'] <  0.5) & (res['ratio'] > 3)]
    med_range =  res[(res['q'] == 0.5) & (res['ratio'] > 2)]
    high_range = res[(res['q'] >  0.5) & (res['ratio'] > 3)]
    
    fail=False
    if len(low_range) > 0:
        print(f'There are issues with low range, please have a look (more than factor 3)')
        print(low_range)
        # fail=True
        
    if len(med_range) > 0:
        print(f'There are issues with the median, please have a look (more than factor 2)')
        print(med_range)
        # fail=True
    
    if len(high_range) > 0:
        print(f'There are issues with high range, please have a look (more than factor 3)')
        print(high_range)
        # fail=True
   
    print('Done testing values of signal %s'%(sig_name))
    
    return not(fail)


