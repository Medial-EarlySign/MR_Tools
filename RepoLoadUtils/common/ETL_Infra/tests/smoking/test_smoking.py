from datetime import datetime
import pandas as pd

def Test(df: pd.DataFrame, si, codedir: str, workdir: str):
    sig_name=df['signal'].iloc[0]
    
    if sig_name=='Smoking_Quit_Date':
        to_drop = df.time_0.astype(int) < pd.to_numeric(df.value_0).astype(int)
        if to_drop.sum() > len(df)*0.01:
            print('Failed! There are %d(%2.3f%%) rows with quit_date > signal_time for signal Smoking_Quit_Date'%(to_drop.sum(), 100*to_drop.sum()/len(df)))
            return False
        if to_drop.sum() > 0:
            print('There are %d(%2.3f%%) rows with quit_date > signal_time for signal Smoking_Quit_Date'%(to_drop.sum(), 100*to_drop.sum()/len(df)))
            #clean ilegal
            df = df[~to_drop]
            df = df.reset_index(drop=True, inplace=True)
        print(f'Done testing Smoking_Quit_Date')
        return True
    
    if sig_name=='Smoking_Status':
        first_smoker = df[df.value_0.isin(['Current', 'Former'])].groupby('pid').time_0.min().reset_index().rename(columns={'time_0':'smoker'})
        last_never = df[df.value_0=='Never'].groupby('pid').time_0.max().reset_index().rename(columns={'time_0':'never'})
        merged = first_smoker.merge(last_never, on='pid', how='inner')
        merged = merged[merged.smoker < merged.never]
        if len(merged) > 0:
            print('There are', len(merged), 'patients with Never after Smoker or Ex Smoker, out of', len(first_smoker), ' - ', round(100*len(merged)/len(first_smoker),2), '%')

    return True



