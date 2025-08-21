import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from plot_graph import plot_graph

def Test(df: pd.DataFrame, si, codedir: str, workdir: str):
    cols=['pid', 'value_0']
    sig_name=df['signal'].iloc[0]
    before_size=len(df)
    #only test BDATE - can fail BDATE signal:
    CURRENT_YEAR=datetime.now().year
    MAX_DATE=(CURRENT_YEAR+1)*10000+101
    df['value_0']=pd.to_numeric(df['value_0']).astype(int)
    ilegal_dates_cnt=len(df[ (df['value_0']<19000101) | (df['value_0']>=MAX_DATE)])
    
    if ilegal_dates_cnt/len(df)>0.002:
        print('Failed! There are %d(%2.3f%%) ilegal dates for signal %s'%(ilegal_dates_cnt, 100*ilegal_dates_cnt/len(df), sig_name))
        return False
    if ilegal_dates_cnt > 0:
        print('There are %d(%2.3f%%) ilegal dates for signal %s'%(ilegal_dates_cnt, 100*ilegal_dates_cnt/len(df), sig_name))
        #clean ilegal
        df.drop(df.loc[(df['value_0']<19000101) | (df['value_0']>=MAX_DATE)].index, inplace=True)
        df.reset_index(drop=True, inplace=True)
    if before_size!=len(df):
        print(f'Done testing {sig_name} dates. start with {before_size} patients and left with {len(df)}')
    #Test for "month" "days"
    month_vals=(df['value_0']//100)%100
    days_vals=(df['value_0']%100)
    ilegal_month=len(month_vals[(month_vals<1) | (month_vals>12)])
    ilegal_days=len(days_vals[(days_vals<1) | (days_vals>31)])
    js_path = os.path.join('..', 'js', 'plotly.js')
    if ilegal_month> 0:
        print(f'There are ilegal month values. month distribution values for signal {sig_name}')
        res=month_vals.value_counts().reset_index()
        print(res)
        os.makedirs(os.path.join(workdir, 'outputs', sig_name), exist_ok=True)
        plot_graph(res,os.path.join(workdir, 'outputs', sig_name, 'test_date_month.html'), javascript_path = js_path)
    if ilegal_days > 0:
        print(f'There are ilegal days values. month distribution values for signal {sig_name}')
        res=days_vals.value_counts().reset_index()
        print(res)
        os.makedirs(os.path.join(workdir, 'outputs', sig_name), exist_ok=True)
        plot_graph(res,os.path.join(workdir, 'outputs', sig_name, 'test_date_days.html'), javascript_path = js_path)
    return True


