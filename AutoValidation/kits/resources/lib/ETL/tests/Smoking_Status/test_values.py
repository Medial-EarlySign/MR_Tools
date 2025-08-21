from datetime import datetime

def Test(df, si, codedir, workdir):
    sig_name=df['signal'].iloc[0]
    allowed_values= ['Current', 'Never', 'Passive', 'Former', 'Never_or_Former', 'Unknown']
    bad_values=df[~df['value_0'].isin(allowed_values)]
    if len(bad_values)>0:
        stats=bad_values['value_0'].value_counts()
        print('Smoking_Status Bad values: ')
        print(stats)
        return False
    return True


