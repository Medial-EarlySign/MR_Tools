import pandas as pd
import os
import sys
import time
# MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
#sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, fwf_formats
from sql_utils import get_sql_engine, pd_to_sql
import d6tstack
#SQL_SERVER = 'POSTGRESSQL'
SQL_SERVER = 'D6_POSTGRESSQL'
DBNAME = 'RawTHIN1801'
username = 'postgres'
password=''


def read_lookup(lookup_name, path, field_dict):
    existing_files = os.listdir(path)
    lookup_file = [x for x in existing_files if x.startswith(lookup_name)][0]
    file_name = os.path.join(path, lookup_file)
    print(" reading from " + file_name)
    colspecs = [(x[0]-1, x[1]) for x in field_dict.values()]
    names = field_dict.keys()
    df = pd.read_fwf(file_name, colspecs=colspecs, names=names)
    return df


def thin_to_tables(file_prefix):
    cfg = Configuration()
    data_path = fixOS(cfg.raw_source_path)
    db_engine = get_sql_engine(SQL_SERVER, DBNAME, username, password)
    in_file_names = list(filter(lambda f: f.startswith(file_prefix), os.listdir(data_path)))

    cnt = 0
    for in_file_name in in_file_names:
        if in_file_name < 'therapy.a7916':
            continue
        print(str(cnt) + ") reading from " + in_file_name)
        time1 = time.time()
        thr_df = read_fwf(file_prefix, data_path, in_file_name)
        #thr_df = thr_df[thr_df['category'].astype(str).str[0] != 'v']
        thr_df['prac'] = in_file_name[-5:]
        time2 = time.time()
        print('    load ' + file_prefix + ' file ' + str(thr_df.shape[0]) + ' records in ' + str(time2 - time1))
        if cnt == 0:
            d6tstack.utils.pd_to_psql(thr_df, db_engine, file_prefix, if_exists='replace')
        else:
            d6tstack.utils.pd_to_psql(thr_df, db_engine, file_prefix, if_exists='append')
        print('    saved ' + in_file_name + ' to sql  records in ' + str(time.time() - time1))
        cnt += 1


def look_up_to_sql(lookup_name, fwf_format):
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    db_engine = get_sql_engine('POSTGRESSQL', DBNAME, username, password)
    lu_df = read_lookup(lookup_name, doc_path, fwf_format)
    print('saving ' + lookup_name + ' to sql')
    pd_to_sql('POSTGRESSQL', lu_df, db_engine, lookup_name, if_exists='replace')
    #lu_df.to_sql(lookup_name, db_engine, if_exists='replace')


def drugs_loopups_to_sql():
    lookups = ['Drugcodes', 'ATCTerms', 'Pack', 'Packsize', 'BNFcode', 'Dosage']
    for lookup in lookups:
        fwf_dict = fwf_formats[lookup]
        look_up_to_sql(lookup, fwf_dict)


def medical_lookups_to_sql():
    lookups = ['NHSspeciality', 'Readcodes']
    for lookup in lookups:
        fwf_dict = fwf_formats[lookup]
        look_up_to_sql(lookup, fwf_dict)


def frequency_to_sql():
    lookups = ['MedicalReadcodeFrequency', 'AHDReadcodeFrequency', 'DrugcodeFrequency']
    for lookup in lookups:
        fwf_dict = fwf_formats[lookup]
        look_up_to_sql(lookup, fwf_dict)


if __name__ == '__main__':
    #thin_to_tables('therapy')
    #thin_to_tables('medical')
    drugs_loopups_to_sql()
    #medical_lookups_to_sql()
    #frequency_to_sql()
