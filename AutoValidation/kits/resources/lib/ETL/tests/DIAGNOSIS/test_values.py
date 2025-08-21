from datetime import datetime

def Test(df, si, codedir, workdir):
    sig_name=df['signal'].iloc[0]
    bad_values=df[~df['value_0'].astype(str).map(lambda x: x.startswith('ICD9_CODE:') or x.startswith('ICD10_CODE:'))]
    if len(bad_values)>0:
        stats=bad_values['value_0'].value_counts()
        print('DIAGNOSIS Bad values: ')
        print(stats)
        return False
    return True


