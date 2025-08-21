import pandas as pd
import numpy as np
import os, re
from datetime import datetime

from smoking_config import *

MIN_REPO_DATE = 19000101
MAX_REPO_DATE = 20220101

# lab (look for 0 values)
# check KP Fev1 numbers

# Later
# -----
# membership
# BP
# height, weight, BMI

# ahd files - labs
###################
def thin_ahd_lab_data_fetcher(batch_size, batch_num):
    
    data_fetcher = fetch_dataframe('/nas1/Data/THIN2101/THINDB2101', 'ahd.', batch_size, batch_num, max_files=2)
    
    for i,data in enumerate(data_fetcher):
        
        thin_signal_mapping = pd.read_csv('thin_signal_mapping.csv', sep='\t')
        
        # just medcodes with numeric signal
        data.drop(columns='signal', inplace=True)
        data = data.merge(thin_signal_mapping[['signal', 'code', 'description', 'type']].rename(columns={'code':'medcode'}), on='medcode', how='left')
        data = data[data['type']=='numeric']
        
        # remove eGFR (we will calculate independently) smoking statistics, to make statistice meaningful
        data = data[data.signal!='eGFR']
        data = data[data.medcode.map(lambda x: x[0:3]!='137')]
        print('Batch #' + str(i) + ' total candidat numeric rows (without smoking and without eGFR: ' + str(len(data)))
        
        # just numeric values in data field
        data['data2'] = pd.to_numeric(data.data2, errors='coerce')
        data = data[data.data2.notna()]
        print('Batch #' + str(i) + ' after removing no data: ' + str(len(data)))
        
        # must have code for unit
        data = data[data.data3.map(lambda x: x[0:3]=='MEA')] 
        print('Batch #' + str(i) + ' after removing no unit: ' + str(len(data)))
        
        # translate to unit
        translate_to_unit = get_translate_to_unit()
        data = data.merge(translate_to_unit[['data3', 'unit']], on='data3', how='left')
                
        # merge with formula
        unitTranslator = pd.read_csv('unitTranslator.txt', sep='\t')
        unitTranslator.loc[unitTranslator.unit=='None', 'unit'] = 'null value'
        data = data.merge(unitTranslator, on=['signal', 'unit'], how='left')
        
        # print missing formula statistics
        print('Most common missing unit translation:')
        one = pd.DataFrame(data[data.addition.isna()][['signal', 'unit']].value_counts()).rename(columns={0:'missing'})
        two = pd.DataFrame(data[['signal']].value_counts()).rename(columns={0:'total_for_signal'})
        print(one.join(two).sort_values(by='missing').tail(3))
        data = data[data.addition.notna()]
        print('Batch #' + str(i) + ' after removing rows without unit translation: ' + str(len(data)))
        
        # calculate value
        data['value_0'] = data.muliplier.astype(float) * data.data2+ data.addition.astype(float)
        data['value_0'] = data['value_0'] / data.Round
        data['value_0'] = round(data['value_0'], 0) * data.Round
        
        # time cleaning
        return_df = check_and_fix_date(data, col='time_0')
        
        before = len(return_df)
        return_df = return_df[return_df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
        after = len(return_df)
        if before > after:
            print('Batch #' + str(i) + ': drop ' + str(before-after) + ' lab records because date of signal out of repo range')
            
        yield return_df[['pid', 'signal', 'time_0', 'value_0']]     
        
# medical files - diagnosis, other (as diagnosis) and (optional) race
#####################################################################
def thin_medical_data_fetcher(batch_size, batch_num):
    
    data_fetcher = fetch_dataframe('/nas1/Data/THIN2101/THINDB2101', 'medical.', batch_size, batch_num, max_files=5)
    
    for i,data in enumerate(data_fetcher):
        
        print('Batch #' + str(i) + ' total medical rows: ' + str(len(data)) + '\n')
        
        return_df = check_and_fix_date(data, col='time_0')
        return_df.rename(columns={'medcode':'value_0'}, inplace=True)
        return_df['signal'] = 'DIAGNOSIS'
        
        before = len(return_df)
        return_df = return_df[return_df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
        after = len(return_df)
        if before > after:
            print('Batch #' + str(i) + ': drop ' + str(before-after) + ' medical records because date of signal out of repo range')
            
        # To add seperate Ethnicity signal
        # --------------------------------
        breakpoint()
        return_df.loc[(return_df.value_0.str.startswith('9S')) | (return_df.value_0.str.startswith('9t')) | (return_df.value_0.str.startswith('9T')), 'signal'] = 'Ethnicity'
        
        return_df = return_df.sort_values(by=['pid', 'time_0'])
        yield return_df[['pid', 'signal', 'time_0', 'value_0']]

# smoking processing
####################
def thin_smoking_data_fetcher(batch_size, batch_num):
    
    data_fetcher = fetch_dataframe('/nas1/Data/THIN2101/THINDB2101', 'ahd.', batch_size, batch_num, max_files=5)
    
    for i,data in enumerate(data_fetcher):
        
        data = data[data.medcode.str.startswith('137')]
        print('Batch #' + str(i) + ' total rows: ' + str(len(data)) + '\n')
        
        # remove irrelevant codes
        to_ignore = data.medcode.isin(ignore) 
        print('Batch #' + str(i) + ' ignore rows: ' + str(to_ignore.sum()) + '\n')
        data = data[~to_ignore].reset_index()
        
        # status not given
        to_drop = ~data.data1.isin(['Y', 'D', 'N'])
        if to_drop.sum() > 0:
            print('Batch #' + str(i) + ' missing status: ' + str(to_drop.sum()) + '\n')
            data = data[~to_drop].reset_index()
        
        # check for unknown codes
        no_code = ~data.medcode.isin(ex_smoker + smoker + ever_smoker + never_smoker + non_smoker + generic_smoker) 
        if no_code.sum() > 0:
            print('Batch #' + str(i) + ' unknown codes: ' + str(no_code.sum()) + '\n')
            print(data[no_code].medcode.value_counts())
            data = data[~no_code].reset_index()
        
        # update D to N when necessary, and remove in-consistent rows 
        
        before = len(data)
        
        data = N2D(data) 
        data = data[(~data.medcode.isin(ex_smoker)) | (data.data1=='D')]
        data = data[(~data.medcode.isin(smoker)) | (data.data1=='Y')]
        data = data[(~data.medcode.isin(ever_smoker)) | (data.data1.isin(['Y','D']))]
        data = data[(~data.medcode.isin(never_smoker)) | (data.data1=='N')] # note that we drop here original N that we changed to D as they are 'never' (not just non) with intesity info
        data = data[(~data.medcode.isin(non_smoker)) | (data.data1.isin(['N','D']))]
        
        after = len(data)
        print('Batch #' + str(i) + ' in-consistent rows: ' + str(before-after) + ' equal to ' + str(round(100*(before-after)/before,1)) + '%\n')
                   
        # Smoking_Status signal
        
        dict = pd.DataFrame(data={('N', 'Never'), ('D', 'Former'), ('Y', 'Current')}, columns=['data1', 'value_0'])
        smoking_status = data[['pid', 'time_0', 'data1' ]].merge(dict, on='data1', how='left')
        smoking_status['signal'] = 'Smoking_Status'
        smoking_status.drop(columns='data1', inplace=True)
        
        # Smoking_Quit_Date signal
        
        quit_date = data[(data.data1=='D') & (data.data6 != '')][['pid', 'time_0', 'data6']].copy()
        quit_date['signal'] = 'Smoking_Quit_Date'
        quit_date.rename(columns={'data6':'value_0'}, inplace=True)
        quit_date = check_and_fix_date(quit_date, col='value_0')
        quit_date = quit_date[quit_date.value_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
        
        # Smoking_Intensity
        
        intensity = data[(data.data1!='N') & (data.data2!='')][['pid', 'time_0', 'data2']].copy()
        intensity['signal'] = 'Smoking_Intensity'
        intensity.rename(columns={'data2':'value_0'}, inplace=True)
        intensity = intensity[intensity.value_0.str.isnumeric()]
        intensity = intensity[intensity.value_0.astype(int).between(1,MAX_INTENSITY)]
        
        # Pack_Years: Ignore, almost no information
        # Smoking_Duration: Ignore, almost no information about start date

        return_df = pd.concat([smoking_status, quit_date, intensity])
        return_df = return_df.sort_values(by=['pid', 'time_0'])
        return_df = check_and_fix_date(return_df, col='time_0')

        before = len(return_df)
        return_df = return_df[return_df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
        after = len(return_df)
        if before > after:
            print('Batch #' + str(i) + ': drop ' + str(before-after) + ' smoking features because date of signal out of repo range')
                
        yield return_df

                    
# check if N has valid intensity value so he should be D 
def N2D(data):
    df = data[data.data1=='N'].copy()
    df = df[df.data2.str.isnumeric()]
    df = df[df.data2.astype(int).between(1,MAX_INTENSITY)]
    df['N2D'] = True
    print('Convert ', len(df), ' N to D')
    data = data.merge(df[['pid', 'time_0', 'N2D']], on=['pid', 'time_0'], how='left')
    data.loc[data.N2D==True, 'data1'] = 'D'
    return data               


# patient processing
####################
def thin_patient_data_fetcher(batch_size, batch_num):

    data_fetcher = fetch_dataframe('/nas1/Data/THIN2101/THINDB2101', 'patient.', batch_size, batch_num)

    for i,data in enumerate(data_fetcher):
        
        # fix/check BDATE
        data = check_and_fix_date(data, col='BDATE')
        data = check_and_fix_date(data, col='DEATH')

        # arrange in the right format        
        data = (
              data[['pid', 'GENDER', 'BDATE', 'DEATH']]
              .set_index('pid')
              .stack()
              .reset_index()
              .rename(columns={'level_1':'signal', 0:'value_0'})
               )
        
        # remove dead signal 00000000 => means no death
        to_drop = (data.signal=='DEATH') & (data.value_0==-1)
        data = data[~to_drop].reset_index()
        
        # remove patients with DEATH out od repo range
        before = len(data)
        to_drop = (data.signal=='DEATH') & (~data.value_0.astype(int).between(MIN_REPO_DATE, MAX_REPO_DATE))
        if to_drop.sum() > 0:
            print('Batch #' + str(i) + ': Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients death date is out of repo range')
            patients_to_drop = data[to_drop].pid.tolist()
            data = data[~data.pid.isin(patients_to_drop)]
        
        # remove BDATE before 1900 or after 2021
        to_drop = (data.signal=='BDATE') & (~data.value_0.astype(int).between(19000101, 20220101))
        print('Batch #' + str(i) + ': Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients with BDATE before 1990 or after 2021 or not a date as BDATE')
        data = data[~to_drop].reset_index()
        
        # remove signal GENDER with value not in [1,2]
        to_drop = (data.signal=='GENDER') & (~data.value_0.isin(['1', '2']))
        print('Batch #' + str(i) + ': Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients with GENDER other than MALE or FEMALE')
        data = data[~to_drop]
        
        yield data[['pid', 'signal', 'value_0']]

def thin_ahd_data_fetcher(signal, batch_size, batch_num):
    #Will ignore batch_size - will go file over file
    #Will ignore signal - you will filter what you want later
    return fetch_dataframe('/nas1/Data/THIN2101/THINDB2101', 'ahd.', signal, batch_size, batch_num)
 
 
# File loader and parsing
#########################

def fetch_dataframe(base_path, file_prefix_name, batch_size, batch_num=0, max_files=0):
    files = list(filter(lambda x : x.startswith(file_prefix_name) , os.listdir(base_path)))
    files = sorted(files, key=lambda x : x.split('.')[1] )
    all_data = None
    curr_data = []
    if max_files==0:
        max_files=len(files)
    
    for file in files[batch_num:max_files]:
        full_f = os.path.join(base_path, file)
        print('Process file %s'%(full_f), flush=True)
        data = read_file_to_df(full_f)
        data['file_name'] = file.split('.')[1]
        curr_data.append(data)
        print('Done reading')
        if (batch_size>0) and (len(curr_data)>=batch_size):
            data = pd.concat(curr_data, ignore_index=True)
            curr_data = []
            yield data
    
    if len(curr_data) > 0:
        data = pd.concat(curr_data, ignore_index=True)
        yield data
        

#File type router
def read_file_to_df(filepath):
    #data=pd.read_csv(full_f, compression='gzip', sep='|', header=None, index_col=False, names=columns)
    fname=os.path.basename(filepath)
    if fname.startswith('ahd.'):
        df=read_ahd_file(filepath)
        df = df[df['ahdflag']=='Y'].reset_index(drop=True)
    elif fname.startswith('patient.'):
        df= read_demo_file(filepath)
        df = df[df['patflag']=='A'].reset_index(drop=True)
    elif fname.startswith('medical.'):
        df= read_medical_file(filepath)
        df = df[df['medflag']=='R'].reset_index(drop=True)
    else:
        raise NameError(f'Unknown file format {fname}')
    
    return df

def read_thin_file(filepath, parser_function, columns):
    fr=open(filepath, 'r')
    data=fr.readlines()
    fr.close()
    prc=filepath.split('.')[1]
    data = list(map(lambda x: parser_function(x, prc), data))
    res=pd.DataFrame()
    for i,col in enumerate(columns):
        res[col]=list(map(lambda x: x[i], data))
    if not('signal' in res):
        res['signal']=None
    #res = res[res['ahdflag']=='Y'].reset_index(drop=True)
    return res

def read_ahd_file(filepath):
    columns=['pid', 'time_0', 'ahdcode', 'ahdflag', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'medcode']
    return read_thin_file(filepath, parse_ahd_line, columns)

def parse_ahd_line(l, prc):
    return [prc + l[0:4].strip(),l[4:12].strip(),l[12:22].strip(),l[22:23].strip(),l[23:36].strip(),\
    l[36:49].strip(),l[49:62].strip(),l[62:75].strip(),l[75:88].strip(),l[88:101].strip(), l[101:108].strip()]

def read_demo_file(filepath):
    columns=['pid', 'patflag', 'BDATE', 'famenum', 'GENDER', 'regdate', 'regstat', 'DEATH']
    return read_thin_file(filepath, parse_pat_line, columns)

def parse_pat_line(l, prc):
    return [prc + l[0:4].strip(),l[4:5].strip(),l[5:13].strip(),l[13:19].strip(),l[19:20].strip(),\
    l[20:28].strip(), l[28:30].strip(), l[40:48].strip()]

def read_medical_file(filepath):
    columns=['pid', 'time_0', 'datatype', 'medcode', 'medflag', 'category']
    return read_thin_file(filepath, parse_medical_line, columns)

def parse_medical_line(l, prc):
    return [prc + l[0:4].strip(), l[4:12].strip(), l[20:22].strip(), l[22:29].strip(),\
    l[29:30].strip(), l[48:49].strip()]

def check_and_fix_date(data, col):
    data.loc[~data[col].str.isnumeric(), col] = '-1'
    data.loc[data[col]=='00000000', col] = '-1'
    data[col] = data[col].map(lambda x: x if len(x)==8 else x + '01' if len(x)==6 else x + '0101' if len(x)==4 else '-1')
    data[col] = data[col].map(lambda x: x[0:4] + '0101' if x[4:8]=='0000' else x[0:6] + '01' if x[6:8]=='00' else x)
    data[col] = data[col].astype(int)
    return data

def get_translate_to_unit():
    f_MEA = '/nas1/Data/THIN2101/IMRD Ancil TEXT/text/AHDlookups2101.txt'
    mea = pd.read_csv(f_MEA, names = ['input'])
    mea = mea[mea.input.map(lambda x: x[0:3]=='MEA')]
    mea[mea.input.map(lambda s: s[:16]=='MEA MEASURE_UNIT ')].shape
    mea['data3'] = mea.input.map(lambda s: s[38:44])
    mea['unit'] = mea.input.map(lambda s: s[44:].strip())
    return mea

    


    
