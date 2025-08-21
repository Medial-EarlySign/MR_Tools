import pandas as pd

def test_numeric(df, col, allow_date_transforms=True):
    df[col + '_before']=df[col]
    if allow_date_transforms:
        df[col]=pd.to_numeric( df[col].astype(str).map(lambda x: x.replace('/','').replace('-','')), errors='coerce')
    else:
        df[col]=pd.to_numeric(df[col], errors='coerce')
    before_nana=len(df)
    examples=df[df[col].isnull()].reset_index(drop=True)
    df=df[df[col].notnull()].reset_index(drop=True)
    df=df.drop(columns=[col + '_before'])
    if len(df)!=before_nana:
        print(f'Removed non numeric in {col}. size was {before_nana}, now {len(df)}. Excluded {before_nana-len(df)}')
        print('Empty examples:')
        print(examples[col+'_before'].value_counts(dropna=False))
    return df


def rename_cols(df):
    df=df.rename(columns={'ID':'pid', 'Signal': 'signal', 'Date': 'time_0', 'Value': 'value_0', 'Unit': 'unit'})
    return df