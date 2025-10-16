#!/usr/bin/env python
import os, sys, re
import pandas as pd
from PY_Helper import plot_graph

def convert_date(df, column_name):
    cond_0 = df[column_name]%100==0
    bad_date_sz = len(df[cond_0])
    if bad_date_sz > 0:
        df.loc[cond_0, column_name] = df.loc[cond_0, column_name] + 1
        print(f'Fixed date for column {column_name} where days was 0 for {bad_date_sz}({100*bad_date_sz/len(df):.3f}%) records out of {len(df)}')
    cond_0 = df[column_name]//100%100==0
    bad_date_sz = len(df[cond_0])
    if bad_date_sz > 0:
        df.loc[cond_0, column_name] = df.loc[cond_0, column_name] + 100
        print(f'Fixed date for column {column_name} where months was 0 for {bad_date_sz}({100*bad_date_sz/len(df):.3f}%) records out of {len(df)}')
    df[column_name]=pd.to_datetime(df[column_name], format='%Y%m%d')
    return df

def get_samples_stats(samples_pt, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    df=pd.read_csv(samples_pt, sep='\t')
    df = convert_date(df, 'time')
    df = convert_date(df, 'outcomeTime')

    df['time_gap_days']=(df['outcomeTime']-df['time']).dt.days
    df['time_gap_months'] = df['time_gap_days']//30
    
    #Print how many ids, has both cases/controls:
    fw=open(os.path.join(output_dir, 'stats.txt'), 'w')
    print('Outcome count per patient')
    fw.write('Outcome count per patient\n')
    outcome_cnt=df[['id', 'outcome']].groupby('id').nunique().reset_index().groupby('outcome').count().reset_index().rename(columns={'outcome':'distinct_outcome_count', 'id':'count'})
    if (outcome_cnt.distinct_outcome_count.max()>1):
        print(outcome_cnt)
        fw.write('%s\n'%(outcome_cnt))
    else:
        print('Each patient is either case or control')
        fw.write('Each patient is either case or control\n')
    fw.close()
    #How many times each patient apears in cases/control:
    cases=df[df['outcome']>0].reset_index(drop=True).copy()
    controls=df[df['outcome']<1].reset_index(drop=True).copy()
    cases_samples=cases[['id', 'time']].groupby('id').count().reset_index().groupby('time').count().reset_index().rename(columns={'time':'distinct_time', 'id':'count'})
    contrls_samples=controls[['id', 'time']].groupby('id').count().reset_index().groupby('time').count().reset_index().rename(columns={'time':'distinct_time', 'id':'count'})
    g={'controls': contrls_samples, 'cases': cases_samples}
    plot_graph(g, os.path.join(output_dir, 'cases_controls_id_histogram.html'), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))
    #Plot cases/controls gap from outcomeTime:
    cases_tm=cases[['id', 'time_gap_months']].groupby('time_gap_months').count().reset_index().rename(columns={'id':'count'})
    controls_tm=controls[['id', 'time_gap_months']].groupby('time_gap_months').count().reset_index().rename(columns={'id':'count'})
    g={'controls':controls_tm , 'cases': cases_tm}
    plot_graph(g, os.path.join(output_dir, 'cases_controls_outcome_time_gap.html'), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))

if __name__ == '__main__':
    if len(sys.argv)<2:
        raise NameError('Please provide 2 inputs')
    samples_path=sys.argv[1]
    output_dir=sys.argv[2]
    get_samples_stats(samples_path, output_dir)
