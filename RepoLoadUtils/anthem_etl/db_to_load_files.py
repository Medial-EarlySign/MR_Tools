import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from Configuration import Configuration
sys.path.append('/mnt/project/Tools/RepoLoadUtils/common')
from sql_utils import create_postgres_engine_generic
from utils import write_tsv, read_tsv, add_fisrt_line
from generate_id2nr import get_id2nr_map
#from tarin_signal import create_train_signal
from DB import DB
from stage_to_signals import remove_errors, unit_convert
import math


def round_ser(ser, rnd):
    #epsi = 0.000001
    rel_rnd = int(abs(math.log10(rnd)))
    new_ser = ser.round(rel_rnd)
    return new_ser


def numeric_to_files(db_det, signal_map, unit_mult, id2nr_map, out_folder, suff=None):
    error_file = 'errors.txt'
    sig_suf = ''
    if suff:
        sig_suf = suff
    unit_mult['unit'] = unit_mult['unit'].str.lower().str.strip()
    unit_mult.drop_duplicates(inplace=True)
    unit_mult.loc[unit_mult['rndf'].isnull(), 'rndf'] = unit_mult[unit_mult['rndf'].isnull()]['rnd']
    lab_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_labs_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    for sig, sig_grp in signal_map.groupby('signal'):
        if os.path.exists(os.path.join(out_folder, sig+sig_suf+'1')) | \
                os.path.exists(os.path.join(out_folder, sig+sig_suf)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        select = "membernumberhci as orig_pid, testname as code, testname as description, resulttext as value, servicedate as date1, unitsid as unit, 'abs_sample_3years' as source"
        sql_query = "SELECT " + select + " FROM " + lab_table + " WHERE code in ('" + "','".join(codes_list) + "')"
        sql_query = sql_query.replace('%', '%%')
        print(sql_query)
        cnt=1
        for vals in pd.read_sql_query(sql_query, db_engine, chunksize=5000000):
            #vals = get_values_for_code(db_engine, stage_def.TABLE, codes_list)
            #vals = handel_special_cases(stage_def, sig, vals)
            if vals.empty:
                continue
            vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map)
            print('   read chuck ' + str(cnt))
            vals['signal'] = sig
            cond = vals['medialid'].isnull()
            vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')

            cond = vals['date1'].isnull()
            vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')

            cond = pd.DatetimeIndex(vals['date1']).year < 1900
            vals, all_errors = remove_errors(vals, all_errors, cond, 'before1900')


            if 'value2' in vals.columns:
                vals.drop_duplicates(subset=['medialid', 'date1', 'value', 'value2'], inplace=True)
            else:
                vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
            vals, errs = unit_convert(sig, vals, unit_mult)
            ##  Special cases:
            if sig == 'Eosinophils#':
                vals['value'] = vals['value'].where(vals['value'] < 10, vals['value'] / 1000)
                vals['value'] = round_ser(vals['value'], 0.01)
            ##
            all_errors = all_errors.append(errs, sort=False)
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
            sig_file = sig + sig_suf + str(cnt)
            cnt+=1
            write_tsv(vals[cols], out_folder, sig_file, mode='w')
        if all_errors.shape[0] > 0:
            add_cols = [x for x in all_errors.columns if x in ['reason', 'orig_val', 'description']]
            write_tsv(all_errors[cols+add_cols], out_folder, error_file)


def labs_to_files(filter='labs_sample_3years'):
    cfg = Configuration()
    db = DB()
    work_folder = cfg.work_path
    code_folder = cfg.code_folder
    out_folder = os.path.join(work_folder, 'FinalSignals')

    at_map = pd.read_csv(os.path.join(code_folder, 'anthem_pre2d_signal_map.csv'), sep='\t')
    lab_chart_cond = (at_map['source'] == filter)
    # lab_chart_cond = ((kp_map['source'] == filter) & (kp_map['signal'] == 'Resp_Rate'))
    at_map_numeric = at_map[(at_map['type'] == 'numeric') & lab_chart_cond]
    print(at_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    numeric_to_files(db, at_map_numeric, unit_mult, id2nr, out_folder)


def demographic_to_sql():
    sigs = ['GENDER', 'BDATE', 'STATE']
    cfg = Configuration()
    db_det = DB()
    work_folder = cfg.work_path
    code_folder = cfg.code_folder
    out_folder = os.path.join(work_folder, 'FinalSignals')
    id2nr = get_id2nr_map()
    id_list = id2nr.index.tolist()
    sigs_df_dict = {x: pd.DataFrame() for x in sigs}
    demo_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_eligibility_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    sql_query = "SELECT distinct membernumberhci, birthdate as BDATE, gendercode as GENDER, state FROM " + demo_table
    print(sql_query)
    cnt = 0
    for demo_df in pd.read_sql_query(sql_query, db_engine, chunksize=10000000):
        print(' Read chank '+str(cnt))
        demo_df = demo_df[demo_df['membernumberhci'].isin(id_list)]
        print(' active pids ' + str(demo_df.shape[0]))
        demo_df['medialid'] = demo_df['membernumberhci'].astype(str).map(id2nr)
        demo_df.drop('membernumberhci', inplace=True, axis=1)
        demo_df.set_index('medialid', inplace=True)
        demo_df = demo_df.stack().to_frame().reset_index()
        demo_df.rename(columns={'level_1': 'sig', 0: 'value'}, inplace=True)
        demo_df['sig'] = demo_df['sig'].str.upper()
        for sig in sigs:
            sig_filter = demo_df[demo_df['sig'] == sig]
            sigs_df_dict[sig] = sigs_df_dict[sig].append(sig_filter)
        cnt += 1
        print(' total pids ' + str(sigs_df_dict['GENDER'].shape))
    cols = ['medialid', 'sig', 'value']
    for sig in sigs:
        sig_df = sigs_df_dict[sig]
        sig_df = sig_df[sig_df['value'].str.strip() != '']
        sig_df.drop_duplicates(cols, inplace=True)
        sig_df.sort_values(by=['medialid'], inplace=True)
        write_tsv(sig_df[cols], out_folder, sig, mode='w')
    sig = 'BYEAR'
    sig_df = sigs_df_dict['BDATE']
    sig_df['sig'] = sig
    sig_df['value'] = sig_df['value'].str[0:4]
    sig_df.drop_duplicates(cols, inplace=True)
    sig_df.sort_values(by=['medialid'], inplace=True)
    write_tsv(sig_df[cols], out_folder, sig, mode='w')


def drugs_to_files():
    sig = 'Drug'
    cfg = Configuration()
    db_det = DB()
    work_folder = cfg.work_path
    code_folder = cfg.code_folder
    out_folder = os.path.join(work_folder, 'FinalSignals')

    drug_table = 'pk_us_516_o_kj9fj1q4w4nf_anthem_datascience_poc0_pharmacy_sample_3years'
    lab_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_labs_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    id2nr = get_id2nr_map()
    id_list = id2nr.index.tolist()
    unique_ndcs = []
    sql_query = "SELECT membernumberhci, filldate, ndc, dayssupply, quantitydispensed FROM " + drug_table + " WHERE ndc != 'null'"
    cnt=0
    start_time = datetime.now()
    print('starting...')
    for vals in pd.read_sql_query(sql_query, db_engine, chunksize=10000000):
        print('   read chuck ' + str(cnt))
        vals = vals[vals['membernumberhci'].isin(id_list)]
        if vals.empty:
            continue
        vals['medialid'] = vals['membernumberhci'].astype(str).map(id2nr)
        vals['ndc'] = 'ICD10_CODE:' + vals['ndc'].str.strip()
        vals['signal'] = sig
        vals['ndc'] = 'NDC:' + vals['ndc'].astype(str)
        unique_ndcs = list(set(unique_ndcs + vals['ndc'].unique().tolist()))
        print('unique ndcs = ' + str(len(unique_ndcs)))
        sig_file = sig + str(cnt)
        cnt += 1
        cols = ['medialid', 'signal', 'filldate', 'ndc', 'dayssupply', 'quantitydispensed']
        vals = vals[vals['ndc'].str.strip() != '']
        vals.sort_values(by=['medialid', 'filldate'], inplace=True)
        write_tsv(vals[cols], out_folder, sig_file, mode='w')
        curr_tm = datetime.now()
        print('%s :: Done processing %d line. Saved to file %s Elapsed %d minutes'%(curr_tm, vals.shape[0], sig_file,int((curr_tm - start_time).total_seconds()/60)))

    print('Gnerating dict')
    dict_path = os.path.join(work_folder, 'rep_configs', 'dicts')
    dc_start = 1000
    dict_file = 'dict.drugs'
    dict_df = pd.DataFrame(unique_ndcs)
    dict_df = dict_df.assign(defid=range(dc_start, dc_start + dict_df.shape[0]))
    dict_df['def'] = 'DEF'
    write_tsv(dict_df[['def', 'defid', 0]], dict_path, dict_file)
    first_line = 'SECTION\t' + sig + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))


def identify_icd(x):
    if x.startswith('CPT_CODE'):
        return x
    elif x[0].isdigit():
        return 'ICD9_CODE:' + x.strip()
    else:
        return 'ICD10_CODE:' + x.strip()


def diag_to_files():
    sig = 'DIAGNOSIS'
    cfg = Configuration()
    db_det = DB()
    work_folder = cfg.work_path
    code_folder = cfg.code_folder
    out_folder = os.path.join(work_folder, 'FinalSignals')

    diag_table = 'pk_us_522_o_kj9fj1q4w4nf_anthem_datascience_poc0_medical_detail_diabetes_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    id2nr = get_id2nr_map()
    id_list = id2nr.index.tolist()
    #diag_cols = ['diag1line', 'diag2line', 'diag3line', 'diag4line', 'diag5line', 'diag6line', 'diag7line', 'diag8line']
    sql_query = "SELECT membernumberhci, servicestring, cptcode, diag1line,diag2line,diag3line,diag4line, diag5line,diag6line,diag7line,diag8line FROM " + diag_table
    cnt=0
    unique_diags = []
    start_time = datetime.now()
    print('starting...')
    for vals in pd.read_sql_query(sql_query, db_engine, chunksize=10000000):
        print(' Read chank ' + str(cnt))
        vals = vals[vals['membernumberhci'].isin(id_list)]
        print(' active pids ' + str(vals.shape[0]))
        vals['medialid'] = vals['membernumberhci'].astype(str).map(id2nr)
        vals.drop('membernumberhci', inplace=True, axis=1)
        vals.set_index(['medialid', 'servicestring'], inplace=True)
        vals['cptcode'] = 'CPT_CODE:' + vals['cptcode']
        vals = vals.stack().to_frame().reset_index()
        vals = vals[vals[0].str.strip() != '']
        vals['code'] = vals[0].apply(lambda x: identify_icd(x))
        cnt += 1
        print('unique diags = ' + str(len(unique_diags)))
        vals['signal'] = sig
        sig_file = sig + str(cnt)
        cols = ['medialid', 'signal', 'servicestring', 'code']
        vals.drop_duplicates(cols, inplace=True)
        vals = vals[vals[0].str.strip() != '']
        vals.sort_values(by=['medialid', 'servicestring'], inplace=True)
        write_tsv(vals[cols], out_folder, sig_file, mode='w')
        curr_tm = datetime.now()
        print('%s :: Done processing %d line. Saved to file %s Elapsed %d minutes' % (
        curr_tm, vals.shape[0], sig_file, int((curr_tm - start_time).total_seconds() / 60)))


def train_signal():
    cfg = Configuration()
    create_train_signal(cfg)


def start_end_date():
    cfg = Configuration()
    db_det = DB()
    work_folder = cfg.work_path
    code_folder = cfg.code_folder
    out_folder = os.path.join(work_folder, 'FinalSignals')

    demo_table = 'pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_eligibility_sample_3years'
    db_engine = create_postgres_engine_generic(db_det.host, db_det.port, db_det.dbname, db_det.user, db_det.password)
    id2nr = get_id2nr_map()
    id_list = id2nr.index.tolist()
    #join_m = "(select distinct labs.membernumberhci from pk_us_496_o_kj9fj1q4w4nf_anthem_datascience_poc0_labs_sample_3years labs join map_signals ms on labs.testname=ms.testname where ms.targetname in ('HbA1C', 'Glucose'))"
    sql_query = "SELECT membernumberhci, min(effectivedate) as startdate, max(expirationdate) as enddate FROM " + demo_table + " GROUP BY membernumberhci"
    final_df = pd.DataFrame()
    cnt=0
    for vals in pd.read_sql_query(sql_query, db_engine, chunksize=10000000):
        print(' Read chank ' + str(cnt))
        vals = vals[vals['membernumberhci'].isin(id_list)]
        print(' active pids ' + str(vals.shape[0]))
        vals['medialid'] = vals['membernumberhci'].astype(str).map(id2nr)
        vals['startdate'] = vals['startdate'].str.replace('-', '')
        vals['enddate'] = vals['enddate'].str.replace('-', '')
        vals.drop('membernumberhci', inplace=True, axis=1)
        final_df = final_df.append(vals)
        cnt+=1

    sig = 'STARTDATE'
    final_df['sig'] = sig
    final_df.sort_values(['medialid', 'startdate'], inplace=True)
    write_tsv(final_df[['medialid', 'sig', 'startdate']], out_folder, sig, mode='w')
    sig = 'ENDDATE'
    final_df['sig'] = sig
    print(final_df.dtypes)
    final_df['enddate'] = final_df['enddate'].where(final_df['enddate'].astype(str).str[0:4] != '9999', '20171231')
    final_df.sort_values(['medialid', 'enddate'], inplace=True)
    write_tsv(final_df[['medialid', 'sig', 'enddate']], out_folder, sig, mode='w')


if __name__ == '__main__':
    #labs_to_files()
    #demographic_to_sql()
    #drugs_to_files()
    #diag_to_files()
    #train_signal()
    start_end_date()
