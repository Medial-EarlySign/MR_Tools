import pandas as pd

MIN_REPO_DATE = 19010101
MAX_REPO_DATE = 20220101

def format_date(s):
    tokens=s.split('/')
    return tokens[2]+tokens[1] + tokens[0]

def fix_date(data, col):
    data.loc[data[col].notnull(),col] = data.loc[data[col].notnull(),col].map(lambda x: format_date(x) if len(x)==10 and x.find('/') else '-1')
    return data

def check_and_fix_date(data, col):
    data.loc[~data[col].str.isnumeric(), col] = '-1'
    data.loc[data[col]=='00000000', col] = '-1'
    data[col] = data[col].map(lambda x: x if len(x)==8 else x + '01' if len(x)==6 else x + '0101' if len(x)==4 else '-1')
    data[col] = data[col].map(lambda x: x[0:4] + '0101' if x[4:8]=='0000' else x[0:6] + '01' if x[6:8]=='00' else x)
    
    before = len(data)
    
    data = data[data[col] != '-1'].reset_index(drop=True)
    after = len(data)
    if after < before:
        print('Drop ' + str(before - after) + ' out of ' + str(before) + ' because data is invalid')
    
    data[col] = data[col].astype(int)
    return data