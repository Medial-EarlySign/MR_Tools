import pandas as pd


def convert_ratio_to_numeric(values_ser):
    numeric_ser = pd.to_numeric(values_ser, errors='coerce')
    ratio_df = pd.DataFrame(values_ser[numeric_ser.isnull()])
    ratio_df['value'] = ratio_df['value'].str.replace(';', ':')
    ratio_df['value'] = ratio_df['value'].str.replace('..', ':', regex=False)
    ratio_df['value'] = ratio_df['value'].str.replace('/', ':', regex=False)
    ratio_df['splited'] = ratio_df['value'].str.split(':', expand=False)
    range_cond = (ratio_df['splited'].str.len() == 2) & (ratio_df['value'].notnull())

    ratio_df.loc[range_cond, 'value'] = pd.to_numeric(ratio_df[range_cond]['splited'].str[0], errors='coerce') / pd.to_numeric(ratio_df[range_cond]['splited'].str[1], errors='coerce')
    numeric_ser.loc[numeric_ser.isnull()] = ratio_df['value']
    return numeric_ser


def convert_bdate_byear(values_ser):
    dt_ser = values_ser.astype('datetime64[ns]')
    return dt_ser.dt.year


def datetime_to_date(values_ser):
    return values_ser.str[0:10]


def mayo_special_cases(sig, vals_df):
    #if sig == 'GENDER':
    #    vals_df['value'] = vals_df['value'].map({'M': 1, 'F': 2})
    if sig == 'BDATE':
        vals_df['value'] = pd.to_datetime(vals_df['value'], format='%m/%d/%Y %H:%M').dt.date
    if sig == 'BYEAR':
        vals_df['value'] = pd.to_datetime(vals_df['value'], format='%m/%d/%Y %H:%M').dt.year
    return vals_df
