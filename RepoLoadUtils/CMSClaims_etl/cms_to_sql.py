import os
import sys
import pandas as pd
import io
import time
from utils import fixOS
from sql_utils import get_sql_engine
from Configuration import Configuration
import d6tstack
#SQL_SERVER = 'MSSQL'
SQL_SERVER = 'POSTGRESSQL'
#SQL_SERVER = 'D6_POSTGRESSQL'
DBNAME = 'RawCMS_syn'
username = 'postgres'
password=''

file_type = ['Beneficiary', 'Carrier', 'Inpatient', 'Outpatient', 'Prescription']


def cms_to_sql(cms_file, data_folder, db_engine):
    full_file = os.path.join(data_folder, cms_file)
    c_size = 1000000
    cnt = 0
    time2 = time.time()
    table = [x for x in file_type if x in cms_file][0]
    table = table.replace('"', '')
    if table == 'Beneficiary':
        year = cms_file.split('_')[2]
        print('year=' + str(year))

    print('reading from ' + full_file)
    for csv_df in pd.read_csv(full_file, chunksize=c_size):  # , skiprows=32000000):
        ren_cols = {x: x.replace('"', '') for x in csv_df.columns}
        csv_df.rename(columns=ren_cols, inplace=True)
        if table == 'Beneficiary':
            csv_df['year']=year
        time1 = time.time()
        print('    load cunk ' + str(cnt) + ' from ' + cms_file + ' file ' + str(csv_df.shape[0]) + ' records in ' + str(time1 - time2))
        csv_df.to_sql(table, db_engine, if_exists='append', index=False)
            #d6tstack.utils.pd_to_psql(mim_df, db_engine, table, if_exists='append')
        print('    saved ' + table + ' to sql in ' + str(time.time() - time1))
        time2 = time.time()
        cnt += 1


def icd9_to_sql(db_engine):
    icd9_dx = 'H:\\MR\\Tools\\DictUtils\\Ontologies\\ICD9\\icd9dx2015.csv'
    icd9_sg = 'H:\\MR\\Tools\\DictUtils\\Ontologies\\ICD9\\icd9sg2015.csv'

    dx_df = pd.read_csv(icd9_dx)
    dx_df['type'] = 'DX'
    dx_df.rename(columns={dx_df.columns[0]: 'code'}, inplace=True)
    dx_df.to_sql('ICD9', db_engine, if_exists='replace', index=False)

    sg_df = pd.read_csv(icd9_sg)
    sg_df['type'] = 'SG'
    sg_df.rename(columns={sg_df.columns[0]: 'code'}, inplace=True)
    sg_df.to_sql('ICD9', db_engine, if_exists='append', index=False)


def hcpcs_to_sql(db_engine):
    hcpc_file = 'H:\\MR\\Tools\\DictUtils\\Ontologies\\HCPCS\\HCPC2018 simplied.txt'
    hc_df = pd.read_csv(hcpc_file, sep='\t', skiprows=4)
    hc_df.to_sql('HCPCS', db_engine, if_exists='replace', index=False)


def cpt_to_sql(db_engine):
    cpt_file = 'H:\\MR\\Tools\\DictUtils\\Ontologies\\CPT\\CPT codes.txt'
    cpt_df = pd.read_csv(cpt_file, sep='\t', usecols=[0, 1], dtype={'CPT_CODE': str})
    print(cpt_df)
    cpt_df.to_sql('CPT', db_engine, if_exists='replace', index=False)


def providers_to_sql(cfg, db_engine):
    #https://data.cms.gov/Medicare-Inpatient/Inpatient-Prospective-Payment-System-IPPS-Provider/97k6-zzx3
    prov_file = os.path.join(fixOS(cfg.cms_folder), 'Inpatient_Prospective_Payment_System__IPPS__Provider_Summary_for_the_Top_100_Diagnosis-Related_Groups__DRG__-_FY2011.csv')
    prov_df = pd.read_csv(prov_file)
    prov_df.to_sql('ip_providers', db_engine, if_exists='replace', index=False)


if __name__ == '__main__':
    cfg = Configuration()
    data_folder = fixOS(cfg.data_folder)
    cms_files = os.listdir(data_folder)
    db_engine = get_sql_engine(SQL_SERVER, DBNAME, username, password)

    # for fl in cms_files:
    #    cms_to_sql(fl, data_folder, db_engine)

    #icd9_to_sql(db_engine)
    #hcpcs_to_sql(db_engine)
    #cpt_to_sql(db_engine)
    providers_to_sql(cfg, db_engine)
