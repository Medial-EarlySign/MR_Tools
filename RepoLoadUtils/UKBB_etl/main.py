#!/nas1/Work/python-env/python38/bin/python

# to run: UNIX => ./main.py

###
# this file document all code, that was actually run on notebooks earlier,
# so hopefully everything work right ...

import pandas as pd
import numpy as np
import datetime

import os
from os import listdir
import sys

# to import from common
#sys.path.insert(0, '.../common')
#import ...


def get_basic_features():
    
    basic_features = {'GENDER':'31-0.0',
                      'BYEAR':'34-0.0',
                      'DEATH':'40000-0.0'}
    
    for (k, col) in basic_features.items():
        outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/" + k
        if os.path.isfile(outfile)==True:
            os.remove(outfile)
    
    df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", nrows=2, low_memory=False)
    names = df.columns
    
    nrows = 100000
    i = 1
    while i > 0:
        print(i, datetime.datetime.now())
        df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", names = names, skiprows = i, nrows=nrows, low_memory=False)
        
        if len(df) == nrows:
            i = i + nrows
        else:
            i = 0
        
        for (k, col) in basic_features.items():
            data = df[['eid', col]].copy()
            data['signal'] = k
            
            if k=='GENDER':
                # Input format: Male=1,Female=0
                # EarlySign format: Male=1,Female=2
                data[col] = 2 - data[col]
                
            if k=='DEATH':
                data[col] = pd.to_datetime(data[col])
                
            outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/" + k
            data = data[['eid', 'signal', col]].dropna()
            data.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)
            
            if k=='BYEAR':
                outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/BDATE"
                data['signal'] = 'BDATE'
                data[col] = data[col].astype(int).astype(str) + '-01-01'
                data[col] = pd.to_datetime(data[col])
                data.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)
                          
    print('DONE')
    return


def det_TRAIN_sig():
    
    all_pids = pd.read_csv("/nas1/Work/Users/Eitan/ukbb_loading/outputs/BDATE", sep='\t', names = ['pid', 'sig', 'val'])

    all_pids['sig'] = 'TRAIN'
    all_pids['val'] = np.nan

    train_pids = all_pids.pid.sample(frac=0.7)
    all_pids.loc[all_pids.pid.isin(train_pids), 'val'] = 1

    validation_pids = all_pids[all_pids.val.isna()].pid.sample(frac=0.666666)
    all_pids.loc[all_pids.pid.isin(validation_pids), 'val'] = 2

    all_pids.val.fillna(3, inplace=True)

    all_pids.to_csv("/nas1/Work/Users/Eitan/ukbb_loading/outputs/TRAIN", sep='\t', index = False, header = False)
    
    return


def get_cancer_location():
    # generate cancer file

    df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", nrows=2, low_memory=False)
    names = df.columns

    outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/CANCER"

    if os.path.isfile(outfile)==True:
        os.remove(outfile)
    
    nrows = 100000
    
    j = 1
    while j > 0:
        print(j, datetime.datetime.now())

        df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", names = names, skiprows = j, nrows=nrows, low_memory=False)

        # data
        # ----
        # 40005 date of cancer diagnosis
        # 40006 type of cancer ICD-10
        # 40013 type of cancer ICD-9
        
        # when we have ICD9, most of the time we also have ICD10 - anyway I left both
        
        # self reported - currently ignored
        # ---------------------------------
        # 20001 cancer code, self reported
        # 20006 interpolated year of 20000 (cancer first diagnosed)
        # 20012 method of recording time of 20006   
        # 40019 cancer record format
        # 40021 cancer record origin
        
        # when we have self reported ...
            # reported has a unique dict
            # it is likely to have 9 or 10 or both as well, but time might be significantly different ...
            # and, it might be unique ...
            # for counting as many are unique, mapping is required

            # options
            # ignore - current state
            # add as is - simple only after mapping (as is = let the first be the first)
            # add only if no 9/10 (as the date for 9/10 is safer) - more effort
      
        cols_header = ['40005', '40006', '40013']
        cols = [x for x in df.columns if x[0:5] in cols_header]

        cancer = df[['eid'] + cols].copy()
        
        for i in range(15):
            cancer['40006-'+str(i)+'.0'] = cancer['40006-'+str(i)+'.0'].fillna(cancer['40013-'+str(i)+'.0'])
        cancer = cancer[[x for x in cancer.columns if x[0:5] != '40013']]
        
        cancer_flat = pd.DataFrame()
        for i in range(15):
            tmp = cancer[['eid', '40005-'+str(i)+'.0', '40006-'+str(i)+'.0']]
            tmp.columns = ['eid', 'time', 'val']
            tmp = tmp.dropna()
            cancer_flat = pd.concat([cancer_flat, tmp], sort=False)
        
        cancer_flat['signal'] = 'Cancer_Location'
        
        # we drop the followint as they unrecognized in ICD-10 and almost always come with another code on the same day
        ICD_O_codes = ['C420', 'C421', 'C422', 'C423', 'C424']
        cancer_flat = cancer_flat[~cancer_flat.val.isin(ICD_O_codes)]
        
        cancer_flat.loc[cancer_flat.val.isin(['C832', 'C834']), 'val'] = 'C83'
        
        cancer_flat['icd_val'] = cancer_flat.val.map(lambda x: 'ICD10_CODE:' + x if type(x)==str
                                                               else 'ICD9_CODE:' + str(int(x)))
        
          
        if len(cancer) == nrows:
            j = j + nrows
        else:
            j = 0
           
        cancer_flat = cancer_flat[['eid', 'signal', 'time', 'icd_val']].sort_values(by=['eid', 'time'])
        cancer_flat.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)
        
    return
       
       
def get_date_of_attending():

    df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", nrows=2, low_memory=False)
    names = df.columns

    outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/date_of_attending"

    if os.path.isfile(outfile)==False:
        nrows = 100000

        j = 1
        cols_header = ['53-']
        cols = ['eid'] + [x for x in df.columns if x[0:3] in cols_header]
        
        while j > 0:
            print(j, datetime.datetime.now())
            df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", names = names, skiprows = j, nrows=nrows, low_memory=False)
            df = df[cols]
            df.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)
            
            if len(df) == nrows:
                j = j + nrows
            else:
                j = 0
                
    date_of_attending = pd.read_csv("/nas1/Work/users/Eitan/UKBB_loading/outputs/date_of_attending", sep="\t", 
                                    names=['eid', 'visit1', 'visit2', 'visit3', 'visit4'])
        
    return date_of_attending


def get_NMR_Metabolomics():

    # data is in 23400 - 23578
        # They also have "QC flag" over part of the data (we have not requested it) - what does it mean?

    # Date of data is Date of attending assessment centre
        
    nmr = pd.read_csv("/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/metabolic.signals", sep="\t", 
                     names=['ignore1', 'signal_number', 'ignore2', 'ignore3', 'signal_name'])

    nmr = nmr[[x for x in nmr.columns if x[0:2] != "ig"]]
    nmr = nmr.dropna().reset_index(drop=True)
    nmr['signal_name'] = nmr['signal_name'].map(lambda x: x.replace(' ', '_'))

    date_of_attending = get_date_of_attending()

    df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", nrows=2, low_memory=False)
    names = df.columns

    nrows = 100000
    j = 1 
    while j > 0:
        print(j, datetime.datetime.now())
        df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb49235_c.csv", names = names, skiprows = j, nrows=nrows, low_memory=False)
        for i in nmr.index:
            col = nmr.loc[i].signal_number
            data = df[['eid', col]].set_index('eid', drop=True).dropna()
            data = data.rename(columns={col:'val'}).merge(date_of_attending[['eid', 'visit1']].rename(columns={'visit1':'sample_date'}), on='eid')
            col = col[0:6] + '1.0'
            data2 = df[['eid', col]].dropna()
            data2 = data2.rename(columns={col:'val'}).merge(date_of_attending[['eid', 'visit2']].rename(columns={'visit2':'sample_date'}), on='eid')
            data = pd.concat([data, data2], sort=False)

            data['signal'] = 'NMR_' + nmr.loc[i].signal_name
            data = data[['eid', 'signal', 'sample_date', 'val']].sort_values(by=['eid', 'sample_date'])
            
            outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/NMR/NMR_" + nmr.loc[i].signal_name
            data.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)

        if len(df) == nrows:
            j = j + nrows
        else:
            j = 0
    
    return


def fix_HbA1C(data, digits = -1): 

    data['value3a'] = data.value3.map(lambda x: '%' if '%' in str(x)
                                                else 'mol' if 'mol/m' in str(x).lower()
                                                else 'ignore' if '/l' in str(x).lower()
                                                else 'na')

    def mol2percent(x):
        return 0.09148 * x + 2.152

    data = data[data.value3a != 'ignore'].copy()

    data.loc[data.value3a == 'mol', 'value1'] = data.loc[data.value3a == 'mol', 'value1'].map(mol2percent)
    data.loc[data.value1 > 18, 'value1'] = data.loc[data.value1 > 18, 'value1'].map(mol2percent)
   
    if digits != -1:
        data.value1 = data.value1.round(digits)
    
    return data


def fix_signal_units(data, bar = 10, factor = 1, digits = -1):
    if factor <= 1:
        data.loc[data.value1 > bar, 'value1'] *= factor
    else:
        data.loc[data.value1 < bar, 'value1'] *= factor
    
    if digits != -1:
        data.value1 = data.value1.round(digits)
    
    return data


def data_arrange(tmp, sig):
      
    # if value1 has text, then use value2 instead
    text_to_remove = ['OPR001', 'OPR002', 'OPR003', 'OPR004']
    tmp1 = tmp[tmp.value1.isin(text_to_remove)].copy()
    tmp2 = tmp[~tmp.value1.isin(text_to_remove)].copy()
    tmp1['value1'] = tmp1['value2']
    tmp1['value2'] = np.nan 
    tmp = pd.concat([tmp1, tmp2], sort=False)
    
    # rarely value1 is missing but value2 exists
    tmp1 = tmp[tmp.value1.isna()].copy()
    tmp2 = tmp[~tmp.value1.isna()].copy()
    tmp1['value1'] = tmp1['value2']
    tmp1['value2'] = np.nan
    tmp = pd.concat([tmp1, tmp2], sort=False)
    
    # rarely no numeric value
    tmp = tmp.dropna(subset=['value1'])
    tmp = tmp[pd.to_numeric(tmp.value1, errors='coerce').notnull()]
    tmp.value1 = tmp.value1.astype(float)
    tmp = tmp[tmp.value1 > 0]
        
    # some signals have mixed unit, e.g, g/L and g/dL, and furthermore, unit is not always given and not always right
    # looking on thin problematix signals, plus comparing median and mean, we need the following fixes
        
    if sig == 'HbA1C':
        tmp = fix_HbA1C(tmp, digits = 1)
        
    if sig == 'Hemoglobin':
        tmp = fix_signal_units(tmp, bar = 25, factor = 0.1, digits = 1)
        
    if sig == 'MCHC-M':
        tmp = fix_signal_units(tmp, bar = 100, factor = 10, digits = 1)
        
    if sig =='Uric_Acid':
        tmp = fix_signal_units(tmp, bar = 1, factor = 0.001, digits = 3)
        
    return tmp.sort_values(by=['eid', 'event_dt'])



# blood pressure

def bp(gp):
    outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_MES/Diastolic_BP_reading'
    if os.path.isfile(outfile)==True:
        return
    bp = gp[gp.read_2=='246..'].copy()
    Diastolic = gp[gp.read_2=='246A.'].copy()
    Systolic = gp[gp.read_2=='2469.'].copy()

    bp = bp.dropna(subset=['value1', 'value2'])

    tmp = bp.copy()
    tmp['value1'] = pd.to_numeric(tmp.value1, errors='coerce')
    tmp['value2'] = pd.to_numeric(tmp.value2, errors='coerce')
    tmp['Diastolic'] = tmp.apply(lambda r: min(r.value1, r.value2), axis=1)
    tmp['Systolic'] = tmp.apply(lambda r: max(r.value1, r.value2), axis=1)
    tmp.drop(columns=['value1', 'value2'], inplace=True)

    Diastolic = pd.concat([tmp.rename(columns={'Diastolic':'value1'}), Diastolic], sort=False)
    Diastolic = Diastolic.dropna(subset=['value1'])
    Diastolic.value1 = Diastolic.value1.astype(float)
    Diastolic = Diastolic.sort_values(by=['eid', 'event_dt'])

    Systolic = pd.concat([tmp.rename(columns={'Systolic':'value1'}), Systolic], sort=False)
    Systolic = Systolic.dropna(subset=['value1'])
    Systolic.value1 = Systolic.value1.astype(float)
    Systolic = Systolic.sort_values(by=['eid', 'event_dt'])

    sig = "Diastolic_BP_reading"
    Diastolic['signal'] = sig

    if len(Diastolic) > 0:
        outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_MES/' + sig
        Diastolic[['eid', 'signal', 'event_dt', 'value1']].to_csv(outfile, sep='\t', index = False, header = False)

    sig = "Systolic_BP_reading"
    Systolic['signal'] = sig

    if len(Systolic) > 0:
        outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_MES/' + sig
        Systolic[['eid', 'signal', 'event_dt', 'value1']].to_csv(outfile, sep='\t', index = False, header = False)
    
    return


def get_primary_care():
    
    ### PREPARE
    
    # read data
    print(datetime.datetime.now())
    df = pd.read_csv("/nas1/Data/UKBB/UKBBdata/gp_clinical.txt", sep = "\t", 
                     encoding_errors='ignore', low_memory=False)
    print('finish reading ', datetime.datetime.now())

    # merge with dic so we can translate all to read codes ver 2
    rc3_to_rc2 = pd.read_excel("/nas1/Work/users/Eitan/UKBB_loading/outputs/dict/all_lkps_maps_v3.xlsx", sheet_name='read_ctv3_read_v2')
    rc23_read = rc3_to_rc2[['READV2_CODE', 'READV3_CODE']].rename(columns={'READV3_CODE':'read_3'}).drop_duplicates(subset=['read_3'])
    rc23_term = rc3_to_rc2[['READV2_CODE', 'TERMV3_CODE']].rename(columns={'TERMV3_CODE':'read_3', 'READV2_CODE':'READV2_CODE2'}).drop_duplicates(subset=['read_3'])
    
    df = df.merge(rc23_read, on='read_3', how='left')
    df = df.merge(rc23_term, on='read_3', how='left')

    df['read_2'] = df['read_2'].fillna(df['READV2_CODE']).fillna(df['READV2_CODE2'])
    df = df.dropna(subset=['read_2'])
    df = df[df.read_2 != '_NONE']

    # type change, in (relatively) efficient way
    tmp = df.drop_duplicates(subset=['event_dt']).copy()
    tmp['event_dt1'] = pd.to_datetime(tmp['event_dt'])
    print('finish to_datetime', datetime.datetime.now())
    df = df.merge(tmp[['event_dt', 'event_dt1']], on='event_dt', how='left')
    df['event_dt'] = df['event_dt1']
    df.drop(columns='event_dt1', inplace=True)
    df = df.dropna(subset=['event_dt'])

    # read code to signal mapping
    rc2_to_bt = pd.read_csv("/nas1/Work/users/Eitan/UKBB_loading/outputs/dict/thin_signal_mapping.csv", sep='\t')
    rc2_to_bt = rc2_to_bt[266:]
    rc2_to_bt['read_2'] = rc2_to_bt['code'].map(lambda x: x[0:5])
    rc2_to_bt = rc2_to_bt.drop_duplicates(subset=['read_2'])
    df = df.merge(rc2_to_bt[['signal', 'read_2']], on='read_2', how='left')

    print(df.shape)
    
    ### BT

    for sig in rc2_to_bt.signal.unique():
 
        if sig in ['Alcohol_quantity', 'Smoking_quantity']:
            # need specific treatment TBD
            continue
        
        outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_BT/' + sig
        if os.path.isfile(outfile)==True:
            continue
                      
        data = df[df.signal==sig].copy()
        data['signal'] = sig

        # check that we have one numeric value
        data = data_arrange(data, sig)
        print(sig, len(data), datetime.datetime.now())
        print('')
        if len(data) > 0:
            data[['eid', 'signal', 'event_dt', 'value1']].to_csv(outfile, sep='\t', index = False, header = False)

    # next go to other 
    gp = df[df.signal.isna()].copy()

    ### blood pressure
    print('bp ', datetime.datetime.now())
    bp(gp)
    gp = gp[~gp.read_2.isin(['246..', '246A.', '2469.'])]

    ### BMI
    print('BMI ', datetime.datetime.now())
    mydic = {'weight':'22A..', 'height':'229..', 'BMI':'22K..'}

    for k,v in mydic.items():
        outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_MES/' + k
        if os.path.isfile(outfile)==True:
            continue
        tmp = gp[gp.read_2 == v].copy()
        tmp.value1 = tmp.value1.fillna(tmp.value2).fillna(tmp.value3)
        tmp = tmp[pd.to_numeric(tmp.value1, errors='coerce').notnull()]
        tmp.value1 = tmp.value1.astype(float)
        tmp['signal'] = k
        
        if k == 'height':
            tmp.loc[tmp.value1 > 2, 'value1'] *= 0.01

        tmp[['eid', 'signal', 'event_dt', 'value1']].to_csv(outfile, sep='\t', index = False, header = False)

    ### all the rest (without value)
    print('Last... ', datetime.datetime.now())
    gp.value1 = gp.value1.fillna(gp.value2).fillna(gp.value3)
    gp = gp[gp.value1.isna()]
    sig = 'Primary_Care'
    gp['signal'] = sig
    
    # codes with errors that we cannot resolve (1/25000 of the rows, mostly strats with Z)
    bad_read_codes = pd.read_csv('/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/bad_readcodes.txt').code.tolist()
    gp = gp[~gp.read_2.isin(bad_read_codes)].copy()
    gp['to_drop'] = gp.read_2.map(lambda x: x[0]=='Z' and x[1]!='V')
    gp = gp[~gp.to_drop]
       
    outfile = '/nas1/Work/users/Eitan/UKBB_loading/outputs/' + sig
    gp[['eid', 'signal', 'event_dt', 'read_2']].to_csv(outfile, sep='\t', index = False, header = False)
    
    return


def get_first_occurance():
    
    mapping = pd.read_csv("/nas1/Data/UKBB/ukbb_db/first_occurance_data_fields.txt", sep='\t')
    mapping = mapping[mapping.Description.map(lambda s: 'Source' not in s)]
    mapping['icd10'] = 'ICD10_CODE:' + mapping.Description.map(lambda s: s.split(' ')[1])
        
    df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb51583.csv", nrows=2)
    names = df.columns
    
    nrows = 25000
    
    i = 1
    while i > 0:
        print(i, datetime.datetime.now())
        df = pd.read_csv("/nas1/Data/UKBB/ukbb_db/ukb51583.csv", names = names, skiprows = i, nrows=nrows, low_memory=False)
        
        if len(df) == nrows:
            i = i + nrows
        else:
            i = 0
            
        df = (
            df
            .set_index('eid')
            .unstack()
            .reset_index()
            .dropna()
            .rename(columns={0:'time', 'level_0':'Field ID'})
            )

        df['Field ID'] = df['Field ID'].map(lambda x: x.split('-')[0])
        df['Field ID'] = df['Field ID'].astype(int)

        df['time'] = pd.to_datetime(df['time'])
        print(datetime.datetime.now())
               
        df = df.merge(mapping, on='Field ID', how='inner')
        df = df.sort_values(by=['eid', 'time'])
        
        df['signal'] = 'RC'
        
        outfile = "/nas1/Work/users/Eitan/UKBB_loading/outputs/DIAG"
        df = df[['eid', 'signal', 'time', 'icd10']].dropna()
        df.to_csv(outfile, sep='\t', mode = 'a', index = False, header = False)
    
    return

##################################################
# update config and signal files
# both files need some manual work in advance 

def add_NMR_signals():

    outfile1 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/load_config_file.config"
    outfile2 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/ukbb.signals"

    nmr1 = nmr.copy()
    nmr1['col1'] = 'SIGNAL'
    nmr1['signal_type'] = '16:my_SDateVal'
    nmr1['cat'] = 0
    nmr1['last'] = 'na'
    nmr1['NMR'] = 'NMR_' + nmr['signal_name']
    nmr1['sn'] = nmr.signal_number.map(lambda x: x[0:5])
    nmr1[['col1', 'NMR', 'sn', 'signal_type', 'signal_name', 'cat', 'last']].to_csv(outfile2, sep='\t', mode = 'a', index = False, header = False)

    nmr1['file_location'] = '../NMR/NMR_' + nmr1['signal_name']
    nmr1['col1'] = 'DATA'

    nmr1[['col1', 'file_location']].to_csv(outfile1, sep='\t', mode = 'a', index = False, header = False)
    
    return


def add_bt_signals():

    outfile1 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/load_config_file.config"
    outfile2 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/ukbb.signals"

    fs = listdir("/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_BT")
    fs = pd.DataFrame(fs)
    fs.columns = ['sig']

    # DATA  ../GP_BT/ALKPfs['col1'] = 'DATA'
    fs['file_location'] = '../GP_BT/' + fs['sig']
    fs['col1'] = 'DATA'
    fs[['col1', 'file_location']].to_csv(outfile1, sep='\t', mode = 'a', index = False, header = False)

    # SIGNAL    NMR_Triglycerides_in_Small_HDL  23578   16:my_SDateVal  Triglycerides_in_Small_HDL  0   na
    fs['col1'] = 'SIGNAL'
    fs['signal_type'] = '16:my_SDateVal'
    fs['cat'] = 0
    fs['last'] = 'na'
    fs['sn'] = 10000 + fs.index
    fs[['col1', 'sig', 'sn', 'signal_type', 'sig', 'cat', 'last']].to_csv(outfile2, sep='\t', mode = 'a', index = False, header = False)
    
    return


def add_mes_signals():

    outfile1 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/load_config_file.config"
    outfile2 = "/nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/ukbb.signals"

    fs = listdir("/nas1/Work/users/Eitan/UKBB_loading/outputs/GP_MES")
    fs = pd.DataFrame(fs)
    fs.columns = ['sig']

    # DATA  ../GP_BT/ALKPfs['col1'] = 'DATA'
    fs['file_location'] = '../GP_MES/' + fs['sig']
    fs['col1'] = 'DATA'
    fs[['col1', 'file_location']].to_csv(outfile1, sep='\t', mode = 'a', index = False, header = False)

    # SIGNAL    NMR_Triglycerides_in_Small_HDL  23578   16:my_SDateVal  Triglycerides_in_Small_HDL  0   na
    fs['col1'] = 'SIGNAL'
    fs['signal_type'] = '16:my_SDateVal'
    fs['cat'] = 0
    fs['last'] = 'na'
    fs['sn'] = 11000 + fs.index
    fs[['col1', 'sig', 'sn', 'signal_type', 'sig', 'cat', 'last']].to_csv(outfile2, sep='\t', mode = 'a', index = False, header = False)
    
    return

   
# get_first_occurance()
get_basic_features()
# get_cancer_location()
# get_NMR_Metabolomics()
# get_primary_care()
# BDATE_from_BYEAR()
# add_NMR_signals()
# add_bt_signals(
# add_mes_signals(
    


    

       