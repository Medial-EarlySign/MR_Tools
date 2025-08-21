from datetime import datetime

def Test(df, si, codedir: str, workdir: str):
    sig_name=df['signal'].iloc[0]
    allowed_values= ['1', '2', 'Male', 'Female', 'M', 'F']
    bad_values=df[~df['value_0'].isin(allowed_values)]
    if len(bad_values)>0:
        stats=bad_values['value_0'].value_counts()
        print('Gender Bad values: ')
        print(stats)
        return False
    return True


