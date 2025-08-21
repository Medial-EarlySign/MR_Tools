import pandas as pd
import os
from sql_utils import get_sql_engine
from dictionery_chinese import ch_en_dict

SQL_SERVER = 'POSTGRESSQL'
#SQL_SERVER = 'D6_POSTGRESSQL'
DBNAME = 'RawJilinV2'
username = 'postgres'
password = ''


def jilin_table_no_pid_to_sql(excl_file, path, engine, map_df, prefix=None):
    table = excl_file.split('.')[0].replace(' ', '_').lower()
    # table = 'esophagus_and_stomach_normal_control_group'
    if prefix:
        table = prefix + '_' + table
    print(table)
    full_file = os.path.join(path, excl_file)
    orig_df = pd.read_excel(full_file)
    en_columns = []
    orig_columns = orig_df.columns
    cnt = 1
    for col in orig_columns:
        col_en = ch_en_dict.get(col, 'col' + str(cnt))
        cnt += 1
        en_columns.append(col_en)
        print(col_en)
    en_columns = [x.replace(' ', '_').lower() for x in en_columns]
    if table == 'exam_gastric_examination':  #or table == 'exam_physical_examination_other_findings':
        en_columns = ['patient_type', 'name', 'gender', 'age', 'seen_under_the_microscope', 'microscopic_diagnosis', 'pathological_diagnosis', 'report_time']
    eng_df = pd.DataFrame(columns=en_columns)
    num_cols = len(en_columns)
    for c in range(0, num_cols):
        if orig_df[orig_columns[c]].dtype != int and orig_df[orig_columns[c]].dtype != 'int64' and orig_df[orig_columns[c]].dtype != float:
            print('translating column ' + en_columns[c])
            eng_df[en_columns[c]] = orig_df[orig_columns[c]].apply(lambda x: ch_en_dict.get(str(x).strip(), x))
        else:
            print('copy column ' + en_columns[c])
            eng_df[en_columns[c]] = orig_df[orig_columns[c]]
    eng_df['dob'] = eng_df['report_time'].str[0:4].astype(int) - eng_df['age']
    eng_df['dob'] = eng_df['dob'].astype(float)
    dc_start = 55500000
    eng_df['new_id'] = dc_start + eng_df.index
    eng_df = pd.merge(eng_df, map_df, how='left', left_on=['name', 'gender', 'dob'], right_on=['name', 'gender', 'dob'])
    eng_df['patient_id'] = eng_df['patient_id'].where(eng_df['patient_id'].notnull(), eng_df['new_id'])
    eng_df.to_sql(table, engine, if_exists='replace', index=False)


def jilin_table_to_sql(excl_file, path, engine, prefix=None):
    table = excl_file.split('.')[0].replace(' ', '_').lower()
    #table = 'esophagus_axknd_stomach_normal_control_group'
    if prefix:
        table = prefix + '_' + table
    print(table)
    full_file = os.path.join(path, excl_file)
    orig_df = pd.read_excel(full_file)
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


def build_name_pid_map():
    lab_dir = 'W:\\Users\\Tamar\\a_table_of_content_requested_by_Israel\\laboratory_results\\physical_examination_result\\physical_examination_result'
    map_df = pd.DataFrame()
    for subdir, dirs, files in os.walk(lab_dir):
        for file in files:
            full_file = os.path.join(subdir, file)
            print(full_file)
            orig_df = pd.read_excel(full_file)
            trans_columns = {}
            orig_columns = orig_df.columns
            for col in orig_columns:
                col_en = ch_en_dict[col]
                col_en = col_en.replace(' ', '_').lower()
                trans_columns[col] = col_en
            print(trans_columns)
            orig_df.rename(columns=trans_columns, inplace=True)
            #orig_df = orig_df[(orig_df['patient_id'] > 0) & (orig_df['patient_id'].notnull())]
            orig_df['dob'] = orig_df['bad_code_time'].apply(lambda x: x.year) - orig_df['age']
            #orig_df['dob'] = orig_df['dob'].astype(int)
            map_df = map_df.append(orig_df[['patient_id', 'name', 'gender', 'dob']].drop_duplicates())
    map_df.drop_duplicates(inplace=True)
    return map_df


def to_sql(name_pid_map):
    db_engine = get_sql_engine(SQL_SERVER, DBNAME, username, password)
    #### Labs
    lab_dir = 'W:\\Users\\Tamar\\a_table_of_content_requested_by_Israel\\laboratory_results'
    for subdir, dirs, files in os.walk(lab_dir):
        for file in files:
            print(os.path.join(subdir, file))
            jilin_table_to_sql(file, subdir, db_engine, prefix='labs')

    rootdir = 'W:\\Users\\Tamar\\a_table_of_content_requested_by_Israel\\endoscopic_results\\outpatient_and_inpatient'
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            print(os.path.join(subdir, file))
            jilin_table_to_sql(file, subdir, db_engine, prefix='endo')

    rootdir = 'W:\\Users\\Tamar\\a_table_of_content_requested_by_Israel\\endoscopic_results\\medical_examination'
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            print(os.path.join(subdir, file))
            jilin_table_no_pid_to_sql(file, subdir, db_engine, name_pid_map, prefix='exam')


if __name__ == '__main__':
    name_pid_map = build_name_pid_map()
    to_sql(name_pid_map)

