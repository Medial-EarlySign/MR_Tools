from datetime import datetime

def Test(df, si, codedir: str, workdir: str):
    sig_name=df['signal'].iloc[0]
    cnt=df[['pid', 'signal']].groupby('pid').count().reset_index().sort_values('signal', ascending=False)
    if cnt.iloc[0]['signal']>1:
        print(f'Signal {sig_name} has multiple values for same pid')
        return False
    return True
