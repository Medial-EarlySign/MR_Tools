import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv
from staging_config import JilinLabs, JilinDemographic
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, demographic_to_files
from dictionery_chinese import ch_en_dict


def jilin_labs_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals2')
    jilin_def = JilinLabs()

    jilin_map = pd.read_csv(os.path.join(code_folder, 'jilin_signal_map.csv'), sep='\t')
    #lab_cond = ((jilin_map['source'] == 'jilinlabs') & (jilin_map['signal'] == 'Creatinine'))
    lab_cond = (jilin_map['source'] == 'jilinlabs')
    mimic_map_numeric = jilin_map[(jilin_map['type'] == 'numeric') & lab_cond]
    print(mimic_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    numeric_to_files(jilin_def, mimic_map_numeric, unit_mult, id2nr, out_folder)


def jilin_demographic_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    jilin_def = JilinDemographic()

    jilin_map = pd.read_csv(os.path.join(code_folder, 'jilin_signal_map.csv'), sep='\t')
    lab_cond = ((jilin_map['source'] == 'jilindemographic') & (jilin_map['signal'] == 'BYEAR'))
    #lab_cond = (jilin_map['source'] == 'jilindemographic')
    jilin_map_demo = jilin_map[lab_cond]
    print(jilin_map_demo)
    id2nr = get_id2nr_map()
    demographic_to_files(jilin_def, jilin_map_demo, id2nr, out_folder)


def jilin_table_to_registry(excl_file, path, engine, prefix=None):
    table = excl_file.split('.')[0].replace(' ', '_').lower()

    if prefix:
        table = prefix + '_' + table
    print(table)
    full_file = os.path.join(path, excl_file)
    orig_df = pd.read_excel(full_file, usecols=0)
    en_columns = []
    orig_columns = orig_df.columns
    cnt=1
    for col in orig_columns:
        #col_en = ch_en_dict[col]
        col_en = ch_en_dict.get(col, 'col'+str(cnt))
        if prefix == 'endo':
            if col_en == 'col1':
                col_en = 'patient_id'
            if col_en == 'female' or col_en == 'male':
                col_en = 'gender'
            if col_en == 'col3':
                col_en = 'age'
            if col_en == 'col4' or col_en == 'Stomach pain' or col_en == 'Upper abdominal distension 1 week':
                col_en = 'Chief complaint'

        cnt += 1
        en_columns.append(col_en)
        print(col_en)
    en_columns = [x.replace(' ', '_').lower() for x in en_columns]
    eng_df = pd.DataFrame(columns=en_columns)
    num_cols = len(en_columns)
    for c in range(0, num_cols):
        if en_columns[c] == 'patient_id':
            orig_df = orig_df[orig_df[orig_columns[c]].notnull()]
            orig_df[orig_columns[c]] = orig_df[orig_columns[c]].astype(int)

        if orig_df[orig_columns[c]].dtype != int and orig_df[orig_columns[c]].dtype != float:
            print('translating column ' + en_columns[c])
            eng_df[en_columns[c]] = orig_df[orig_columns[c]].apply(lambda x:  ch_en_dict.get(x, x))
        else:
            print('copy column ' + en_columns[c])
            eng_df[en_columns[c]] = orig_df[orig_columns[c]]
    eng_df.to_sql(table, engine, if_exists='replace', index=False)


def cancer_registry():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    data_folder = fixOS(cfg.data_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    endo_dir = os.path.join(data_folder, 'endoscopic_results', 'outpatient_and_inpatient')
    signal = 'cancer_registry'
    reg_files = {'colorectal': 'cancer cases/2010-2015 colorectal cancer.xlsx',
                 'esophageal': 'cancer cases/2010-2015 esophageal cancer.xlsx',
                 'gastric': 'cancer cases/2010-2015 gastric cancer.xlsx',
                 'precancer_esophagus': 'other findings/Esophagus-otherfindings.xlsx',
                 'precancer_colon': 'other findings/Colon-othrerfindings.xls',
                 'precancer_gastric': 'other findings/Gastric-otherfindings.xlsx'
                }
    id2nr = get_id2nr_map()
    all_cancers = pd.DataFrame()
    for k in reg_files.keys():
        print(k, reg_files[k])
        full_file = os.path.join(endo_dir, reg_files[k])
        if k == 'precancer_gastric':
            pids_df = pd.read_excel(full_file, usecols=[0, 8], names=['patient_id', 'report_time'])
        else:
            pids_df = pd.read_excel(full_file)
        en_columns = {}
        for col in pids_df.columns:
            # col_en = ch_en_dict[col]
            col_en = ch_en_dict.get(col, col)
            en_columns[col] = col_en.replace(' ', '_').lower()
        pids_df.rename(columns=en_columns, inplace=True)
        pids_df['value'] = k
        all_cancers = all_cancers.append(pids_df[['patient_id', 'report_time', 'value']])
    all_cancers['signal'] = signal
    all_cancers['report_time'] = pd.to_datetime(all_cancers['report_time'])
    all_cancers['patient_id'] = pd.to_numeric(all_cancers['patient_id'], errors='coerce')
    all_cancers = all_cancers[all_cancers['patient_id'].notnull()]
    all_cancers['patient_id'] = all_cancers['patient_id'].astype('int64')
    all_cancers['medialid'] = all_cancers['patient_id'].astype(str).map(id2nr)
    all_cancers = all_cancers[all_cancers['medialid'].notnull()]
    all_cancers.sort_values(by=['medialid', 'report_time'], inplace=True)
    cols = ['medialid', 'signal', 'report_time', 'value']
    if os.path.exists(os.path.join(out_folder, signal)):
        os.remove(os.path.join(out_folder, signal))
    write_tsv(all_cancers[cols], out_folder, signal)


if __name__ == '__main__':
    #jilin_labs_to_files()
    jilin_demographic_to_files()
    #cancer_registry()
