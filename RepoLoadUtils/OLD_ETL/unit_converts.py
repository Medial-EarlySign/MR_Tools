import pandas as pd
import traceback
import math


def value_to_numeric(val_ser, val):
    numeric_ser = pd.to_numeric(val_ser, errors='coerce')
    non_numeric_df = pd.DataFrame(val_ser[numeric_ser.isnull()])
    print('  Non numeric before clean: ' + str(non_numeric_df.shape[0]))
    if non_numeric_df.shape[0] == 0:
        return numeric_ser
    # negative values are set to zero
    neg_cond = (non_numeric_df[val] == 'NEG') | (non_numeric_df[val] == 'NEGATIVE')
    non_numeric_df.loc[neg_cond, val] = '0'
    non_numeric_df['splited'] = non_numeric_df[val].str.split('-', expand=False)
    non_numeric_df['numeric'] = non_numeric_df[val].str.extract('(\d+)')
    non_numeric_df['less'] = (non_numeric_df[val].str.lower().str.contains('less')) | (non_numeric_df[val].str.contains('<'))
    non_numeric_df['great'] = (non_numeric_df[val].str.lower().str.contains('great')) | (non_numeric_df[val].str.contains('>'))
    non_numeric_df['cs'] = non_numeric_df[val].str.lower().str.contains('cs')
    # For less then values take 80% of value
    less_cond = (non_numeric_df['less']) & (non_numeric_df['numeric'].notnull())
    non_numeric_df.loc[less_cond, val] = non_numeric_df[less_cond]['numeric'].astype(float) * 0.8
    # For grater then values take 120% of value
    grt_cond = (non_numeric_df['great']) & (non_numeric_df['numeric'].notnull())
    non_numeric_df.loc[grt_cond, val] = non_numeric_df[grt_cond]['numeric'].astype(float) * 1.2
    # If value contain cs take the numeric value found in val
    cs_cond = (non_numeric_df['cs']) & (non_numeric_df['numeric'].notnull())
    non_numeric_df.loc[cs_cond, val] = non_numeric_df[cs_cond]['numeric'].astype(float)
    # if value is range take the middle
    range_cond = (non_numeric_df['splited'].str.len() > 1) & (non_numeric_df['numeric'].notnull())
    non_numeric_df.loc[range_cond,val] = (pd.to_numeric(non_numeric_df[range_cond]['splited'].str[0],
                                                             errors='coerce') + pd.to_numeric(
        non_numeric_df[range_cond]['splited'].str[1], errors='coerce')) / 2
    non_numeric_df.loc[range_cond, val] = non_numeric_df[range_cond][val].astype(float).round(0)
    # print(non_numeric_df[val])
    numeric_ser.loc[numeric_ser.isnull()] = non_numeric_df[val]
    return numeric_ser


def round_ser(ser, rnd_ser):
    #epsi = 0.000001
    rel_rnd = rnd_ser.apply(lambda x: 10**(math.ceil(-(math.log10(1 if int(x)==x else x-int(x))))))
    new_ser = ser/rnd_ser
    new_ser = new_ser.round(0)
    new_ser = new_ser*rnd_ser
    #new_ser = new_ser.round(rel_rnd)
    new_ser = (new_ser*rel_rnd).apply(lambda x: float(round(x)))/rel_rnd
    return new_ser


def signal_unit_convert(sig, signal_df, convert_map):
    errors = pd.DataFrame()
    try:
        signal_df['unit'] = signal_df['unit'].str.lower().str.strip()
        signal_df['unit'].fillna('none', inplace=True)
        signal_df = pd.merge(signal_df, convert_map, how='left', left_on=['signal', 'unit'], right_on=['signal', 'unit'])
        signal_df = signal_df[(signal_df['mult'].notnull()) | (signal_df['add'].notnull())]
        signal_df['mult'].fillna(1, inplace=True)
        signal_df['add'] = signal_df['add'].astype(float).fillna(0)
        signal_df['mult_float'] = pd.to_numeric(signal_df['mult'], errors='coerce')
        signal_df['mult_float'].fillna(1, inplace=True)
        signal_df['rndf']=signal_df['rndf'].astype(float)
        signal_df['rnd']=signal_df['rnd'].astype(float)
        vals = [x for x in signal_df.columns if 'value' in x]
        for val in vals:
            if signal_df[val].isnull().all():
                continue
            signal_df['orig_val'] = signal_df[val]
            signal_df[val] = value_to_numeric(signal_df[val], val)
            if all(pd.to_numeric(signal_df[val], errors='coerce').isnull()):
                print('Signal: "' + sig + '" All values are not numeric ')
                errors = errors.append(signal_df.copy())
                errors['reason'] = 'all_non_numeric'
                return signal_df
            signal_df[val] = pd.to_numeric(signal_df[val], errors='coerce')
            errors = errors.append(signal_df[signal_df[val].isnull()].copy())
            errors['reason'] = 'non_numeric'
            print(str(signal_df[signal_df[val].isnull()].shape[0]) + '(' + str(signal_df.shape[0]) + ') values can not be converted to numeric')
            signal_df = signal_df.loc[signal_df[val].notnull()]

            signal_df[val] = round_ser(signal_df[val], signal_df['rnd'])  # round first before multiply
            if 'Formula1' in signal_df['mult'].astype(str).values:
                signal_df[val] = signal_df[val].where(signal_df['mult'].str.contains('Formula1') == False, 100 / signal_df[val])
            signal_df[val] = signal_df[val] * signal_df['mult_float'] + signal_df['add']
            signal_df[val] = round_ser(signal_df[val], signal_df['rndf'])  # round first before multiply
        signal_df['unit'] = signal_df['unit'].where(signal_df['unit'] != 'null', 'null_value')
    except BaseException:
        print('Error In unit conversion for signal %s' % sig)
        traceback.print_exc()
        raise
    return signal_df, errors


def unit_convert(sig, signal_df, convert_map):
    if sig not in convert_map['signal'].values:
        print('Signal "' + sig + '" has no unit conversion defined')
        errors = pd.DataFrame()
    else:
        signal_df, errors = signal_unit_convert(sig, signal_df, convert_map)
    return signal_df, errors
