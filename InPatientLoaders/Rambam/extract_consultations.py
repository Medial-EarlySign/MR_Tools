import pandas as pd
import os
from extract_utils import read_rambam_xmls


rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
out_dir = 'W:\\Users\\Tamar\\rambam_load\\raw_tables_extracted_from_xmls\\'
rep_load_dir = 'W:\\Users\\Tamar\\rambam_load\\repo_load_files\\'
id2nr_file = rep_load_dir + '..\\id2nr'


def consult_repfile_prepare(id2nr_map):
    raw_consult_file = out_dir + 'rambam_consult'
    attr_list = ['orderedconsulttype', 'consultingdepartment', 'consultdate', 'orderdate',
                 'consultingdepartment', 'orderedconsulttype']
    if os.path.isfile(raw_consult_file):
        consult_df = pd.read_csv(raw_consult_file, sep='\t')
    else:
        consult_df = read_rambam_xmls(rambam_xml_dir, ['ev_consultations'], attr_list, raw_consult_file)
    # consult_df['orderedconsulttypehier'] = consult_df['orderedconsulttypehier'].where(consult_df['orderedconsulttypehier'] != 'None', consult_df['consultingdepartmenthier'])
    consult_df['orderedconsulttype'] = consult_df['orderedconsulttype'].where(consult_df['orderedconsulttype'] != 'Null', consult_df['consultingdepartment'])
    print(consult_df)

    out_consult_df = pd.DataFrame(columns=['pid', 'signal', 'time1', 'time2', 'val1'])
    out_consult_df['pid'] = consult_df['pid'].map(id2nr_map)
    out_consult_df['signal'] = 'CONSULTATION'
    out_consult_df['time1'] = consult_df['orderdate']
    out_consult_df['time2'] = consult_df['date']
    out_consult_df['val1'] = 'RAMBAM_CODE:' + consult_df['orderedconsulttype'].astype(str)
    out_consult_df.sort_values(['pid', 'time1'], inplace=True)

    rambam_repo_consult = rep_load_dir + 'rambam_repo_consultations'
    out_consult_df.to_csv(rambam_repo_consult, index=False, header=False, sep='\t')
    print(out_consult_df)


if __name__ == '__main__':
    id2nr_map = pd.read_csv(id2nr_file, sep='\t', names=['medial_id', 'rambam_id'])
    id2nr_map = id2nr_map.set_index('rambam_id')['medial_id']
    consult_repfile_prepare(id2nr_map)




