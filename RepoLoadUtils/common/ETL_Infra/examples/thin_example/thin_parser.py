import pandas as pd
import os, re, sys
from ETL_Infra.data_fetcher.files_fetcher import files_fetcher, list_directory_files

#THIN example - the batch will be by "practice file"
def thin_ahd_data_fetcher(batch_size, start_batch):
    files = list_thin_files('^ahd\.')
    return files_fetcher(files, batch_size, thin_file_parser_to_df,start_batch)
 
def thin_patient_data_fetcher(batch_size, start_batch):
    files = list_thin_files('^patient\.')
    return files_fetcher(files, batch_size, thin_file_parser_to_df,start_batch)

def thin_demographic_data_fetcher(batch_size, start_batch):
    yield pd.read_csv('/nas1/Data/THIN2101/IMRD Ancil TEXT/Patient_Demography2101/patient_demography.csv').rename(columns={'combid': 'pid'})

def thin_medical_data_fetcher(batch_size, start_batch):
    files = list_thin_files('^medical\.')
    return files_fetcher(files, batch_size, thin_file_parser_to_df, start_batch)

def thin_therapy_data_fetcher(batch_size, start_batch):
    files = list_thin_files('^therapy\.')
    return files_fetcher(files, batch_size, thin_file_parser_to_df, start_batch)

def list_thin_files(file_prefix):
    base_path='/nas1/Data/THIN2101/THINDB2101'
    return list_directory_files(base_path, file_prefix)

#File type router
def thin_file_parser_to_df(filepath):
    fname=os.path.basename(filepath)
    if fname.startswith('ahd.'):
        df=read_ahd_file(filepath)
    elif fname.startswith('patient.'):
        df= read_demo_file(filepath)
    elif fname.startswith('medical.'):
        df= read_medical_file(filepath)
    elif fname.startswith('therapy.'):
        df= read_therapy_file(filepath)
    else:
        raise NameError(f'Unknown file format {fname}')
    
    return df

def read_ahd_file(filepath):
    columns=['pid', 'time_0', 'ahdcode', 'ahdflag', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'medcode']
    return read_thin_file(filepath, parse_ahd_line, columns)

def read_therapy_file(filepath):
    columns=['pid', 'time_0', 'value_0', 'drugflag']
    return read_thin_file(filepath, parse_therapy_line, columns)

def read_demo_file(filepath):
    columns=['pid', 'patflag', 'yob', 'famenum', 'sex', 'regdate', 'regstat', 'dod', 'xferdate']
    return read_thin_file(filepath, parse_pat_line, columns)

def read_medical_file(filepath):
    columns=['pid', 'eventdate', 'datatype', 'medcode', 'medflag', 'category']
    return read_thin_file(filepath, parse_medical_line, columns)
        
def parse_ahd_line(l, prc):
    return [prc + l[0:4].strip(),l[4:12].strip(),l[12:22].strip(),l[22:23].strip(),l[23:36].strip(),\
    l[36:49].strip(),l[49:62].strip(),l[62:75].strip(),l[75:88].strip(),l[88:101].strip(), l[101:108].strip()]

def parse_therapy_line(l, prc):
    return [prc + l[0:4].strip(),l[4:12].strip(),l[12:20].strip(),l[20:21].strip()]

def parse_pat_line(l, prc):
    return [prc + l[0:4].strip(),l[4:5].strip(),l[5:13].strip(),l[13:19].strip(),l[19:20].strip(),\
    l[20:28].strip(), l[28:30].strip(), l[40:48].strip(), l[30:38].strip()]

def parse_medical_line(l, prc):
    return [prc + l[0:4].strip(), l[4:12].strip(), l[20:22].strip(), l[22:29].strip(),\
    l[29:30].strip(), l[48:49].strip()]

def read_thin_file(filepath, parser_function, columns):
    fr=open(filepath, 'r')
    data=fr.readlines()
    fr.close()
    prc=filepath.split('.')[1]
    data = list(map(lambda x: parser_function(x, prc), data))
    res=pd.DataFrame()
    for i,col in enumerate(columns):
        res[col]=list(map(lambda x: x[i], data))
    #if not('signal' in res):
    #    res['signal']=signal_type
    #res = res[res['ahdflag']=='Y'].reset_index(drop=True)
    return res

def parse_readcodes():
    f_path='/nas1/Data/THIN2101/IMRD Ancil TEXT/text/Readcodes2101.txt'
    fr=open(f_path, 'r')
    lines=fr.readlines()
    fr.close()
    lines=list(map(lambda x: x.strip(),lines))
    lines=list(filter(lambda x: len(x)>0,lines))
    tokens=list(map(lambda x: ['ReadCode:' + x[:7].strip(), x[7:].strip()],lines))
    df_def=pd.DataFrame({'code': list(map(lambda x: x[0],tokens)), 'desc': list(map(lambda x: x[1],tokens))})
    #Add parents
    idx_7_digits=df_def['code'].map(lambda x: len(x[9:])==7)
    parents=df_def[idx_7_digits].reset_index(drop=True).copy()
    parents['code'] = parents['code'].map(lambda x: x[:-2])
    parents['desc'] = ''
    
    df_def= pd.concat([df_def, parents], ignore_index=True)
    
    print(f'Read {f_path}')
    return df_def

def get_icd_to_readcodes():
    f_path='/nas1/Work/Data/Mapping/RC_TO_ICD/Full_RC_MAP.tsv'
    df=pd.read_csv(f_path, sep='\t')
    
    #Readcode to 5 digits
    read_codes=parse_readcodes()
    idx_7_digits=read_codes['code'].map(lambda x: len(x[9:])==7)
    read_cd=read_codes[idx_7_digits].reset_index(drop=True)[['code']]
    read_cd['ICDID'] = read_cd['code'].map(lambda x: x[:-2])
    read_cd=read_cd.rename(columns={'code':'RCID'})
    read_cd=read_cd[['ICDID', 'RCID']]
    
    df['RCID']='ReadCode:' + df['RCID']
    df['ICDID']='ICD10_CODE:' + df['ICDID']
    df=df[['ICDID', 'RCID']]
    #Filter unknown RC:
    before=len(df)
    df=df[df['RCID'].isin(read_codes['code'])].reset_index(drop=True)
    after=len(df)
    if (before!=after):
        print(f'Filtered {before-after} unkown RC codes')
    df = pd.concat([read_cd, df], ignore_index=True)
    print(f'Read {f_path}')
    return df