
def Test(df, si, codedir: str, workdir: str):
    if len(df)==0:
        return True
    cols=[x for x in df.columns if x=='pid' or 'value_' in x or 'time_' in x]
    sig_name=df['signal'].iloc[0]
    signal_columns=[ 'time_%d'%(i) for i in range (len(si.t_ch))] + [ 'value_%d'%(i) for i in range (len(si.v_ch))]
    signal_columns.append('pid')
    for col in cols:
        if col not in signal_columns:
            print(f'Skip columns {col} which is not needed in signal {sig_name}')
            continue
        null_date_cnt=len(df[df[col].isnull()])    
        if null_date_cnt/len(df)>0.001:
            print('Failed! There are %d(%2.3f%%) missing values for signal %s in col %s'%(null_date_cnt, 100*null_date_cnt/len(df), sig_name, col))
            return False
        if null_date_cnt > 0:
            print('There are %d(%2.3f%%) missing values for signal %s in col %s'%(null_date_cnt, 100*null_date_cnt/len(df), sig_name, col))
        df.drop(df.loc[df[col].isnull()].index, inplace=True) #clean nulls
        df.reset_index(drop=True, inplace=True)
    print('Done testing nulls in signal %s'%(sig_name))
    return True


