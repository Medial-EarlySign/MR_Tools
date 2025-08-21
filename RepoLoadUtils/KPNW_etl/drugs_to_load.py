import pandas as pd
from numpy import  nan
import os
import re
import sys
#MR_ROOT = '/opt/medial/tools/bin/'
#sys.path.append(os.path.join(MR_ROOT, 'common'))
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils','common'))
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces
from staging_config import KPNWDemographic, KPNWLabs, KPNWVitals, KPNWLabs2
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files, remove_errors


def normlize_names(ser1):
    ser1 = ser1.str.upper()
    ser2 = ser1.str.replace(r"\(.*\)", "") # remove all in parentases (manufcturer name
    ser2 = ser2.str.replace('-', '_')
    ser2 = ser2.str.replace('"', '')
    ser2 = ser2.str.replace('\'', '')
    ser2 = ser2.apply(lambda x: '_'.join(re.split('_+', str(x))))
    ser2 = ser2.where((ser2.notnull()) & (~ser2.str.endswith('_')), ser2.str[:-1])
    ser2 = ser2.where((ser2.notnull()) & (~ser2.str.endswith('.')), ser2.str[:-1])
    return ser2


def build_drug_map():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    map_file = os.path.join(work_folder, 'drug_names_ndc_kp.csv')
    data_path = os.path.join(work_folder, 'data')
    #data_path = fixOS('W:\\Users\\Avi\\NWP\\data')

    drugs_files = ['drugs_all.csv', 'drugs_delta.csv', 'drugs_delta_aug20.csv', 'drugs_delta_nov20.csv']
    full_files = [os.path.join(data_path, f) for f in drugs_files]
    if os.path.exists(map_file):
        all_drugs = pd.read_csv(map_file, sep='\t')
    else:
        #full_files = [os.path.join(data_path, drugs_file), os.path.join(data_path, delta_drugs_file), os.path.join(data_path, delta_drugs_file2)]
        all_drugs = pd.DataFrame()
        cnt = 1
        for full_file in full_files:
            print('raeding file '+ full_file)
            for drug_df in pd.read_csv(full_file, sep='\t', usecols=[1, 3], names=['drug_name', 'drugid'], chunksize=1000000, header=1):
                print('Read chunck ' + str(cnt))
                drug_df['drug_name'] = replace_spaces(drug_df['drug_name'].str.upper())
                drug_df.drop_duplicates(inplace=True)
                all_drugs = all_drugs.append(drug_df)
                all_drugs.drop_duplicates(inplace=True)
                cnt += 1
        all_drugs = all_drugs[(all_drugs['drug_name'].notnull()) & (all_drugs['drug_name'].str.strip() != '')]
        all_drugs['drug_name'] = normlize_names(all_drugs['drug_name'])
        all_drugs['drugid'] = all_drugs['drugid'].where(all_drugs['drugid'].str[0:5] != '99999', nan)
        all_drugs.sort_values(['drug_name', 'drugid'], na_position='last', inplace=True)
        all_drugs.drop_duplicates('drug_name', keep='first', inplace=True)
        no_ndcs = all_drugs[(all_drugs['drugid'].isnull())]
        print('Missing NDCs No: ' + str(no_ndcs.shape[0]))
        no_ndcs = no_ndcs.assign(drugid=range(100000, 100000 + no_ndcs.shape[0]))
        no_ndcs['drugid'] = 'KP:' + no_ndcs['drugid'].astype(int).astype(str)

        with_ndcs = all_drugs[(all_drugs['drugid'].notnull())].copy()
        #with_ndcs = with_ndcs[with_ndcs['drugid'].str[0:6] != '99999-']
        with_ndcs['drugid'] = 'KP_NDC:' + with_ndcs['drugid']
        print('With NDCs No: ' + str(with_ndcs.shape[0]))
        all_drugs = with_ndcs.append(no_ndcs)
        all_drugs[['drug_name', 'drugid']].to_csv(os.path.join(work_folder, map_file), sep='\t', index=False)
    all_drugs = all_drugs.set_index(['drug_name'])['drugid']
    return all_drugs


def drug_to_load(drug_map):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    data_path = os.path.join(work_folder, 'data')
    #data_path = fixOS('W:\\Users\\Avi\\NWP\\data')
    drugs_files = ['drugs_all.csv', 'drugs_delta.csv', 'drugs_delta_aug20.csv', 'drugs_delta_nov20.csv']
    full_files = [os.path.join(data_path, f) for f in drugs_files]
    id2nr_map = get_id2nr_map()
    all_df = pd.DataFrame()
    cnt = 1
    for full_file in full_files:
        print('reading file ' + full_file)
        for drug_df in pd.read_csv(full_file, sep='\t', usecols=[0, 1, 7, 8],
                                   names=['medialid', 'drug_name', 'start_date', 'end_date'],
                                   chunksize=1000000, header=1):
            print('Read chunk ' + str(cnt))
            drug_df['medialid'] = drug_df['medialid'].astype(int).astype(str).map(id2nr_map)
            drug_df['drug_name'] = replace_spaces(drug_df['drug_name'])
            drug_df['drug_name'] = normlize_names(drug_df['drug_name'])
            drug_df['drug_id'] = drug_df['drug_name'].map(drug_map)
            drug_df = drug_df[(drug_df['start_date'].notnull()) | (drug_df['end_date'].notnull())]
            drug_df.loc[drug_df['start_date'].isnull(), 'start_date'] = drug_df[drug_df['start_date'].isnull()]['end_date']
            drug_df.loc[drug_df['end_date'].isnull(), 'end_date'] = drug_df[drug_df['end_date'].isnull()]['start_date']
            drug_df['start_date'] = pd.to_datetime(drug_df['start_date'], format='%Y%m%d')

            print('Removed due to illigal date ' + str(drug_df[drug_df['start_date'].dt.year <= 1900].shape[0]))
            drug_df = drug_df[drug_df['start_date'].dt.year > 1900]
            print('Removed due to empty drug name ' + str(drug_df[(drug_df['drug_id'].isnull()) | (drug_df['drug_id'].str.strip() == '')].shape[0]))
            drug_df = drug_df[(drug_df['drug_id'].notnull()) & (drug_df['drug_id'].str.strip() != '')]

            drug_df['end_date'] = pd.to_datetime(drug_df['end_date'], format='%Y%m%d')
            drug_df['days'] = (drug_df['end_date'] - drug_df['start_date']).dt.days + 1
            drug_df['days'] = drug_df['days'].where(drug_df['days'] > 0, (drug_df['start_date'] - drug_df['end_date']).dt.days + 1)
            all_df = all_df.append(drug_df[['medialid', 'start_date', 'drug_id', 'days']])
            cnt += 1

    sig = 'Drug'
    all_df['signal'] = sig
    all_df.sort_values(by=['medialid', 'start_date'], inplace=True)
    write_tsv(all_df[['medialid', 'signal', 'start_date', 'drug_id', 'days']], out_folder, sig, mode='w')


if __name__ == '__main__':
    drug_map = build_drug_map()
    drug_to_load(drug_map)
    print('DONE')
