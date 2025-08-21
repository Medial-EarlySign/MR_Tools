import pandas as pd
import numpy as np
import os
import re, math
from utils import write_tsv, replace_spaces, to_float
from sql_utils import get_sql_engine
from get_from_stage import get_values_for_code, get_values_for_one_code
from unit_converts import unit_convert
from special_cases import convert_ratio_to_numeric, convert_bdate_byear, mayo_special_cases, datetime_to_date
from thin_special_cases import handle_thin_special
from fix_factors import fixFactorsMixtureGaussian
import statistics
import time


EMPTY_VALUE = 'EMPTY_FIELD'


def decimalize_feet(s):
    m = re.match(r'\D*(\d*)\D+(\d*\.*\d*)\"\D*', s)
    if m:
        if m.group(1) == "" or m.group(2) == "":
            return s
        return float(m.group(1))*12 + float(m.group(2))
    else:
        return s  # to_float(s) * 2.54


def split_bp(s, pos):
    m = None
    if pos == 1:
        m = re.match(r'(\d*)/.+', s)
    elif pos == 2:
        m = re.match(r'.+/(\d*)', s)
    if m:
        if m.group(1) != "":
            return m.group(1)
    return s


def handel_special_cases(stage_def, sig, vals):
    if sig in stage_def.SPECIAL_CASES:
        if 'mimic' in stage_def.TABLE.lower():
            if sig == 'I_E_Ratio':
                vals['value'] = convert_ratio_to_numeric(vals['value'])
            if sig == 'BYEAR':
                vals['value'] = convert_bdate_byear(vals['value'])
                vals = vals[vals['value'] >= 1900]
            if sig == 'BDATE':
                vals['value'] = datetime_to_date(vals['value'])
                vals = vals[vals['value'].str[0:4].astype(int) >= 1900]
        if 'jilin' in stage_def.TABLE.lower():
            if sig == 'GENDER':
                vals['value'] = vals['value'].map({'male': 1, 'female': 2})
            if sig == 'BYEAR':
                # remove pid with more then 2 year of birth
                vals['value'] = vals['value'].astype(float).astype(int)
                pid_grp = vals.groupby('orig_pid')
                calc_df = pd.concat([pid_grp['value'].count().rename('value_count'),  pid_grp['value'].apply(list).rename('value_list')], axis=1)
                calc_df['diff'] = calc_df['value_list'].apply(lambda x: max(x) - min(x))
                calc_df.loc[calc_df['diff'] <= 1, 'value'] = calc_df['value_list'].apply(lambda x: min(x))
                calc_df.loc[calc_df['diff'] == 2, 'value'] = calc_df['value_list'].apply(lambda x: int(statistics.mean(x)))
                age_map = calc_df['value']
                vals = vals.merge(age_map.reset_index(), how='left', on='orig_pid')
                vals.rename(columns={'value_y': 'value'}, inplace=True)
                vals = vals[vals['value'].notnull()]
                vals['value'] = vals['value'].astype(int).astype(str)
        if 'kpnw' in stage_def.TABLE.lower():
            if sig == 'BP':
                vals['value2'] = vals['value'].apply(lambda x: split_bp(x, 2) if x else x)
                vals['value'] = vals['value'].apply(lambda x: split_bp(x, 1) if x else x)
                #vals['value2'] = vals['value'].apply(lambda x: x.split('/')[1] if x else x)
                #vals['value'] = vals['value'].apply(lambda x: x.split('/')[0] if x else x)
            if sig == 'GENDER':
                vals['value'] = vals['value'].replace('U', np.nan)
            if sig == 'Height':
                vals['value'] = vals['value'].apply(lambda x: decimalize_feet(x) if x else x)
            if sig == 'DEATH':
                vals['value'] = vals['value'].str[0:10].str.replace('-', '')
        if 'mayo' in stage_def.TABLE.lower():
            vals = mayo_special_cases(sig, vals)
    if 'thin' in stage_def.TABLE.lower():
        vals = handle_thin_special(sig, vals, stage_def.TABLE.lower())
    return vals


def regex_to_file(stage_def, signal_map, id2nr_map, out_folder, suff=None):
    error_file = 'errors.txt'
    sig_suf = ''
    if suff:
        sig_suf = suff

    db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)
    for sig, sig_grp in signal_map.groupby('signal'):
        if os.path.exists(os.path.join(out_folder, sig + sig_suf + '1')) | \
                os.path.exists(os.path.join(out_folder, sig + sig_suf)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        for rx in codes_list:
            sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code ~ '" + rx + "'"
            print(sql_query)
            cnt = 1
            saves = 1
            collct_df = pd.DataFrame()
            time1 = time.time()
            need_filter=False
            if stage_def.DBTYPE == 'FILE':
                df_iterator= pd.read_csv(os.path.join(stage_def.DBNAME, stage_def.TABLE), sep='\t', chunksize=10000000)
                need_filter=True
            else:
                df_iterator=pd.read_sql_query(sql_query, db_engine, chunksize=10000000)
            for vals in df_iterator:
                if need_filter:
                    vals = vals[vals['code'].str.contains(rx)].reset_index(drop=True)
                print('   read chuck ' + str(cnt))
                time2 = time.time()
                print(' Query time =' +  str(round(time2 - time1)))
                if stage_def.TABLE == 'thinlabs':
                    cond = vals['source'].isnull()
                    if vals[vals['source'].isnull()].shape[0] > 0:
                        print(vals[vals['source'].isnull()])
                    vals, all_errors = remove_errors(vals, all_errors, cond, 'no_val')
                    vals['value'] = vals['source'].apply(lambda x: x.split('|')[1])
                vals = handel_special_cases(stage_def, sig, vals)
                if vals.empty:
                    continue
                vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map)
                vals['signal'] = sig
                cond = vals['medialid'].isnull()
                vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')

                cond = vals['date1'].isnull()
                vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')

                cond = pd.DatetimeIndex(vals['date1']).year < 1900
                vals, all_errors = remove_errors(vals, all_errors, cond, 'before1900')

                vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
                collct_df = collct_df.append(vals, ignore_index=True, sort=False)
                print(collct_df.shape[0])
                if collct_df.shape[0] >= 100000000:
                    print('going to save file ' + sig + sig_suf + str(saves))
                    collct_df['id_int'] = collct_df['medialid'].astype(int)
                    collct_df.sort_values(by=['id_int', 'date1'], inplace=True)
                    cols = ['medialid', 'signal', 'date1', 'value', 'source']
                    sig_file = sig + sig_suf + str(saves)
                    saves += 1
                    write_tsv(collct_df[cols], out_folder, sig_file)
                    del collct_df
                    collct_df = pd.DataFrame()
                    print(' File ' + sig_file + ' saved')
                cnt += 1
                time1 = time.time()
                print(' Procces time = '+str(round(time1-time2)))
        if all_errors.shape[0] > 0:
            cols = ['medialid', 'signal', 'date1', 'value', 'source']
            write_tsv(all_errors[cols + ['reason', 'description']], out_folder, error_file)
        # Save remains
        print(collct_df.shape[0])
        print('going to save file ' + sig + sig_suf + str(saves))
        collct_df['id_int'] = collct_df['medialid'].astype(int)
        collct_df.sort_values(by=['id_int', 'date1'], inplace=True)
        cols = ['medialid', 'signal', 'date1', 'code', 'source']
        sig_file = sig + sig_suf + str(saves)
        saves += 1
        write_tsv(collct_df[cols], out_folder, sig_file)
        print(' File ' + sig_file + ' saved')

def plot_graph(y, save_path, mode='markers+lines'):
    import plotly.graph_objs as go
    fig=go.Figure()
    df=pd.DataFrame(y, columns=['value'])
    df['signal']=1
    
    df = df[['value', 'signal']].groupby('value').count().reset_index()
    amode=mode
    fig.add_trace(go.Scatter(x=df['value'], y=df['signal'] ,mode=amode, name='histogram'))
    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title='Value')
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title='Count')
    fig.layout.plot_bgcolor='white'
    fig.layout.title='Plot'
    fig.write_html(save_path)
    print('Wrote html into %s'%(save_path))

def round_num(ser, rnd_ser):
    #epsi = 0.000001
    #rel_rnd = int(abs(math.log10(rnd_ser)))
    rel_rnd = 10**(math.ceil(-(math.log10(1 if int(rnd_ser)==rnd_ser else rnd_ser-int(rnd_ser)))))
    new_ser = ser/rnd_ser
    new_ser = new_ser.round(0)
    new_ser = new_ser*rnd_ser
    new_ser=  (new_ser*rel_rnd).apply(lambda x: float(round(x)))/rel_rnd
    #new_ser = new_ser.round(rel_rnd)
    return new_ser

#inputs:
#vals with cols:['orig_pid', 'date1', 'value' (, 'value2' optional) , 'source', 'unit' (, 'code' optional)]
#stage_def - Configuration for DB and special cases (can be None to skip)
# sig - string signal name
#sig_buf - string - buffer to add signal name when there are splits. can be ''
#id2nr_map - converted of id2nr (can be None to skip)
#unit_mult - unit translator reading dataframe
#sig_factors - configuration for mixture of guisian if needed. can pass [] to skip
#cnt chunk number - for printing qand writing files
#all_errors - dataframe of errors. can start with all_errors = pd.DataFrame()
#out_folder - output folder to write loading files
#debug_input - output folder to write debug files (optional, can be None to cancel)
def handle_batch(vals, stage_def, sig, sig_suf, id2nr_map, unit_mult, sig_factors, cnt, all_errors, out_folder, debug_input):
    if stage_def is not None:
        vals = handel_special_cases(stage_def, sig, vals)
    if vals.empty:
        return
    if id2nr_map is not None:
        vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map)
    else:
        vals['medialid'] = vals['orig_pid']
    if cnt is None:
        cnt=''
    print('   read chuck ' + str(cnt))
    vals['signal'] = sig
    cond = vals['medialid'].isnull()
    vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')

    cond = vals['date1'].isnull()
    vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')

    cond = vals['value'].isnull()
    vals, all_errors = remove_errors(vals, all_errors, cond, 'no_value')

    cond = pd.DatetimeIndex(vals['date1']).year < 1900
    vals, all_errors = remove_errors(vals, all_errors, cond, 'before1900')
    if 'value2' in vals.columns:
        vals.drop_duplicates(subset=['medialid', 'date1', 'value', 'value2'], inplace=True)
    else:
        vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
    if (debug_input is not None):
        vals.to_csv(os.path.join(debug_input, sig + sig_suf + str(cnt)), sep='\t', index=False)
        print('Wrote debug file without unit convertor into %s'%(os.path.join(debug_input, sig + sig_suf + str(cnt))))
    vals, errs = unit_convert(sig, vals, unit_mult)
    all_errors = all_errors.append(errs, sort=False)
    if 'code' in vals.columns:
        vals['source'] = vals['source'] + '_' + vals['code'].astype(str)
    vals['source'] = vals['source'].str.replace(' ', '_')
    #vals['date2'] = vals['date2'].where(vals['date2'].notnull(), vals['date1'])
    #vals['date2'] = vals['date2'].astype('datetime64[ns]')
    vals['unit'] = vals['unit'].where(vals['unit'].notnull(), 'None')
    vals['id_int'] = vals['medialid'].astype(int)
    vals.sort_values(by=['id_int', 'date1'], inplace=True)
    if 'value2' in vals.columns:
        cols = ['medialid', 'signal', 'date1', 'value', 'value2', 'unit', 'source']
    else:
        cols = ['medialid', 'signal', 'date1', 'value', 'unit', 'source']
    #if os.path.exists(os.path.join(out_folder, sig)):
    #    os.remove(os.path.join(out_folder, sig))
    sig_file = sig + sig_suf + str(cnt)
    time3 = time.time()
    #handle mixture of units if needed (only suppoerfix in first value channel. no problems in other channels yet):
    if len(sig_factors) >0:
        mean_val=None
        if not(pd.isna(sig_factors['SupposeMean'].iloc[0])):
            mean_val=sig_factors['SupposeMean'].iloc[0]
        trim_max=1e6
        if not(pd.isna(sig_factors['trim_max'].iloc[0])):
            trim_max=sig_factors['trim_max'].iloc[0]
        fix_std=True
        if not(pd.isna(sig_factors['variable_std'].iloc[0])):
            fix_std=not(sig_factors['variable_std'].iloc[0] > 0)
        if cnt!='':
            print('Fixing mixture of guassians in signal %s, batch %d'%(sig, cnt))
        else:
            print('Fixing mixture of guassians in signal %s'%(sig))
        try:
            vals['value'] = fixFactorsMixtureGaussian(vals['value'].to_numpy(),[ sig_factors['factors'].iloc[0]], sig_factors['error_threshold'].iloc[0],
                                                  trim_max, mean_val, fix_std)
            if not(pd.isna(sig_factors['FinalFactor'].iloc[0])):
                vals['value'] = vals['value']* sig_factors['FinalFactor'].iloc[0]
            if not(pd.isna(sig_factors['Resolution'].iloc[0])):
                vals['value'] = round_num(vals['value'], sig_factors['Resolution'].iloc[0])
        except:
            bs_path=os.path.join(out_folder, 'mixture_errors')
            os.makedirs(bs_path, exist_ok=True)
            fpath=os.path.join(bs_path, sig + '_' + str(cnt) + '.no_mixture.html')
            plot_graph(vals['value'].to_numpy(), fpath)
            vals[['value']].to_csv(os.path.join(bs_path, sig + '_' + str(cnt) + '.no_mixture.csv'), index=False)
            print('Maybe it\'s not a mixture? - continuing\nplease check:%s'%(fpath))
            
        
    write_tsv(vals[cols], out_folder, sig_file, mode='w')
    time1 = time.time()
    print(str(cnt) +') Save time time for chunk ' + str(time1 - time3))
    return time1

def numeric_to_files(stage_def, signal_map, unit_mult, unit_special_factor , id2nr_map, out_folder, suff=None, main_cond='code', debug_input=None):
    error_file = 'errors.txt'
    sig_suf = ''
    if suff:
        sig_suf = suff
    unit_mult['unit'] = unit_mult['unit'].str.lower().str.strip()
    unit_mult.drop_duplicates(inplace=True)
    unit_mult.loc[unit_mult['rndf'].isnull(), 'rndf'] = unit_mult[unit_mult['rndf'].isnull()]['rnd']
    db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)
    for sig, sig_grp in signal_map.groupby('signal'):
        if os.path.exists(os.path.join(out_folder, sig+sig_suf+'1')) | \
                os.path.exists(os.path.join(out_folder, sig+sig_suf)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        sig_factors=unit_special_factor[unit_special_factor['signal']==sig]
        print(sig, codes_list)
        if main_cond == 'code':
            sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code in ('" + "','".join(codes_list) + "')"
        else:
            where = ''
            for cd in codes_list:
                where = where + "source like '%" + cd + "%' OR "
            where = where[:-3]
            sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code like '%%_data1' AND source  SIMILAR  TO '%%(" + "|".join(codes_list) + ")%%'"
            #sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code like '%%_data1'"  #  AND " + where
        print(sql_query)
        cnt=1
        time1 = time.time()
        time_start = time1
        
        if (debug_input is not None) and os.path.exists(os.path.join(debug_input, sig + sig_suf + str(1))):
            all_files=os.listdir(debug_input)
            all_sigs_files=list(filter(lambda x: x.startswith(sig + sig_suf) ,all_files))
            for f in all_sigs_files:
                full_f = os.path.join(debug_input, f)
                vals=pd.read_csv(full_f, sep='\t')
                time2 = time.time()
                print(str(cnt) + ') Read(from file) time for chunk: ' + str(time2 - time1))
                
                time1 = handle_batch(vals, stage_def, sig, sig_suf, id2nr_map, unit_mult, sig_factors, cnt, all_errors, out_folder, None)
                print(str(cnt) +') Total time for chunk ' + str(time1 - time2))
                cnt += 1
        else:
            need_filter=False
            if stage_def.DBTYPE == 'FILE':
                df_iterator= pd.read_csv(os.path.join(stage_def.DBNAME, stage_def.TABLE), sep='\t', chunksize=15000000)
                need_filter=True
            else:
                df_iterator=pd.read_sql_query(sql_query, db_engine, chunksize=15000000)
            for vals in df_iterator:
                if need_filter:
                    if main_cond == 'code':
                        vals=vals[vals['code'].isin(codes_list)].reset_index(drop=True)
                    else:
                        vals=vals[(vals['code'].str.endswith('_data1')) & (vals['source'].str.contains('|'.join(codes_list)))].reset_index(drop=True)
                time2 = time.time()
                print(str(cnt) + ') Query time for chunk: ' + str(time2 - time1))
                
                time1 = handle_batch(vals, stage_def, sig, sig_suf, id2nr_map, unit_mult, sig_factors, cnt, all_errors, out_folder, debug_input)
                print(str(cnt) +') Total time for chunk ' + str(time1 - time2))
                cnt += 1

        if all_errors.shape[0] > 0:
            add_cols = [x for x in all_errors.columns if x in ['reason', 'orig_val', 'description']]
            write_tsv(all_errors[cols+add_cols], out_folder, error_file)

        print('Total time signal ' + sig + ': ' + str(time.time() - time_start))


def remove_errors(val_df, all_errors, cond, reason):
    if val_df[cond].shape[0] > 0:
        errs = val_df[cond].copy()
        errs['reason'] = reason
        val_df = val_df[~cond]
        all_errors = all_errors.append(errs, sort=False)
    return val_df, all_errors


def clean_values(val_ser):
    val_ser = val_ser.str.lower()
    val_ser = val_ser.where(~((val_ser.str.contains('see')) & (val_ser.str.contains('note'))) & (val_ser != 'sn'), 'see_note')
    val_ser = val_ser.where(~(val_ser.str.contains('neg')) & (val_ser != 'n'), 'negative')
    val_ser = val_ser.where(~val_ser.str.contains('pos'), 'positive')
    val_ser = val_ser.where(~val_ser.str.contains('norm'), 'normal')
    val_ser = val_ser.where(~(val_ser.str.contains('full')), 'full_field')
    val_ser = replace_spaces(val_ser)
    return val_ser


def categories_to_files(stage_def, signal_map, id2nr_map, out_folder, suff=None):
    sig_suf = ''
    if suff:
        sig_suf = suff
    error_file = 'errors.txt'
    db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)

    for sig, sig_grp in signal_map.groupby('signal'):
        sig_file = sig + sig_suf
        if os.path.exists(os.path.join(out_folder, sig_file)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        vals = get_values_for_code(db_engine, stage_def.TABLE, codes_list)
        vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map)
        vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
        vals['signal'] = sig
        vals = handel_special_cases(stage_def, sig, vals)
        #cond = vals['value'].isnull()
        #vals, all_errors = remove_errors(vals, all_errors, cond, 'no_value')

        #cond = vals['value'] == 'nan'
        #vals, all_errors = remove_errors(vals, all_errors, cond, 'no_value')

        vals['value'] = vals['value'].replace('nan', np.NaN)
        vals.loc[vals['value'].str.strip() == '', 'value'] = np.NaN
        vals['value'] = vals['value'].replace('', np.NaN)
        vals['value'].fillna(EMPTY_VALUE, inplace=True)

        cond = vals['medialid'].isnull()
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')

        cond = vals['date1'].isnull()
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')
        if stage_def.TABLE == 'thinlabs' or stage_def.TABLE == 'mimiclabs':
            vals['value'] = clean_values(vals['value'])
        else:
            vals['value'] = replace_spaces(vals['value'])
        vals['source'] = vals['source'] + '_' + vals['code'].astype(str)
        vals['source'] = vals['source'].str.replace(' ', '_')
        # vals['date2'] = vals['date2'].where(vals['date2'].notnull(), vals['date1'])
        # vals['date2'] = vals['date2'].astype('datetime64[ns]')
        vals['id_int'] = vals['medialid'].astype(int)
        vals.sort_values(by=['id_int', 'date1'], inplace=True)
        cols = ['medialid', 'signal', 'date1', 'value', 'source']
        if os.path.exists(os.path.join(out_folder, sig_file)):
            os.remove(os.path.join(out_folder, sig_file))
        write_tsv(vals[cols], out_folder, sig_file)
        if all_errors.shape[0] > 0:
            write_tsv(all_errors[cols+['reason', 'description']], out_folder, error_file)


def demographic_to_files(stage_def, signal_map, id2nr_map, out_folder):
    error_file = 'errors.txt'
    db_engine = get_sql_engine(stage_def.DBTYPE, stage_def.DBNAME, stage_def.username, stage_def.password)
    for sig, sig_grp in signal_map.groupby('signal'):
        if os.path.exists(os.path.join(out_folder, sig)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        #sql_query = "SELECT * FROM " + stage_def.TABLE + " WHERE code in ('" + "','".join(codes_list) + "') limit 10000000"
        #print(sql_query)
        #vals = pd.read_sql(sql_query, db_engine)
        vals = get_values_for_code(db_engine, stage_def.TABLE, codes_list)
        #vals = get_values_for_one_code(db_engine, stage_def.TABLE, mapi['code'])
        # vals = get_column_vals(db_engine, stage_def.TABLE, mapi['code'])
        vals = handel_special_cases(stage_def, sig, vals)

        vals['signal'] = sig

        vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map)
        cond = vals['medialid'].isnull()
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')
        if not pd.api.types.is_numeric_dtype(vals['value'].dtype):
            vals['value'] = vals['value'].str.strip()
            cond = (vals['value'].isnull()) | (vals['value']=='')
        else:
            cond = (vals['value'].isnull())
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_val')

        if sig_grp.iloc[0]['type'] == 'string' or sig_grp.iloc[0]['type'] == 'category':
            vals['value'] = replace_spaces(vals['value'])

        vals.drop_duplicates(subset=['medialid', 'value'], inplace=True)
        vals['id_int'] = vals['medialid'].astype(int)
        if 'date1' in vals.columns and not vals['date1'].isnull().all():
            vals.loc[:, 'date1'] = vals['date1'].str[6:10] + vals['date1'].str[3:5] + vals['date1'].str[0:2]
            cols = ['medialid', 'signal', 'date1', 'value']
        else:
            cols = ['medialid', 'signal', 'value']

        vals.sort_values(by=['id_int'], inplace=True)
        if os.path.exists(os.path.join(out_folder, sig)):
            os.remove(os.path.join(out_folder, sig))
        write_tsv(vals[cols], out_folder, sig)
        if all_errors.shape[0] > 0:
            write_tsv(all_errors[cols + ['reason', 'description']], out_folder, error_file)
