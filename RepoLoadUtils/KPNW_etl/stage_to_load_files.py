import pandas as pd
import os
import sys
import datetime
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils','common'))

from Configuration import Configuration
from utils import fixOS, read_tsv, write_tsv, replace_spaces, is_nan
from staging_config import KPNWDemographic, KPNWLabs, KPNWVitals, KPNWLabs2
from generate_id2nr import get_id2nr_map
from stage_to_signals import numeric_to_files, categories_to_files, demographic_to_files, remove_errors


def labs_to_files(kp_def, filter, suff=None):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    kp_map = pd.read_csv(os.path.join(code_folder, 'kp_signal_map.csv'), sep='\t')
    lab_chart_cond = (kp_map['source'] == filter)
    #lab_chart_cond = ((kp_map['source'] == filter) & (kp_map['signal'] == 'Resp_Rate'))
    kp_map_numeric = kp_map[(kp_map['type'] == 'numeric') & lab_chart_cond]
    print(kp_map_numeric)
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                         names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    if os.path.exists(os.path.join(code_folder, 'mixture_units_cfg.txt')):
        special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    else:
        special_factors_signals = None
    numeric_to_files(kp_def, kp_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder, suff)


def demographic_stage_to_files():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    kp_def = KPNWDemographic()
    id2nr = get_id2nr_map()
    kp_map = pd.read_csv(os.path.join(code_folder, 'kp_signal_map.csv'), sep='\t')
    demo_cond = (kp_map['source'] == 'medial_flu_pat')
    #demo_cond = (kp_map['source'] == 'medial_flu_pat') & (kp_map['signal'] == 'DEATH')
    kp_map_demo = kp_map[demo_cond]
    print(kp_map_demo)
    demographic_to_files(kp_def, kp_map_demo, id2nr, out_folder)


def category_labs_to_files(kp_def, filter, suff=None):
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    kp_map = pd.read_csv(os.path.join(code_folder, 'kp_signal_map.csv'), sep='\t')
    lab_chart_cond = ((kp_map['source'] == filter) & (kp_map['type'] == 'string'))
    # lab_chart_cond = ((macabi_map['source'] == 'laboratory') & (macabi_map['type'] == 'category') & (macabi_map['signal'] == 'Urine_Leucocytes'))
    kp_map_cat = kp_map[lab_chart_cond]
    print(kp_map_cat)
    id2nr = get_id2nr_map()
    categories_to_files(kp_def, kp_map_cat, id2nr, out_folder, suff)


def load_visits():
    error_file = 'errors_encounters.txt'
    all_errors = pd.DataFrame()
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    visits_file = 'medial_flu_encounters.sas7bdat'

    full_files = []
    for dataf in cfg.data_folders:
        full_files.append(os.path.join(fixOS(dataf), visits_file))
    id2nr_map = get_id2nr_map()
    cnt = 0
    admissions = ['Hospital Emergency Department', 'Hospital Inpatient Admission',
                  'Hospital Observation', 'Residential', 'Hospital Chemical Dependency', 'Hospital Other',
                  'Hospital Mental Health', 'Hospital New Born', 'Hospital Ambulatory Surgery',
                  'Skilled Nursing Facility', 'Hospice', 'Short Term Rehab', 'Intermediate Care Facility',
                  'Ambulatory Surgery Center']
    admissions_df = pd.DataFrame()
    visits_df = pd.DataFrame()
    cols = ['medialid', 'start_date', 'end_date', 'value', 'DRG_CD']
    for full_file in full_files:
        print(full_file)
        for kp_encounters in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
            kp_encounters['medialid'] = kp_encounters['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
            print('   read chuck ' + str(cnt))
            cond = kp_encounters['medialid'].isnull()
            kp_encounters, all_errors = remove_errors(kp_encounters, all_errors, cond, 'no_id')
            ren_dict = {'ENC_BEG_DT': 'start_date', 'ENC_END_DT': 'end_date'}
            kp_encounters.rename(columns=ren_dict, inplace=True)
            kp_encounters['SPECIALTY'].fillna('NA', inplace=True)
            kp_encounters['value'] = kp_encounters['ENC_TYP_DESC'] + ':' + kp_encounters['SPECIALTY']
            # kp_encounters['value'] = kp_encounters['value'].where(kp_encounters['SPECIALTY'].isnull(), kp_encounters['value'] + ':' + kp_encounters['SPECIALTY'])
            kp_encounters['value'] = replace_spaces(kp_encounters['value'])
            admissions_df = admissions_df.append(kp_encounters[kp_encounters['ENC_TYP_DESC'].isin(admissions)][cols])
            visits_df = visits_df.append(kp_encounters[~kp_encounters['ENC_TYP_DESC'].isin(admissions)][cols])
            cnt += 1

    if any(visits_df['start_date'] != visits_df['end_date']):
        print('!!!!!! VISIT with date1!=date2 !!!!!!!!!!!!!!')
        print(visits_df[visits_df['start_date'] != visits_df['end_date']])
    admissions_df.loc[admissions_df['DRG_CD'].isnull(), 'DRG_CD'] = 'unknown'
    admissions_df['DRG_CD'] = 'DRG:' + admissions_df['DRG_CD'].astype(str)
    sig = 'ADMISSION'
    admissions_df['signal'] = sig
    admissions_df.sort_values(by=['medialid', 'start_date'], inplace=True)
    write_tsv(admissions_df[['medialid', 'signal', 'start_date', 'end_date', 'value', 'DRG_CD']], out_folder, sig, mode='w')
    print('DONE ADMISSION')

    sig = 'VISIT'
    visits_df['signal'] = sig
    visits_df.sort_values(by=['medialid', 'start_date'], inplace=True)
    write_tsv(visits_df[['medialid', 'signal', 'start_date', 'value']], out_folder, sig, mode='w')

    if all_errors.shape[0] > 0:
        write_tsv(all_errors[['medialid', 'signal', 'start_date', 'value', 'reason', 'orig_val', 'description']], out_folder, error_file)
    print('DONE STAY')


def load_behav():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    behav_files = 'medial_flu_behav_char.sas7bdat'
    full_files = []
    for dataf in cfg.data_folders:
        full_files.append(os.path.join(fixOS(dataf), behav_files))
    id2nr_map = get_id2nr_map()
    # build data structure
    for kp_behav in pd.read_sas(full_files[0], chunksize=10, iterator=True, encoding='latin-1'):
        break
    sigs = [s for s in kp_behav.columns.tolist() if s not in ['PAT_ID_GEN', 'CONTACT_DATE', 'SMOKING_QUIT_DATE']]
    dfs = {s: pd.DataFrame() for s in sigs}
    ####
    cnt = 0
    for full_file in full_files:
        print(full_file)
        for kp_behav in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
            print('   read chuck ' + str(cnt))
            kp_behav['medialid'] = kp_behav['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
            for s in sigs:
                df = kp_behav[['medialid', 'CONTACT_DATE', s]]
                df = df[(df[s].notnull()) & (df[s].astype(str).str.strip() != '')]
                dfs[s] = dfs[s].append(df)
            cnt += 1

    for sig, df in dfs.items():
        df['signal'] = sig
        if df.shape[0] < 10000:
            continue
        if 'DATE' in sig:
            df[sig] = df[sig].dt.strftime('%Y%m%d')
        elif 'YN' in sig:
            df.loc[df[sig] == 'Y', sig] = 1
            df.loc[df[sig] == 'N', sig] = 0
            df = df[(df[sig] == 0) | (df[sig] == 1)]
        else:
            num_ser = pd.to_numeric(df[sig], errors='coerce')
            if num_ser[num_ser.notnull()].shape[0]*1.2 > df[sig].shape[0]:  # most values are numeric
                #print(' Numeric signal: ' + sig)
                print(sig + 'Non numeric values = ' + str(num_ser[num_ser.isnull()].shape[0]) +'/'+ str(df[sig].shape[0]) + ' in % ' + str(num_ser[num_ser.isnull()].shape[0]/df[sig].shape[0]))
                df[sig] = pd.to_numeric(df[sig], errors='coerce')
                df = df[df[sig].notnull()]
            else:
                print(' Real string signal: '+sig)
                df[sig] = replace_spaces(df[sig].str.strip())
                df[sig] = df[sig].str.replace('=', '').str.replace('"', '').str.replace('`', '')
                df = df[(df[sig].notnull()) & (df[sig] != '')]
                df = df[~df[sig].str.contains('_________________________________________________')]
        df.sort_values(by=['medialid', 'CONTACT_DATE'], inplace=True)
        write_tsv(df[['medialid', 'signal', 'CONTACT_DATE', sig]], out_folder, sig, mode='w')
    print('DONE load_behav')


def load_and_calc_byear():
    #
    # if BYEAR not exist and age=89 and DOD exits: BYEAR = DOD - 90
    # if BYEAR not exist and age = 89: BYAER = 1928
    #
    cfg = Configuration()
    id2nr_map = get_id2nr_map()

    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    pat_demo_file = 'medial_flu_pat.sas7bdat'
    full_files = []
    for dataf in cfg.data_folders:
        full_files.append(os.path.join(fixOS(dataf), pat_demo_file))

    all_df = pd.DataFrame()
    for full_file in full_files:
        print(full_file)
        for demo_df in pd.read_sas(full_file, chunksize=1000000, encoding='utf-8'):
            demo_df['medialid'] = demo_df['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
            demo_df['YOB'] = demo_df['YR_OF_BIRTH']
            # demo_df.loc[demo_df['YR_OF_BIRTH'].notnull(), 'comment'] = 'YR_OF_BIRTH'
            cond1 = (demo_df['YR_OF_BIRTH'].isnull()) & (demo_df['PAT_AGE'].notnull()) & (demo_df['DCSD_DT_GEN'].notnull())
            demo_df.loc[cond1, 'YOB'] = demo_df[cond1]['DCSD_DT_GEN'].dt.year - 90
            # demo_df.loc[cond1, 'comment'] = 'DEATH DATE-90'

            cond2 = (demo_df['YR_OF_BIRTH'].isnull()) & (demo_df['PAT_AGE'] == 89) & (demo_df['DCSD_FLG'] == 0)
            demo_df.loc[cond2, 'YOB'] = 1928
            # demo_df.loc[cond2, 'comment'] = 'set to 1928'
            demo_df['DOB'] = demo_df['YOB'].astype(str) + '0101'
            demo_df = demo_df[demo_df['YOB'].notnull()]
            all_df = all_df.append(demo_df)

    all_df.sort_values(by=['medialid', 'YOB'], inplace=True)
    all_df.drop_duplicates('medialid', keep='last', inplace=True)
    sig = 'BYEAR'
    all_df['signal'] = sig
    write_tsv(all_df[['medialid', 'signal', 'YOB']], out_folder, sig, mode='w')

    sig = 'BDATE'
    all_df['signal'] = sig
    write_tsv(all_df[['medialid', 'signal', 'DOB']], out_folder, sig, mode='w')
    print('DONE BYEAR/BDATE')


def get_one_string_desc(cd, typ, desc):
    prefix = ''
    if is_nan(typ):
        prefix = 'KP:'
    elif 'ICD-10' in typ:
        prefix = 'ICD10:'
    elif 'ICD-9' in typ:
        prefix = 'ICD9:'
    if is_nan(cd):
        cd = ''
    if is_nan(desc):
        desc = ''
    else:
        desc = desc.replace(' ', '_').replace(',', '')
    return prefix+cd+':'+desc


def build_diag_map():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    map_file = os.path.join(work_folder, 'diag_names_map.csv')

    data_path = os.path.join(work_folder, 'data')
    diag_file = 'medial_flu_diagnosis.csv'
    delta_diag_file = 'medial_flu_diagnosis_delta.csv'
    if os.path.exists(map_file):
        all_diags = pd.read_csv(map_file, sep='\t')
    else:
        full_files = [os.path.join(data_path, diag_file), os.path.join(data_path, delta_diag_file)]
        all_diags = pd.DataFrame()
        cnt = 1
        for full_file in full_files:
            for kp_diag in pd.read_csv(full_file, sep='\t', usecols=[3, 4, 5], names=['INDST_DX_CD', 'INDST_DX_TYP', 'DX_NM'],
                                       chunksize=1000000, header=1):
                print('Read chunck ' + str(cnt))
                kp_diag['INDST_DX_CD'] = kp_diag['INDST_DX_CD'].str.replace(',', '.')
                kp_diag.drop_duplicates(inplace=True)
                all_diags = all_diags.append(kp_diag)
                all_diags.drop_duplicates(inplace=True)
                cnt += 1
        all_diags['diag_name'] = all_diags.apply(lambda x: get_one_string_desc(x['INDST_DX_CD'], x['INDST_DX_TYP'], x['DX_NM']), axis=1)
        all_diags.drop_duplicates(subset='diag_name', inplace=True)
        all_diags = all_diags.assign(diagid=range(100000, 100000 + all_diags.shape[0]))
        all_diags['diagid'] = 'KP_DIAG:' + all_diags['diagid'].astype(int).astype(str)
        all_diags[['diag_name', 'diagid']].to_csv(os.path.join(work_folder, map_file), sep='\t', index=False)
    all_diags = all_diags.set_index(['diag_name'])['diagid']
    return all_diags


def load_diagnosis_sas():
    error_file = 'errors_encounters.txt'
    all_errors = pd.DataFrame()
    cfg = Configuration()
    id2nr_map = get_id2nr_map()
    data_path = fixOS(cfg.data_folder)
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    print('Outfolder = ' + out_folder)
    pat_demo_file = 'medial_flu_diagnosis.sas7bdat'
    full_file = os.path.join(data_path, pat_demo_file)
    all_df = pd.DataFrame()
    cnt = 1
    sig = 'DIAGNOSIS'
    diag_map = build_diag_map()
    for kp_diag in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
        kp_diag['medialid'] = kp_diag['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
        print('   read chuck ' + str(cnt))
        cond = kp_diag['medialid'].isnull()
        kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_id')

        #cond = kp_diag['INDST_DX_CD'].isnull()
        #kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_data')

        kp_diag['diag_name'] = kp_diag.apply(lambda x: get_one_string_desc(x['INDST_DX_CD'], x['INDST_DX_TYP'], x['DX_NM']), axis=1)
        kp_diag['diag_id'] = kp_diag['diag_name'].map(diag_map)
        cond = kp_diag['diag_id'].isnull()
        kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_data')

        sv_chunk = 50
        all_df = all_df.append(kp_diag[['medialid', 'DX_DT', 'diag_id', 'DX_1_FLG']])
        if cnt % sv_chunk == 0:
            all_df['signal'] = sig
            all_df.sort_values(by=['medialid', 'DX_DT'], inplace=True)
            sig_file = sig+str(int(cnt/sv_chunk))
            print('Saving to file ' + sig_file)
            if os.path.exists(os.path.join(out_folder, sig_file)):
                os.remove(os.path.join(out_folder, sig_file))
            write_tsv(all_df[['medialid', 'signal', 'DX_DT', 'diag_id', 'DX_1_FLG']], out_folder, sig_file)
            del all_df
            all_df = pd.DataFrame()
        cnt += 1
    all_df['signal'] = sig
    all_df.sort_values(by=['medialid', 'DX_DT'], inplace=True)
    sig_file = sig + str(int((cnt+sv_chunk)/sv_chunk))
    print('Saving to file ' + sig_file)
    if os.path.exists(os.path.join(out_folder, sig_file)):
        os.remove(os.path.join(out_folder, sig_file))
    write_tsv(all_df[['medialid', 'signal', 'DX_DT', 'diag_id', 'DX_1_FLG']], out_folder, sig_file)
    if all_errors.shape[0] > 0:
        write_tsv(all_errors[['medialid', 'signal', 'start_date', 'value', 'reason', 'orig_val', 'description']], out_folder, error_file)


def load_diagnosis_csv():
    error_file = 'errors_encounters.txt'
    all_errors = pd.DataFrame()
    cfg = Configuration()
    id2nr_map = get_id2nr_map()
    data_path = fixOS(cfg.data_folder)
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    cvs_path = os.path.join(work_folder, 'data')
    print('Outfolder = ' + out_folder)
    diags_file = 'medial_flu_diagnosis_1.csv'
    delta_diags_file1 = 'medial_flu_diagnosis_delta_1.csv'
    delta_diags_file2 = 'medial_flu_diagnosis_delta_2.csv'
    delta_diags_file3 = 'medial_flu_diagnosis_delta_3.csv'
    full_files = [os.path.join(cvs_path, diags_file),
                  os.path.join(cvs_path, delta_diags_file1),
                  os.path.join(cvs_path, delta_diags_file2),
                  os.path.join(cvs_path, delta_diags_file3)]

    all_df = pd.DataFrame()
    cnt = 1
    sig = 'DIAGNOSIS'
    diag_map = build_diag_map()
    for full_file in full_files:
        print(full_file)
        for kp_diag in pd.read_csv(full_file, sep='\t', chunksize=1000000, iterator=True, encoding='latin-1'):
            kp_diag['medialid'] = kp_diag['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
            #kp_diag['medialid'] = kp_diag['PAT_ID_GEN'].astype(str).str[:-2].map(id2nr_map)
            print('   read chuck ' + str(cnt))
            cond = kp_diag['medialid'].isnull()
            kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_id')

            #cond = kp_diag['INDST_DX_CD'].isnull()
            #kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_data')

            kp_diag['diag_name'] = kp_diag.apply(lambda x: get_one_string_desc(x['INDST_DX_CD'], x['INDST_DX_TYP'], x['DX_NM']), axis=1)
            kp_diag['diag_id'] = kp_diag['diag_name'].map(diag_map)
            cond = kp_diag['diag_id'].isnull()
            kp_diag, all_errors = remove_errors(kp_diag, all_errors, cond, 'no_data')

            sv_chunk = 50
            all_df = all_df.append(kp_diag[['medialid', 'DX_DT', 'diag_id', 'DX_1_FLG']])
            if cnt % sv_chunk == 0:
                all_df['signal'] = sig
                all_df.sort_values(by=['medialid', 'DX_DT'], inplace=True)
                sig_file = sig+str(int(cnt/sv_chunk))
                print('Saving to file ' + sig_file)
                if os.path.exists(os.path.join(out_folder, sig_file)):
                    os.remove(os.path.join(out_folder, sig_file))
                write_tsv(all_df[['medialid', 'signal', 'DX_DT', 'diag_id', 'DX_1_FLG']], out_folder, sig_file)
                del all_df
                all_df = pd.DataFrame()
            cnt += 1
    all_df['signal'] = sig
    all_df.sort_values(by=['medialid', 'DX_DT'], inplace=True)
    sig_file = sig + str(int((cnt+sv_chunk)/sv_chunk))
    print('Saving to file ' + sig_file)

    write_tsv(all_df[['medialid', 'signal', 'DX_DT', 'diag_id', 'DX_1_FLG']], out_folder, sig_file, mode='w')
    if all_errors.shape[0] > 0:
        write_tsv(all_errors[['medialid', 'signal', 'start_date', 'value', 'reason', 'orig_val', 'description']], out_folder, error_file)


def load_membership():
    error_file = 'errors_membership.txt'
    all_errors = pd.DataFrame()
    cfg = Configuration()
    id2nr_map = get_id2nr_map()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    pat_demo_file = 'medial_flu_pat_membership.sas7bdat'
    full_files = [os.path.join(fixOS(cfg.delta_data_folder2), pat_demo_file),
                  os.path.join(fixOS(cfg.delta_data_folder), pat_demo_file),
                  os.path.join(fixOS(cfg.data_folder), pat_demo_file)
                  ]
    all_df = pd.DataFrame()

    for i, d_file in zip(range(1, len(full_files) + 1), full_files):
        print('Reading file ' + d_file + ' (' + str(i) + ')')
        member_one_df = pd.read_sas(d_file, encoding='latin-1')
        member_one_df['ver'] = i
        all_df = all_df.append(member_one_df)

    all_df.sort_values(['PAT_ID_GEN', 'COVERAGE_START_DT', 'COVERAGE_END_DT', 'ver'], inplace=True)
    all_df.drop_duplicates(['PAT_ID_GEN', 'COVERAGE_START_DT', 'COVERAGE_END_DT'], keep='first', inplace=True)

    curr_pids = all_df[(all_df['ver'] == 1) | (all_df['ver'] == 2)]['PAT_ID_GEN'].unique().tolist()

    #pids that exists in delta 1 and not in delta 2
    only_2 = all_df.groupby('PAT_ID_GEN')['ver'].max()
    only_2 = only_2[only_2 == 2].index.tolist()

    all_df.groupby('PAT_ID_GEN')['ver'].max()[all_df.groupby('PAT_ID_GEN')['ver'].max() == 2]

    ok_mem = all_df[(all_df['COVERAGE_END_DT'] != '2099-12-31') | (~all_df['PAT_ID_GEN'].isin(curr_pids))].copy()

    curr_df = all_df[(all_df['PAT_ID_GEN'].isin(curr_pids))]
    last_date_3 = datetime.datetime.strptime('2019-05-01', '%Y-%m-%d')
    last_date_2 = datetime.datetime.strptime('2020-04-01', '%Y-%m-%d')
    last_date_1 = datetime.datetime.strptime('2020-08-01', '%Y-%m-%d')
    curr_df.loc[(curr_df['ver'] == 2) & (curr_df['COVERAGE_END_DT'] == '2099-12-31'), 'COVERAGE_END_DT'] = last_date_2
    curr_df.loc[(curr_df['ver'] == 2) & (curr_df['COVERAGE_END_DT'] == last_date_2), 'ver'] = 3
    curr_df = curr_df[curr_df['COVERAGE_START_DT'] <= last_date_1]
    ok_2 = pd.DataFrame()
    cnt=0

    for pid, df in curr_df.groupby('PAT_ID_GEN'):
        if df['ver'].max() < 3 or df[df['ver'] != 3].shape[0]==0:  # New pid
            ok_2 = ok_2.append(df)
        else:
            df3 = df[df['ver'] == 3]
            df1 = df[df['ver'] != 3]
            if df1.shape[0] != 1:
                print(df)
            assert (df1.shape[0] == 1)
            if df1['COVERAGE_END_DT'].max() == df3['COVERAGE_END_DT'].max():
                ok_2 = ok_2.append(df3)
            elif df3['COVERAGE_END_DT'].max() <= last_date_3:
                ok_2 = ok_2.append(df3)
                df1.loc[:, 'COVERAGE_START_DT'] = df3['COVERAGE_END_DT'].max()
                ok_2 = ok_2.append(df1)
            else:
                ok_2 = ok_2.append(df)
        cnt+=1
        if cnt % 1000 == 0:
            print(cnt)
    ok_2['CURRENT_MEMBER_FLAG'] = 1
    ok_2.loc[ok_2['PAT_ID_GEN'].isin(only_2), 'CURRENT_MEMBER_FLAG'] = 0

    kp_mem = ok_mem.append(ok_2)
    kp_mem['medialid'] = kp_mem['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
    #cond = all_df['medialid'].isnull()
    #kp_mem, all_errors = remove_errors(kp_mem, all_errors, cond, 'no_id')

    kp_mem.sort_values(by=['medialid', 'COVERAGE_START_DT', 'CURRENT_MEMBER_FLAG'], inplace=True)
    kp_mem.drop_duplicates(['medialid', 'COVERAGE_START_DT', 'COVERAGE_END_DT'], keep='last', inplace=True)
    sig = 'MEMBERSHIP'
    kp_mem['signal'] = sig
    write_tsv(kp_mem[['medialid', 'signal', 'COVERAGE_START_DT', 'COVERAGE_END_DT', 'CURRENT_MEMBER_FLAG']], out_folder, sig, mode='w')
    print('DONE MEMBERSHIP')


def load_vaccination():
    error_file = 'vaccinations_membership.txt'
    all_errors = pd.DataFrame()
    cfg = Configuration()
    id2nr_map = get_id2nr_map()

    work_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    code_name_file = os.path.join(code_folder, 'CVX_IMMUNZTN_NAME.tsv')
    code_name_map = pd.read_csv(code_name_file, sep='\t')
    code_name_map = code_name_map.set_index('IMMUNZATN_NAME')['IMM_CVX_CODE']

    st_vacc_files = ['medial_flu_or_vaccination.sas7bdat', 'medial_flu_wa_vaccination.sas7bdat',
                     'medial_flu_vaccination.sas7bdat']
    all_df = pd.DataFrame()

    for vc_file in st_vacc_files:
        cnt = 1
        full_files = []
        for dataf in cfg.data_folders:
            full_files.append(os.path.join(fixOS(dataf), vc_file))
        for full_file in full_files:
            print(full_file)
            for kp_vak in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
                print('   read chuck ' + str(cnt))
                kp_vak['medialid'] = kp_vak['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
                cond = kp_vak['medialid'].isnull()
                kp_vak, all_errors = remove_errors(kp_vak, all_errors, cond, 'no_id')

                if vc_file == 'medial_flu_vaccination.sas7bdat':
                    kp_vak['CVX'] = kp_vak['IMMUNZATN_NAME'].map(code_name_map)
                    kp_vak.rename(columns={'IMMUNE_DATE': 'DATE_ADMIN'}, inplace=True)
                print('null codes: ' + str(kp_vak[kp_vak['CVX'].isnull()].shape[0]))
                kp_vak['CVX'].fillna(0, inplace=True)
                kp_vak['vacc'] = 'CVX_CODE:' + kp_vak['CVX'].astype(int).astype(str)

                all_df = all_df.append(kp_vak[['medialid', 'DATE_ADMIN', 'vacc']])

    all_df.sort_values(by=['medialid', 'DATE_ADMIN'], inplace=True)
    sig = 'Vaccination'
    all_df['signal'] = sig
    write_tsv(all_df[['medialid', 'signal', 'DATE_ADMIN', 'vacc']], out_folder, sig, mode='w')
    if all_errors.shape[0] > 0:
        write_tsv(all_errors[['medialid', 'signal', 'vacc', 'reason', 'orig_val', 'description']], out_folder, error_file, mode='w')


def calc_smoking():
    cfg = Configuration()
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    visits_file = 'medial_flu_behav_char.sas7bdat'
    full_files = []
    for dataf in cfg.data_folders:
        full_files.append(os.path.join(fixOS(dataf), visits_file))
    id2nr_map = get_id2nr_map()
    cnt = 0
    smok_df = pd.DataFrame()
    usecols = ['PAT_ID_GEN', 'CONTACT_DATE', 'TOBACCO_USER_C', 'TOBACCO_PAK_PER_DY', 'SMOKING_QUIT_DATE']
    CIGS_PER_PACK = 20
    TOBACCO_USER_C_map = {1: 'Current', 2: 'Never', 4: 'Former', 5: 'Passive'}
    # SMOKING_TOB_USE_C_sets = {'Current': {1, 2, 10, 3, 9}, 'Never': {5}, 'Former': {4}, 'Passive': {7}}
    for full_file in full_files:
        print(full_file)
        for kp_behav in pd.read_sas(full_file, chunksize=1000000, iterator=True, encoding='latin-1'):
            print('   read chuck ' + str(cnt))
            smok_df = smok_df.append(kp_behav[usecols])
            cnt+=1

    smok_df['medialid'] = smok_df['PAT_ID_GEN'].astype(int).astype(str).map(id2nr_map)
    smok_df.sort_values(by=['medialid', 'CONTACT_DATE'], inplace=True)

    sig = 'Smoking_Status'
    smok_df['signal'] = sig
    smok_df['final_status'] = smok_df['TOBACCO_USER_C'].map(TOBACCO_USER_C_map)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(smok_df[smok_df['final_status'].notnull()][['medialid', 'signal', 'CONTACT_DATE', 'final_status']], out_folder, sig)

    sig = 'Smoking_Intensity'
    smok_df['signal'] = sig
    smok_df['TOBACCO_PAK_PER_DY'] = pd.to_numeric(smok_df['TOBACCO_PAK_PER_DY'], errors='coerce')
    smok_df.loc[:, 'sig_per_day'] = smok_df['TOBACCO_PAK_PER_DY'] * CIGS_PER_PACK
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(smok_df[smok_df['sig_per_day'].notnull()][['medialid', 'signal', 'CONTACT_DATE', 'sig_per_day']], out_folder, sig)

    sig = 'Smoking_Quit_Date'
    smok_df['signal'] = sig
    smok_df['SMOKING_QUIT_DATE'] = smok_df['SMOKING_QUIT_DATE'].astype(str).str.replace('-', '')
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(smok_df[smok_df['SMOKING_QUIT_DATE'] != 'NaT'][['medialid', 'signal', 'CONTACT_DATE', 'SMOKING_QUIT_DATE']],
              out_folder, sig)


if __name__ == '__main__':
    labs_to_files(KPNWLabs(), 'kpnwlabs')
    labs_to_files(KPNWVitals(), 'kpnwvitals')
    labs_to_files(KPNWLabs2(), 'kpnwlabs2',  '_lab2_')
    category_labs_to_files(KPNWLabs(), 'kpnwlabs')
    category_labs_to_files(KPNWLabs2(), 'kpnwlabs2', '_lab2')
    demographic_stage_to_files()

    load_visits()
    load_behav()
    load_and_calc_byear()
    load_diagnosis_csv()
    load_membership()
    load_vaccination()
    calc_smoking()
