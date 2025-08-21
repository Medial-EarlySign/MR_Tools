from datetime import datetime

def Test(df, si, codedir, workdir):
    sig_name=df['signal'].iloc[0]
    bad_values=df[(df['value_0'].astype(float)<0) | (df['value_0'].astype(float)>200)]
    if len(bad_values)>0:
        stats=bad_values['value_0'].value_counts()
        print(f'{sig_name} Bad values: ')
        print(stats)
        return False
    return True


