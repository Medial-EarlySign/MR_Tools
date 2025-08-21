import os, sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from Configuration import Configuration
from db_connect import DB
#sys.path.append(os.path.join('/opt/medial/tools/bin/', 'RepoLoadUtils','common'))
sys.path.append('/opt/medial_sign/med_scripts/ETL/common')
from utils import write_tsv, add_fisrt_line, replace_spaces, code_desc_to_dict_df, read_tsv
from unit_converts import unit_convert
from stage_to_signals import remove_errors, handel_special_cases
from train_signal import create_train_signal


def id2nr_map_flu(s):
    return s[5:]

ADMISSION_ENC_TYPES = ['ADMISSION', 'ED ONLY', 'ED TO IP', 'IP ONLY', 'ANESTHESIA']

def demographic_to_load(out_folder, db_con, id2nr_map):
    sigs = ['GENDER', 'BDATE', 'BYEAR', 'DEATH', 'RACE', 'ETNICITY', 'INSURENCE', 'HAS_ACTIVE_MEMBERSHIP']
    sigs_df_dict = {x: pd.DataFrame() for x in sigs}
    demo_table = '[flu].[DEMOGRAPHICS]'
    sql_query = 'SELECT PT_ID, PT_BIRTH_DT as BDATE, PT_DEATH_DT as DEATH, PT_SEX as GENDER, PT_RACE_1 as RACE, PT_ETHNICITY as ETNICITY, PT_INS_TYPE_NM as INSURENCE, PT_GHS_PCP_YN as HAS_ACTIVE_MEMBERSHIP  FROM '+ demo_table
    cnt = 0
    for demo_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('read chunk '+ str(cnt))
        demo_df['medialid'] = demo_df['PT_ID'].map(id2nr_map)
        demo_df['medialid'] = demo_df['medialid'].astype(int)
        demo_df.drop('PT_ID', inplace=True, axis=1)
        demo_df['BYEAR'] = demo_df['BDATE'].astype(str).str[0:4]
        demo_df.set_index('medialid', inplace=True)
        demo_df = demo_df.stack().to_frame().reset_index()
        demo_df.rename(columns={'level_1': 'sig', 0: 'value'}, inplace=True)
        for sig in sigs:
            sig_df = demo_df[demo_df['sig'] == sig]
            sigs_df_dict[sig] = sigs_df_dict[sig].append(sig_df)
        cnt += 1
        print(' total pids ' +str(sigs_df_dict["GENDER"].shape[0]))
    cols = ['medialid', 'sig', 'value']
    for sig in sigs:
        print('saving ' + sig)
        sig_df = sigs_df_dict[sig]
        if sig in ['RACE', 'ETNICITY', 'INSURENCE']:
            sig_df['value'] = replace_spaces(sig_df['value'].str.upper())
        sig_df.sort_values('medialid', inplace=True)
        write_tsv(sig_df[cols], out_folder, sig, mode='w')


def get_map(code_folder, typ, filter):
    gei_map = pd.read_csv(os.path.join(code_folder, 'geisinger_signal_map.csv'), sep='\t') #, escapechar='#')
    lab_chart_cond = (gei_map['source'] == filter)
    gei_map_type = gei_map[(gei_map['type'] == typ) & lab_chart_cond]
    #print(gei_map_type)
    return gei_map_type

def fix_Temperature(vals_df):
    numeric_ser = pd.to_numeric(vals_df['value'], errors='coerce')
    vals_df.loc[(numeric_ser >=32) & (numeric_ser <=43), 'unit'] = '[degC]'


def handle_bp(vals_df):
    #grp = vals_df.groupby('medialid', 'date1')
    df_d = vals_df[vals_df['code'] == 'BP Diastolic']
    df_s = vals_df[vals_df['code'] == 'BP Systolic']
    df_bp = pd.merge(df_s, df_d, on=['medialid', 'date1', 'unit', 'source', 'signal'])
    df_bp.loc[:,'code'] = 'BP'
    df_bp.rename(columns={'value_x': 'value', 'value_y': 'value2'}, inplace=True)
    print(df_bp)
    return df_bp

def gei_numeric_to_files(signal_map, unit_mult, id2nr_map, out_folder, table, db_con):
    error_file = 'errors.txt'
    sql_table = 'flu.' + table
    sig_suf = ''
    unit_mult['unit'] = unit_mult['unit'].str.lower().str.strip()
    unit_mult.drop_duplicates(inplace=True)
    unit_mult.loc[unit_mult['rndf'].isnull(), 'rndf'] = unit_mult[unit_mult['rndf'].isnull()]['rnd']
    for sig, sig_grp in signal_map.groupby('signal'):
        if os.path.exists(os.path.join(out_folder, sig+sig_suf+'1')) | \
                os.path.exists(os.path.join(out_folder, sig+sig_suf)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        if table == 'VITALS':
            #sql_query = "SELECT PT_ID as orig_pid, VTL_TYPE as code, VTL_VALUE as value, VTL_DTTM as date1, VTL_VALUE_UOM as unit, '" + table +"' as source FROM " + sql_table + " WHERE VTL_TYPE in ('" + "','".join(codes_list) + "') AND VTL_SETTING NOT IN ('"+ "','".join(ADMISSION_ENC_TYPES) +"')"
            sql_query = "SELECT PT_ID as orig_pid, VTL_TYPE as code, VTL_VALUE as value, VTL_DTTM as date1, VTL_VALUE_UOM as unit, '" + table +"' as source FROM " + sql_table + " WHERE VTL_TYPE in ('" + "','".join(codes_list) + "')"
        else:
            sql_query = "SELECT PT_ID as orig_pid, LAB_COMP_CD as code, LAB_RES_VAL_TXT as value, LAB_TKN_DTTM as date1, LAB_RES_UNIT as unit,'" + table + "' as source FROM " + sql_table + " WHERE LAB_COMP_CD in ('" + "','".join(codes_list) + "')"
        print(sql_query)
        cnt=1
        for vals in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
            #vals = handel_special_cases(stage_def, sig, vals)
            if vals.empty:
                continue
            vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map).astype(int)
            print('   read chuck ' + str(cnt))
            vals['signal'] = sig
            cond = vals['medialid'].isnull()
            vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')
            if sig == 'BP':
                vals = handle_bp(vals)
                
            cond = vals['date1'].isnull()
            vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')
            vals['date1'] = vals['date1'].dt.date

            cond = pd.DatetimeIndex(vals['date1']).year < 1900
            vals, all_errors = remove_errors(vals, all_errors, cond, 'before1900')
            if sig == 'Temperature':
                fix_Temperature(vals)
            
                
            if 'value2' in vals.columns:
                vals.drop_duplicates(subset=['medialid', 'date1', 'value', 'value2'], inplace=True)
            else:
                vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
            
            vals, errs = unit_convert(sig, vals, unit_mult)
            all_errors = all_errors.append(errs, sort=False)
            vals['source'] = vals['source'] + '_' + vals['code'].astype(str)
            vals['source'] = vals['source'].str.replace(' ', '_')
            #vals['date2'] = vals['date2'].where(vals['date2'].notnull(), vals['date1'])
            #vals['date2'] = vals['date2'].astype('datetime64[ns]')
            vals['unit'] = vals['unit'].where(vals['unit'].notnull(), 'None')
            vals.sort_values(by=['medialid', 'date1'], inplace=True)
            if 'value2' in vals.columns:
                cols = ['medialid', 'signal', 'date1', 'value', 'value2', 'unit', 'source']
            else:
                cols = ['medialid', 'signal', 'date1', 'value', 'unit', 'source']
            #if os.path.exists(os.path.join(out_folder, sig)):
            #    os.remove(os.path.join(out_folder, sig))
            sig_file = sig + sig_suf + str(cnt)
            cnt+=1
            write_tsv(vals[cols], out_folder, sig_file)
        if all_errors.shape[0] > 0:
            add_cols = [x for x in all_errors.columns if x in ['reason', 'orig_val', 'description']]
            write_tsv(all_errors[cols+add_cols], out_folder, error_file)
            


def gei_categories_to_files(signal_map, id2nr_map, out_folder, table, db_con):
    error_file = 'errors.txt'
    sql_table = 'flu.' + table
    sig_suf = ''

    for sig, sig_grp in signal_map.groupby('signal'):
        sig_file = sig + sig_suf
        if os.path.exists(os.path.join(out_folder, sig_file)):
            print('Signal files for ' + sig + ' already exists')
            continue
        all_errors = pd.DataFrame()
        codes_list = [str(x) for x in sig_grp['code'].values]
        print(sig, codes_list)
        sql_query = "SELECT PT_ID as orig_pid, LAB_COMP_CD as code, LAB_RES_VAL_TXT as value, LAB_TKN_DTTM as date1,'" + table +"' as source FROM " + sql_table + " WHERE LAB_COMP_CD in ('" + "','".join(codes_list) + "')"
        print(sql_query)
        vals = pd.read_sql(sql_query, db_con)
        vals['medialid'] = vals['orig_pid'].astype(str).map(id2nr_map).astype(int)
        vals.drop_duplicates(subset=['medialid', 'date1', 'value'], inplace=True)
        vals['signal'] = sig
        vals['date1'] = vals['date1'].dt.date
        vals['value'] = vals['value'].replace('nan', np.NaN)
        vals['value'].fillna('EMPTY_FIELD', inplace=True)
        cond = vals['medialid'].isnull()
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_id')
        cond = vals['date1'].isnull()
        vals, all_errors = remove_errors(vals, all_errors, cond, 'no_date')

        vals['value'] = replace_spaces(vals['value'].str.strip().str.upper())

        vals['source'] = vals['source'] + '_' + vals['code'].astype(str)
        vals['source'] = replace_spaces(vals['source'])
        vals.sort_values(by=['medialid', 'date1'], inplace=True)
        cols = ['medialid', 'signal', 'date1', 'value', 'source']
        write_tsv(vals[cols], out_folder, sig_file, mode='w')
        if all_errors.shape[0] > 0:
            #write_tsv(all_errors[cols+['reason', 'description']], out_folder, error_file)
            write_tsv(all_errors[cols+['reason']], out_folder, error_file)


def vitals_to_load(code_folder, out_folder, db_con, id2nr_map):
    vit_map = get_map(code_folder, 'numeric', 'VITALS')
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    gei_numeric_to_files(vit_map, unit_mult, id2nr_map, out_folder, 'VITALS', db_con)

def labs_to_load(code_folder, out_folder, db_con, id2nr_map):
    cat_lab_map = get_map(code_folder, 'category', 'LAB_RESULTS')
    gei_categories_to_files(cat_lab_map, id2nr_map, out_folder,'LAB_RESULTS', db_con)
    num_lab_map = get_map(code_folder, 'numeric', 'LAB_RESULTS')
    #num_lab_map = num_lab_map[num_lab_map['signal'].str.contains('Basophils')]
    #print(num_lab_map)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    gei_numeric_to_files(num_lab_map, unit_mult, id2nr_map, out_folder,'LAB_RESULTS', db_con)
    

def diagnosis_to_load(out_folder, db_con, id2nr_map):
    sig = 'DIAGNOSIS'
    sql_query1 = "SELECT dx.PT_ID as orig_pid, e.ENC_DT as date, DX_CD as code, DX_PRIMARY_YN, CODE_SYSTEM FROM flu.ENCOUNTERS_DX dx JOIN flu.ENCOUNTERS e ON dx.ENC_ID = e.ENC_ID"
    sql_query2 = "SELECT PT_ID as orig_pid, PROB_ENTRY_DT as date, PROB_DX_CD as code , 1 as DX_PRIMARY_YN, CODE_SYSTEM FROM flu.PROBLEM_LIST"
    cnt=1
    for sql_query in [sql_query1, sql_query2]:
        print(sql_query)
        for diag_df in pd.read_sql(sql_query, db_con, chunksize=10000000):
            print('   read chuck ' + str(cnt))
            diag_df['medialid'] = diag_df['orig_pid'].map(id2nr_map)
            diag_df['medialid'] = diag_df['medialid'].astype(int)
            diag_df['signal'] = sig
            diag_df['code'] = diag_df['CODE_SYSTEM'].str.replace('CM', '_CODE') + ':' + replace_spaces(diag_df['code'].str.replace('.', ''))
            diag_df.sort_values(['medialid', 'date'], inplace=True)
            sig_file = sig + str(cnt)
            cnt+=1
            cols = ['medialid', 'signal', 'date', 'code', 'DX_PRIMARY_YN']
            write_tsv(diag_df[cols], out_folder, sig_file, mode='w')
    
def encounter_to_load(out_folder, db_con, id2nr_map, sig, sql_query, dates, cols):
    print(sig)
    print(sql_query)
    cnt=1
    for adm_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('   read chuck ' + str(cnt))
        adm_df['medialid'] = adm_df['PT_ID'].map(id2nr_map)
        adm_df['medialid'] = adm_df['medialid'].astype(int)
        adm_df['signal'] = sig
        adm_df['SPEC'] = replace_spaces(adm_df['SPEC']).fillna('SPEC:UNKNOWN')
        adm_df['ENC_RSN'] = replace_spaces(adm_df['ENC_RSN']).fillna('RSN:UNKNOWN')
        adm_df['ENC_TYPE'] = replace_spaces(adm_df['ENC_TYPE']).fillna('TYPE:UNKNOWN')
        for d in dates:
            if d == 'ENC_DT':
                continue
            print('Converting date field ' + d)
            adm_df[d] = adm_df[d].dt.date
        if len(dates) > 1:
            adm_df[dates[1]] = adm_df[dates[1]].where(adm_df[dates[1]].notnull(), adm_df[dates[0]])
        adm_df.sort_values(['medialid', dates[0]], inplace=True)
        sig_file = sig + str(cnt)
        cnt+=1
        write_tsv(adm_df[cols], out_folder, sig_file, mode='w')

def admission_to_load(out_folder, db_con, id2nr_map):
    sig = 'ADMISSION'
    query = "SELECT PT_ID, ENC_TYPE, ENC_RSN, ENC_ADM_DTTM, ENC_DIS_DTTM, CASE WHEN [ENC_PROV_SPEC] IS null THEN [ENC_DEP_SPEC] ELSE [ENC_PROV_SPEC] END as SPEC FROM flu.ENCOUNTERS WHERE ENC_ADM_DTTM is not null"
    adm_dates = ['ENC_ADM_DTTM', 'ENC_DIS_DTTM']
    adm_cols = ['medialid', 'signal'] + adm_dates + ['SPEC', 'ENC_TYPE', 'ENC_RSN']
    encounter_to_load(out_folder, db_con, id2nr_map, sig, query, adm_dates, adm_cols)
    

def visit_to_load(out_folder, db_con, id2nr_map):
    sig = 'VISIT'
    enc_types = ['OUTPATIENT', 'OTHER APPT', 'ADMISSION', 'TELEMED']
    query = "SELECT PT_ID, ENC_TYPE, ENC_RSN, ENC_DT, CASE WHEN [ENC_PROV_SPEC] IS null THEN [ENC_DEP_SPEC] ELSE [ENC_PROV_SPEC] END as SPEC FROM flu.ENCOUNTERS WHERE ENC_ADM_DTTM is null AND ENC_TYPE in ('" + "','".join(enc_types) + "')"
    vis_dates = ['ENC_DT']
    vis_cols = ['medialid', 'signal'] + vis_dates + ['SPEC', 'ENC_TYPE', 'ENC_RSN']
    encounter_to_load(out_folder, db_con, id2nr_map, sig, query, vis_dates, vis_cols)
    

def med_to_load(out_folder, db_con, id2nr_map):
    sig1 = 'Drug'
    sig2 = 'Drug_detailed'
    sql_query = "SELECT PT_ID, MED_START_DTTM ,MED_END_DTTM, MED_ID FROM [flu].[MEDICATION_ORDERS] WHERE MED_ORD_SETTING = 'OUTPATIENT' AND MED_START_DTTM IS NOT null"
    #select_sql = "SELECT PT_ID, MED_START_DTTM, MED_END_DTTM, MED_ID, DX_CD, CODE_SYSTEM, MED_STRENGTH ,MED_FORM, MED_SIG_TTL_DAY "
    #from_sql = "FROM flu.MEDICATION_ORDERS m JOIN flu.ORDERS_DX o ON m.MED_ORD_ID =o.ORD_ID "
    #where_sql = "WHERE MED_ORD_SETTING = 'OUTPATIENT' AND [MED_END_DTTM] is not NULL" 
    #sql_query = select_sql + from_sql + where_sql
    cnt=1
    print(sql_query)
    cols1 = ['medialid', 'signal', 'MED_START_DTTM', 'MED_ID', 'days']
    cols2 = ['medialid', 'signal', 'MED_START_DTTM', 'MED_ID', 'days', 'diag', 'MED_SIG_TTL_DAY', 'MED_STRENGTH', 'MED_FORM']
    for drug_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('   read chuck ' + str(cnt))
        drug_df['medialid'] = drug_df['PT_ID'].map(id2nr_map)
        drug_df['medialid'] = drug_df['medialid'].astype(int)

        drug_df['days'] = pd.to_datetime(drug_df['MED_END_DTTM'], errors='coerce').dt.date - drug_df['MED_START_DTTM'].dt.date
        drug_df['days'] = drug_df['days'].dt.days
        drug_df['days'].fillna(1, inplace=True)
        print('SORTING')
        drug_df.sort_values(by=['medialid',  'MED_START_DTTM'], inplace=True)
        '''
        drug_df['MED_SIG_TTL_DAY'].fillna(999,inplace=True)
        
        drug_df['diag'] = drug_df['CODE_SYSTEM'].str.replace('CM', '_CODE') + ':' + replace_spaces(drug_df['DX_CD'].str.replace('.', ''))
        drug_df['MED_STRENGTH'] = replace_spaces(drug_df['MED_STRENGTH'])
        drug_df.loc[drug_df['MED_STRENGTH'].isnull(), 'MED_STRENGTH'] = 'DOSE:UNKNOWN'
        
        drug_df['MED_FORM'] = replace_spaces(drug_df['MED_FORM'])
        drug_df.loc[drug_df['MED_FORM'].isnull(), 'MED_FORM'] = 'FORM:UNKNOWN'
        '''
        
        drug_df['signal'] = sig1
        sig_file1 = sig1 + str(cnt)
        print('Saving file ' + sig_file1)
        write_tsv(drug_df[cols1], out_folder, sig_file1, mode='w')
        '''
        drug_df['signal'] = sig2
        sig_file2 = sig2 + str(cnt)
        print('Saving file ' + sig_file2)
        write_tsv(drug_df[cols2], out_folder, sig_file2, mode='w')
        '''
        cnt+=1

def smoke_to_load(out_folder, db_con, id2nr_map):
    sig = 'Smoking_Status'
    sql_query = "SELECT PT_ID, SOC_HX_DT, SOC_HX_SMOKE_STTS FROM [flu].[SOCIAL_HISTORY]"
    cnt=1
    print(sql_query)
    for smk_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('   read chuck ' + str(cnt))
        smk_df['medialid'] = smk_df['PT_ID'].map(id2nr_map)
        smk_df['medialid'] = smk_df['medialid'].astype(int)
        smk_df['SOC_HX_SMOKE_STTS'] = replace_spaces(smk_df['SOC_HX_SMOKE_STTS'])
        smk_df['signal'] = sig
        smk_df.sort_values(['medialid', 'SOC_HX_DT'], inplace=True)
        sig_file = sig + str(cnt)
        cnt+=1
        cols = ['medialid', 'signal', 'SOC_HX_DT', 'SOC_HX_SMOKE_STTS']
        write_tsv(smk_df[cols], out_folder, sig_file, mode='w')


def vacc_to_load(out_folder, db_con, id2nr_map):
    sig = 'Vaccination'
    sql_query = "SELECT PT_ID, IMM_DT, IMM_NM, IMM_STATUS from flu.IMMUNIZATION_HISTORY WHERE IMM_STATUS='GIVEN' AND IMM_DT IS NOT null"
    cnt=1
    print(sql_query)
    for vcc_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('   read chuck ' + str(cnt))
        vcc_df['medialid'] = vcc_df['PT_ID'].map(id2nr_map)
        vcc_df['medialid'] = vcc_df['medialid'].astype(int)
        vcc_df['signal'] = sig
        vcc_df['IMM_NM'] = replace_spaces(vcc_df['IMM_NM'])
        vcc_df.sort_values(['medialid', 'IMM_DT'], inplace=True)
        sig_file = sig + str(cnt)
        cnt+=1
        cols = ['medialid', 'signal', 'IMM_DT', 'IMM_NM']
        write_tsv(vcc_df[cols], out_folder, sig_file, mode='w')


def add_reason_to_load(out_folder, db_con, id2nr_map):
    sig = 'Reason'
    sql_query = 'SELECT PT_ID, ENC_DT, e.ENC_RSN as rsn_prim, a.ENC_RSN rsn_add FROM [flu].[ENCOUNTERS] e JOIN [flu].[ENC_RSN_ADDITIONAL] a ON e.ENC_ID = a.ENC_ID WHERE e.ENC_RSN IS NOT null'
    cnt=1
    print(sql_query)
    for res_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        all_ers_df = pd.DataFrame()
        prim_res_df = res_df[['PT_ID', 'ENC_DT', 'rsn_prim']].drop_duplicates()
        sec_res_df = res_df[['PT_ID', 'ENC_DT', 'rsn_add']].drop_duplicates()
        prim_res_df.rename(columns={'rsn_prim': 'rsn'}, inplace=True)
        sec_res_df.rename(columns={'rsn_add': 'rsn'}, inplace=True)
        all_ers_df = all_ers_df.append(prim_res_df, sort=False)
        all_ers_df = all_ers_df.append(sec_res_df, sort=False)
        all_ers_df['medialid'] = all_ers_df['PT_ID'].map(id2nr_map)
        all_ers_df['medialid'] = all_ers_df['medialid'].astype(int)
        all_ers_df['signal'] = sig
        all_ers_df['rsn'] = replace_spaces(all_ers_df['rsn'].str.strip())
        all_ers_df.sort_values(['medialid', 'ENC_DT'], inplace=True)
        sig_file = sig + str(cnt)
        cnt+=1
        cols = ['medialid', 'signal', 'ENC_DT', 'rsn']
        write_tsv(all_ers_df[cols], out_folder, sig_file, mode='w')


def membership_to_load(out_folder, db_con, id2nr_map):
    sig = 'MEMBERSHIP'
    split_days = 2*365
    sql_query = "SELECT PT_ID,ENC_DT FROM flu.ENCOUNTERS ORDER BY ENC_ID"
    cnt=1
    print(sql_query)
    all_mem_df = pd.DataFrame()
    for mem_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        mem_df['real_date'] = pd.to_datetime(mem_df['ENC_DT'], format='%Y-%m-%d')
        all_mem_df = all_mem_df.append(mem_df)
        print(cnt, all_mem_df.shape[0])
    all_mem_df.sort_values(by=['PT_ID','ENC_DT'], inplace=True)
    all_mem_df['diff'] = (all_mem_df['real_date'] - all_mem_df['real_date'].shift(1)).dt.days
    all_mem_df['split'] = False
    all_mem_df.loc[(all_mem_df['PT_ID'] == all_mem_df['PT_ID'].shift(1)) & (all_mem_df['diff'] > split_days), 'split'] = True
    all_mem_df.loc[all_mem_df['split'] == True, 'real_date'] = all_mem_df.loc[all_mem_df['split'] == True]['real_date'] + timedelta(days=60)
    all_mem_df['cumsum'] = all_mem_df['split'].cumsum()
    grp = all_mem_df.groupby(['PT_ID', 'cumsum'])
    mm = pd.concat([grp['ENC_DT'].min().rename('start_date'), grp['ENC_DT'].max().rename('end_date')], axis = 1)
    mm['end_date'] = mm['end_date'].where(mm['end_date'].astype(str).str[0:4] != '2020', '2099-01-01')
    mm=mm.reset_index()
    mm['medialid'] = mm['PT_ID'].map(id2nr_map).astype(int)
    mm.sort_values(by=['medialid','start_date'], inplace=True)
    mm['signal'] = sig
    cols = ['medialid', 'signal', 'start_date', 'end_date']
    write_tsv(mm[cols], out_folder, sig, mode='w')


def billing_to_load(out_folder, db_con, id2nr_map):
    sig = 'BILLING_CODE'
    sql_query = "SELECT PT_ID, PX_DT, PX_CD, PX_CD_TYPE FROM flu.BILLING_PROCEDURES"
    pref_map = pd.Series({'CPT4': 'CPT_CODE:', 'HCPCS': 'HCPCS_CODE:', 'GHS': 'GHS:', 'ICD9CM': 'ICD9_CODE:', 'ICD10PCS': 'ICD10_CODE:'})
    cnt=1
    print(sql_query)
    print(pref_map)
    for bil_df in pd.read_sql(sql_query, db_con, chunksize=db.default_batch_size):
        print('   read chuck ' + str(cnt))
        bil_df['medialid'] = bil_df['PT_ID'].map(id2nr_map)
        bil_df['medialid'] = bil_df['medialid'].astype(int)
        bil_df['signal'] = sig
        bil_df['code'] = bil_df['PX_CD_TYPE'].map(pref_map) + bil_df['PX_CD']
        bil_df.sort_values(['medialid', 'PX_DT'], inplace=True)
        sig_file = sig + str(cnt)
        cnt+=1
        cols = ['medialid', 'signal', 'PX_DT', 'code']
        write_tsv(bil_df[cols], out_folder, sig_file, mode='w')


def procedures_to_load(out_folder, db_con, id2nr_map):
    sig = 'PROCEDURES'
    sql_query1 = "SELECT PT_ID as orig_pid, PX_ORD_DT as date, PX_ORD_CD as code,  'PX' as source FROM flu.PROCEDURE_ORDERS"
    sql_query2 = "SELECT PT_ID as orig_pid, START_DTTM as date, OR_PROC_ID as code, 'SURGERY' as source FROM flu.SURGERY"
    cnt=1
    for sql_query in [sql_query1, sql_query2]:
        print(sql_query)
        for diag_df in pd.read_sql(sql_query, db_con, chunksize=10000000):
            print('   read chuck ' + str(cnt))
            diag_df['medialid'] = diag_df['orig_pid'].map(id2nr_map)
            diag_df['medialid'] = diag_df['medialid'].astype(int)
            diag_df['signal'] = sig
            diag_df['code'] = diag_df['source'] + ':' + replace_spaces(diag_df['code'].str.replace('.', ''))
            if diag_df.iloc[1]['source'] == 'SURGERY':
                diag_df['date'] = diag_df['date'].dt.date
            diag_df=diag_df[diag_df['date'].notnull()].reset_index(drop=True)
            diag_df.sort_values(['medialid', 'date'], inplace=True)
            sig_file = sig + str(cnt)
            cnt+=1
            cols = ['medialid', 'signal', 'date', 'code']
            write_tsv(diag_df[cols], out_folder, sig_file, mode='w')

def transfers_to_load(out_folder, db_con, id2nr_map):
    sig = 'TRANSFERS'
    sql_query = "SELECT DISTINCT e.PT_ID, e.ENC_ID, ADT_LN, ADT_TYPE,ADT_DTTM,DEP_NM FROM flu.HOSPITAL_ADT a LEFT JOIN flu.ENCOUNTERS e ON e.ENC_ID = a.ENC_ID WHERE [ADT_TYPE]  in ('ADMISSION', 'TRANSFER IN', 'TRANSFER OUT', 'DISCHARGE')"
    print(sql_query)
    df = pd.read_sql(sql_query, db_con)
    #df.drop_duplicates(subset=['ADT_TYPE', 'ENC_ID', 'ADT_DTTM'], inplace=True)

    in_df_ad = df[df['ADT_TYPE'] == 'ADMISSION'].copy()
    in_df_ad.drop_duplicates(subset=['ADT_TYPE', 'ENC_ID', 'ADT_DTTM'], inplace=True)
    in_df = df[df['ADT_TYPE'] =='TRANSFER IN'].copy()
    in_df = in_df.append(in_df_ad)
    in_df.sort_values(['ENC_ID', 'ADT_DTTM', 'ADT_LN'], inplace=True)
    g_in = in_df.groupby('ENC_ID')
    in_df['cumcount'] = g_in.cumcount()

    out_df_ds = df[df['ADT_TYPE'] == 'DISCHARGE'].copy()
    out_df_ds.sort_values(['ENC_ID', 'ADT_DTTM', 'ADT_LN'], inplace=True)
    out_df_ds.drop_duplicates(subset=['ADT_TYPE', 'ENC_ID'], keep='last', inplace=True)
    out_df = df[df['ADT_TYPE'] == 'TRANSFER OUT'].copy()
    out_df = out_df.append(out_df_ds)
    out_df.sort_values(['ENC_ID', 'ADT_DTTM', 'ADT_LN'], inplace=True)
    g_out = out_df.groupby('ENC_ID')
    out_df['cumcount'] = g_out.cumcount()
    trans_df = pd.merge(in_df, out_df, on =['PT_ID' ,'ENC_ID', 'DEP_NM', 'cumcount'], how='left')
    trans_df  = trans_df[trans_df['ADT_DTTM_y'].notnull()]
    trans_df['medialid'] = trans_df['PT_ID'].map(id2nr_map)
    trans_df['medialid'] = trans_df['medialid'].astype(int)
    trans_df['signal'] = sig
    trans_df['ENC_ID'] = trans_df['ENC_ID'].str.replace('MESENC', '')
    trans_df['from_date'] = trans_df['ADT_DTTM_x'].dt.date
    trans_df['to_date'] = trans_df['ADT_DTTM_y'].dt.date
    trans_df['DEP_NM'] = replace_spaces(trans_df['DEP_NM'])
    trans_df.sort_values(['medialid', 'from_date'], inplace=True)
    cols = ['medialid', 'signal', 'from_date', 'to_date', 'DEP_NM', 'ENC_ID']
    trans_df.drop_duplicates(cols, inplace=True)
    write_tsv(trans_df[cols], out_folder, sig, mode='w')

def get_flu_pcr_query(distinct=False):
    serch_texts = ['INFLUENZA B', 'INFLUENZA A', 'INFLUENZA VIRUS A', 'INFLUENZA VIRUS B', 'FLU B PC', 'FLU A PC', 'INFLUENZA ANTIGEN,TYPE ']
    txt_fileds = ['LAB_COMP_NM', 'LAB_LOINC_NM', 'LAB_RES_VAL_TXT']
    where_sql = 'WHERE '
    for st in serch_texts:
        for fl in txt_fileds: 
            where_sql = where_sql+  "upper(" + fl + ") like '%"+ st +"%' OR "
    if distinct:
        select_sql = "SELECT DISTINCT(LAB_RES_VAL_TXT) as value "
    else:
        select_sql = "SELECT PT_ID, LAB_TKN_DTTM as date, LAB_RES_VAL_TXT as value "
    from_sql = "FROM flu.LAB_RESULTS "
    query = select_sql + from_sql + where_sql[:-3]
    return query


def flu_pcr_to_load(out_folder, db_con, id2nr_map):
    sig = 'Flu_lab'
    sql_query = get_flu_pcr_query()
    print(sql_query)
    flu_df = pd.read_sql(sql_query, db_con)
    print('After query: ' + str(flu_df.shape[0]))
    flu_df['medialid'] = flu_df['PT_ID'].map(id2nr_map)
    flu_df['medialid'] = flu_df['medialid'].astype(int)
    flu_df['signal'] = sig
    print('After replace id: ' + str(flu_df.shape[0]))
    flu_df['date'] = flu_df['date'].dt.date
    flu_df['value'] = flu_df['value'].str.replace('"', '').str.replace('&', '_AND_').str.replace('/', '_OR_')
    flu_df['value'] = replace_spaces(flu_df['value'].str.strip().str.upper())
    print('After replace spaces: ' + str(flu_df.shape[0]))
    flu_df.sort_values(['medialid', 'date'], inplace=True)
    cols = ['medialid', 'signal', 'date', 'value']
    print(flu_df[flu_df.duplicated(cols, keep=False)])
    flu_df.drop_duplicates(cols, inplace=True)
    print('After drop_duplicates: ' + str(flu_df.shape[0]))
    write_tsv(flu_df[cols], out_folder, sig, mode='w')
    
    
def tumor_to_load(out_folder, db_con, id2nr_map):
    sig = 'TUMORS'
    sql_query = "SELECT PT_ID, INIT_DX_DT, ICDO_SITE_CD, LATERALITY, ICDO_HISTOLOGY_CD, ICDO_MORPHOLOGY_NM,TUMOR_SIZE, SEER_SUMMARY, AJCC_STG FROM flu.TUMOR_DX"
    tum_df = pd.read_sql(sql_query, db_con)
        
    tum_df['medialid'] = tum_df['PT_ID'].map(id2nr_map)
    tum_df['medialid'] = tum_df['medialid'].astype(int)
    tum_df['ICDO_SITE_CD'] = 'ICDO_CODE:' + tum_df['ICDO_SITE_CD']
    tum_df['ICDO_HISTOLOGY_CD'] = 'ICDO_CODE:' + tum_df['ICDO_HISTOLOGY_CD']
    tum_df['LATERALITY'] = 'LATERALITY:' + replace_spaces(tum_df['LATERALITY'].str.upper())
    tum_df['ICDO_MORPHOLOGY_NM'] = 'MORPHOLOGY:' + replace_spaces(tum_df['ICDO_MORPHOLOGY_NM'].str.upper())
    
    tum_df['SEER_SUMMARY'].fillna('NULL', inplace=True)
    tum_df['AJCC_STG'].fillna('NULL', inplace=True)
    tum_df['stage'] = 'STAGE:' + replace_spaces(tum_df['SEER_SUMMARY'] + '_' + tum_df['AJCC_STG'])
    tum_df['TUMOR_SIZE'].fillna(0, inplace=True)
    tum_df['signal'] = sig
    cols = ['medialid', 'signal', 'INIT_DX_DT', 'ICDO_SITE_CD', 'LATERALITY', 'ICDO_HISTOLOGY_CD', 'ICDO_MORPHOLOGY_NM','TUMOR_SIZE', 'stage']
    tum_df.drop_duplicates(cols, inplace=True)
    tum_df.sort_values(['medialid', 'INIT_DX_DT'], inplace=True)
    write_tsv(tum_df[cols], out_folder, sig, mode='w')
    
    sig = 'LUNG_CANCER_STAGE'
    lung_df = tum_df[tum_df['ICDO_SITE_CD'].str.contains('C34')]
    lung_df['signal'] = sig
    cols = ['medialid', 'signal', 'INIT_DX_DT', 'stage']
    lung_df.drop_duplicates(cols, inplace=True)
    lung_df.sort_values(['medialid', 'INIT_DX_DT'], inplace=True)
    write_tsv(lung_df[cols], out_folder, sig, mode='w')
    
    

def insurance_lob_to_load(out_folder, db_con, id2nr_map):
    sig = 'INSURENCE_LOB'
    sql_query = "SELECT DISTINCT PT_ID,PAYOR_ROLLUP FROM flu.ENCOUNTERS_PAYOR WHERE PAYOR_ROLLUP = 'MEDICAID'"
    aid_df = pd.read_sql(sql_query, db_con)
    sql_query = "SELECT DISTINCT PT_ID,PAYOR_ROLLUP FROM [flu].[ENCOUNTERS_PAYOR] WHERE MOST_RECENT_FLAG = 1"
    lob_df = pd.read_sql(sql_query, db_con)

    lob_df = lob_df[~lob_df['PT_ID'].isin(aid_df['PT_ID'].values)]
    lob_df = lob_df.append(aid_df)
    lob_df.loc[lob_df['PAYOR_ROLLUP'] == 'SELF', 'PAYOR_ROLLUP'] = 'SELF_PAY'

    lob_df['medialid'] = lob_df['PT_ID'].map(id2nr_map)
    lob_df['medialid'] = lob_df['medialid'].astype(int)
    lob_df.drop_duplicates('medialid', inplace=True)
    lob_df.sort_values('medialid', inplace=True)
    lob_df['signal'] = sig
    write_tsv(lob_df[['medialid', 'signal', 'PAYOR_ROLLUP']], out_folder, sig, mode='w')
    
if __name__ == '__main__':
    cfg = Configuration()
    out_folder = os.path.join(cfg.work_path, 'FinalSignals')
    #id2nr_map = get_id2nr_map()
    id2nr_map=id2nr_map_flu
    db = DB()
    db_con = db.get_connect()
    #demographic_to_load(out_folder, db_con, id2nr_map)
    #labs_to_load(cfg.code_folder, out_folder, db_con, id2nr_map)
    #diagnosis_to_load(out_folder, db_con, id2nr_map)
    #admission_to_load(out_folder, db_con, id2nr_map)
    #visit_to_load(out_folder, db_con, id2nr_map)
    #med_to_load(out_folder, db_con, id2nr_map)
    #smoke_to_load(out_folder, db_con, id2nr_map)
    #vacc_to_load(out_folder, db_con, id2nr_map)
    #add_reason_to_load(out_folder, db_con, id2nr_map)
    #membership_to_load(out_folder, db_con, id2nr_map)
    #billing_to_load(out_folder, db_con, id2nr_map)
    #procedures_to_load(out_folder, db_con, id2nr_map)
    #transfers_to_load(out_folder, db_con, id2nr_map)
    #flu_pcr_to_load(out_folder, db_con, id2nr_map)
    #tumor_to_load(out_folder, db_con, id2nr_map)
    #insurance_lob_to_load(out_folder, db_con, id2nr_map)
    #vitals_to_load(cfg.code_folder, out_folder, db_con, id2nr_map)
    create_train_signal(cfg, ['/opt/medial_sign/LOADING_PROCESS/geisinger_load_2021/TRAIN'])
