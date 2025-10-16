import pandas as pd
import numpy as np
import os
import med
import argparse

parser=argparse.ArgumentParser(description='filter')
parser.add_argument("--rep", required=True, help="the repository", type=str)
parser.add_argument("--samples", required=True, help="Samples to explore", type=str)
parser.add_argument("--output", required=True, help="txt file for output", type=str)

parser.add_argument("--time_windows", default="-1,365", help="comma seperated time windows for analysis", type=str)
parser.add_argument("--high_scores", default="10", help="comma seperated % of top high scores", type=str)

parser.add_argument("--prefix", default="", help="prefix for codes to search, empty list is all", type=str)
parser.add_argument("--mydic", required=True, help="path to file with unmapped diagnosis in the repo", type=str)

# init

args = parser.parse_args()
rep = med.PidRepository()

pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None) 

# functions

def add_age(df):
    signal = ['BDATE']
    rep.read_all(args.rep, df.id.tolist(), signal)
    bdate = rep.get_sig('BDATE')
    bdate.columns = ['id', 'bdate']
    df = df.merge(bdate.rename(columns={'pid':'id'}), on='id')
    df['age'] = df.time//10000 - df['bdate']//10000
    return df[['id', 'time', 'age', 'outcome', 'pred_0']]

def match_by_age(high, df):
    target = high.age.value_counts()
    low = {}
    for a in target.index:
        low[a] = df[df.age==a].sort_values(by='pred_0').head(target.loc[a])
    return pd.concat([low[a] for a in low.keys()])
    
def get_dic():
    mydic = pd.read_csv(args.mydic, sep='\t', names=['SECTION', 'codedesc', 'codedesc2'])
    mydic.loc[mydic.codedesc != mydic.codedesc2, 'codedesc'] = mydic.loc[mydic.codedesc != mydic.codedesc2, 'codedesc'] + mydic.loc[mydic.codedesc != mydic.codedesc2, 'codedesc2']
    
    if args.prefix != '':
        mydic = mydic[mydic.codedesc.str.startswith(args.prefix)]
        #mydic = mydic[mydic.codedesc.map(lambda x: x[9]>='A' and x[9]<='Q')] # for readcodes diagnosis
    
    return mydic
    
# main functions

def main2(time_window, low, high, sample_size, fname):
    low['highlow'] = 'low'
    high['highlow'] = 'high'
    df = pd.concat([low, high])
    
    mydic = get_dic()
    lendf = len(df)
    df = df.merge(mydic[['SECTION', 'codedesc']], on='SECTION', how='inner')
    print('Out of', lendf, 'diagnosis,', len(df), 'are with the requested prefix and not mapped (including duplicates)', file=outfile)
    
    df = df[df.diag_time < df.time]
    df['time'] = pd.to_datetime(df.time.astype(str), format = '%Y%m%d')
    df['diag_time'] = pd.to_datetime(df.diag_time.astype(str), format = '%Y%m%d')
    df['delta'] = (df['time'] - df['diag_time']).dt.days 
       
    if time_window == -1:
        print('\nNo time window limit for diagnosis', file=outfile)
        df = df[df.delta > 0]
    else:
        print('\nTime window limit for diagnosis is', time_window, 'days before sample time', file=outfile)
        df = df[df.delta.between(0, time_window)]
    df = df.drop_duplicates(subset=['id', 'SECTION'])
         
    df = df.groupby(['SECTION', 'codedesc', 'highlow']).id.count().unstack().reset_index()
    if 'low' not in df.columns:
        df['low'] = 0
    if 'high' not in df.columns:
        df['high'] = 0
       
    if len(df) > 0:
        df['ratio'] = (df.high + sample_size/20) / (df.low + sample_size/20)
       
        print('\nMost common diagnosis that are not mapped', file=outfile)
        df = df.sort_values(by='high', ascending=False)
        print(df.head(min(len(df),10)), file=outfile)
          
        print('\nDiagnosis with highest ratio between high and low that are not mapped', file=outfile)
        df = df.sort_values(by='ratio', ascending=False)
        print(df.head(min(len(df),10)), file=outfile)
        df.to_csv(outpath[:-3] + fname + '.csv')
        
    
def main1(high_score, sam, fname):
    print('\nHigh scores is set to', high_score, '% of the samples',  file=outfile)
    sam = sam.sort_values(by='pred_0', ascending=False)
    high = sam.head(int(len(sam) * high_score / 100))
    low = match_by_age(high, sam)
    sample_size = len(high)
    print('Sample Size:', sample_size, file=outfile)
    
    signal = ['DIAGNOSIS']
    rep.read_all(args.rep, high.id.tolist() + low.id.tolist(), signal)
    diag = rep.get_sig('DIAGNOSIS', translate=False)
    print('finish reading diagnosis')
    diag.columns = ['id', 'diag_time', 'SECTION']
    
    high = high.merge(diag, on='id', how='inner')
    low = low.merge(diag, on='id', how='inner')
    
    time_windows = args.time_windows.split(",")
    time_windows = [int(x) for x in time_windows]
    
    for time_window in time_windows:
        main2(time_window, low, high, sample_size, fname+'_'+str(high_score)+'_'+str(abs(time_window)))    

# main

outpath = args.output.replace(':','')
outfile = open(outpath, 'w')
sam = pd.read_csv(args.samples, sep='\t')
sam = sam.sample(frac=1).drop_duplicates(subset='id')
sam = add_age(sam)

high_scores = args.high_scores.split(",")
high_scores = [int(x) for x in high_scores]

has_outcome = len(sam.outcome.unique()) == 2

for high_score in high_scores:
    if has_outcome:
        print ('\nAnalysis is for CASES', file=outfile)
        main1(high_score, sam[sam.outcome==1], fname='cases')
        print ('\nAnalysis is for CONTROLS', file=outfile)
        main1(high_score, sam[sam.outcome==0], fname='controls')

    else:
        print ('\nNo outcome. Analysis is for ALL SAMPLES', file=outfile)
        main1(high_score, sam, fname='allSamples')
