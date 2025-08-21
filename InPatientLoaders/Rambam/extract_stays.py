import pandas as pd
import os
from extract_utils import read_rambam_xmls

rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
out_dir = 'W:\\Users\\Tamar\\rambam_load\\raw_tables_extracted_from_xmls\\'
rep_load_dir = 'W:\\Users\\Tamar\\rambam_load\\repo_load_files\\'
id2nr_file = rep_load_dir + '..\\id2nr'
rambam_dept_translate = 'dept_heb_to_eng.csv'
# out_file = out_dir + 'rambam_stays'



def visit_repfile_prepare(id2nr_map):
    raw_visit_file = out_dir + 'rambam_outpatient'
    attr_list = ['startdate','enddate', 'visittype', 'departmentcode', 'orderdate']

    if os.path.isfile(raw_visit_file):
        visit_df = pd.read_csv(raw_visit_file, sep='\t')
    else:
        visit_df = read_rambam_xmls(rambam_xml_dir, ['ev_outpatient_visits'], attr_list, raw_visit_file)

    trans_map = pd.read_csv(rambam_dept_translate, sep='\t', names=['heb', 'eng'], encoding="utf8")
    trans_map['eng'] = trans_map['eng'].str.strip().str.replace(' ', '_')
    #trans_map = trans_map.drop_duplicates('heb')
    #trans_map.set_index('heb', drop=True, inplace=True)['eng']

    #visit_df['list'] = visit_df['departmenthier'].str.split(':|~')
    #visit_df['heb_name'] = visit_df.apply(lambda row: row['list'][3] if len(row['list']) > 3 else None, axis=1)
    #visit_df['eng'] = visit_df['heb_name'].map(trans_map)
    #visit_df['eng'] = visit_df['eng'].str.strip().str.replace(' ', '_')

    list_df = visit_df['departmentcodehier'].str.split(':|~', expand=True)
    visit_df['heb_name'] = list_df[3].str.strip()
    #visit_df['eng'] = visit_df['heb_name'].map(trans_map)
    visit_df = visit_df.merge(trans_map, how='left', left_on='heb_name', right_on='heb')
    #visit_df['eng'] = visit_df['eng'].str.strip().str.replace(' ', '_')

    visit_df.drop(columns=['departmentcodehier', 'visittypehier', 'heb_name', 'heb'], inplace=True)
    out_stay_df = pd.DataFrame(columns=['pid', 'signal', 'time', 'val1', 'val2'])
    out_stay_df['pid'] = visit_df['pid'].map(id2nr_map)
    out_stay_df['signal'] = 'VISIT'
    out_stay_df['time'] = visit_df['startdate']
    out_stay_df['val1'] = 'RAMBAM_CODE:' + visit_df['eng'].astype(str)
    out_stay_df['val2'] = 'RAMBAM_CODE:' + visit_df['visittype'].astype(str)
    out_stay_df.sort_values(['pid', 'time'], inplace=True)

    rambam_repo_visits = rep_load_dir + 'rambam_repo_visits'
    out_stay_df.to_csv(rambam_repo_visits, index=False, header=False, sep='\t')
    print(out_stay_df)


def stay_repfile_prepare(id2nr_map):
    raw_stay_file = out_dir + 'rambam_tarnsfers'
    attr_list = ['startdate', 'enddate', 'visittype', 'departmentcode', 'orderdate']
    if os.path.isfile(raw_stay_file):
        stay_df = pd.read_csv(raw_stay_file, sep='\t')
    else:
        stay_df = read_rambam_xmls(rambam_xml_dir, ['ev_transfers'], attr_list, raw_stay_file)

    out_stay_df = pd.DataFrame(columns=['pid', 'signal', 'time1', 'time2', 'val1'])
    out_stay_df['pid'] = stay_df['pid'].map(id2nr_map)
    out_stay_df['signal'] = 'STAY'
    out_stay_df['time1'] = stay_df['startdate']
    out_stay_df['time2'] = stay_df['enddate']
    out_stay_df['val1'] = 'RAMBAM_CODE:' + stay_df['departmentcode'].astype(str)
    out_stay_df.sort_values(['pid', 'time1'], inplace=True)

    rambam_repo_stays = rep_load_dir + 'rambam_repo_stays'
    out_stay_df.to_csv(rambam_repo_stays, index=False, header=False, sep='\t')
    print(out_stay_df)


if __name__ == '__main__':
    id2nr_map = pd.read_csv(id2nr_file, sep='\t', names=['medial_id', 'rambam_id'])
    id2nr_map = id2nr_map.set_index('rambam_id')['medial_id']
    #stay_repfile_prepare(id2nr_map)
    visit_repfile_prepare(id2nr_map)




