import pandas as pd
import os
from Configuration import Configuration
from utils import fixOS
from staging_config import MimicLabs
from sql_utils import get_sql_engine
from get_from_stage import  get_itemid_units


cfg = Configuration()
raw_path = fixOS(cfg.data_folder)
code_folder = fixOS(cfg.code_folder)
old_conf_path = fixOS('H:\\MR\Tools\\InPatientLoaders\\mimic3\\Configs')
mimic_source_dir = fixOS('T:\\ICU\\Mimic-3-1.4\\')


lab_maps_file = 'LabEvents.Signals.More_Than_1000_Events'
char_maps_file = 'ChartEvents.Signals.More_Than_100000_Events.Filtered'
output_map_file = 'OutputEvents.Signals.More_Than_100_Events'
lab_itemid = pd.read_csv(os.path.join(mimic_source_dir, 'D_LABITEMS.csv'))
all_itemid = pd.read_csv(os.path.join(mimic_source_dir, 'D_ITEMS.csv'))
#lab_map_df = pd.read_csv(os.path.join(old_conf_path, lab_maps_file), sep='\t', names=['ITEMID', 'description_old', 'type', 'sig'])

# lab_map_df = lab_map_df.merge(lab_itemid[['ITEMID', 'LABEL']], how='left', on='ITEMID')
# lab_map_df.rename(columns={'ITEMID': 'code', 'LABEL': 'description'}, inplace=True)
# lab_map_df['signal'] = lab_map_df['sig'].apply(lambda x: x[x.find('_')+1:])
# lab_map_df['source'] = 'labevents'
# lab_map_df['type'] = lab_map_df['type'].str.replace('VALUE', 'numeric')
# lab_map_df['type'] = lab_map_df['type'].str.replace('TEXT', 'string')
# print(lab_map_df)


#char_map_df = pd.read_csv(os.path.join(old_conf_path, char_maps_file), sep='\t', names=['ITEMID', 'description_old', 'type', 'sig'])

# char_map_df = char_map_df.merge(all_itemid[['ITEMID', 'LABEL']], how='left', on='ITEMID')
# char_map_df.rename(columns={'ITEMID': 'code', 'LABEL': 'description'}, inplace=True)
# char_map_df['signal'] = char_map_df['sig'].apply(lambda x: x[x.find('_')+1:])
# char_map_df['source'] = 'chartevents'
# char_map_df['type'] = char_map_df['type'].str.replace('VALUE', 'numeric')
# char_map_df['type'] = char_map_df['type'].str.replace('TEXT', 'string')
# cols = ['signal', 'source', 'code', 'description', 'type']
# lab_map_df = pd.concat([lab_map_df[cols], char_map_df[cols]])
# lab_map_df.sort_values(by='signal', inplace=True)
# lab_map_df.to_csv(os.path.join(code_folder, 'mimic_signal_map.csv'), sep='\t', index=False)
# print(lab_map_df)

# op_map_df = pd.read_csv(os.path.join(old_conf_path, output_map_file), sep='\t', names=['ITEMID', 'description_old', 'type', 'signal'])
# op_map_df = op_map_df.merge(all_itemid[['ITEMID', 'LABEL']], how='left', on='ITEMID')
# op_map_df.rename(columns={'ITEMID': 'code', 'LABEL': 'description'}, inplace=True)
# op_map_df['source'] = 'outputevents'
# op_map_df['type'] = op_map_df['type'].str.replace('VALUE', 'numeric')
# op_map_df['type'] = op_map_df['type'].str.replace('TEXT', 'string')
# cols = ['signal', 'source', 'code', 'description', 'type']
# op_map_df.sort_values(by='signal', inplace=True)
# op_map_df[cols].to_csv(os.path.join(code_folder, 'mimic_output_map.csv'), sep='\t', index=False)


mimic_map = pd.read_csv(os.path.join(code_folder, 'mimic_signal_map.csv'), sep='\t')
signals_units = pd.read_csv(os.path.join(code_folder, '..\\common_knowledge\\', 'signal_units.txt'), sep='\t')
#mrg = signals_units.merge(mimic_map, how='left', left_on='Name', right_on='signal')
#print('ddd')


#-----
# Create unit initial unitTranslator.txt file with 1 to 1 transletors
# mimic_map = mimic_map[mimic_map['type'] == 'numeric']
# mimic_def = MimicLabs()
# db_engine = get_sql_engine(mimic_def.DBTYPE, mimic_def.DBNAME, mimic_def.username, mimic_def.password)
# unit_trans = []
# for i, ev in mimic_map.iterrows():
#     print(ev['signal'])
#     sig_units = get_itemid_units(db_engine, mimic_def.TABLE, ev['code'])
#     for un in sig_units:
#         dict1 = {'signal': ev['signal'], 'unit': un, 'muliplier': 1, 'addition': 0}
#         unit_trans.append(dict1)
# unit_trans_df = pd.DataFrame(unit_trans)
# unit_trans_df.drop_duplicates(inplace=True)
# unit_trans_df[['signal', 'unit', 'muliplier', 'addition']].to_csv(os.path.join(code_folder, 'unitTranslator.txt'), sep='\t', index=False)

admissions_df = pd.read_csv(os.path.join(raw_path, 'ADMISSIONS.csv'), encoding='utf-8')
adm_diags = admissions_df[['DIAGNOSIS']]
adm_diags = adm_diags[adm_diags['DIAGNOSIS'].notnull()]
adm_diags.drop_duplicates(inplace=True)
adm_diags['DIAGNOSIS'] = adm_diags['DIAGNOSIS'].str.replace('\\', ';')
adm_diags['DIAGNOSIS'] = adm_diags['DIAGNOSIS'].str.replace(',', ';')
adm_diags['diag_list'] = adm_diags['DIAGNOSIS'].str.split(';', expand=False)
single_diags = []
for i, row in adm_diags.iterrows():
    print(row['diag_list'])
    for d in row['diag_list']:
        single_diags.append({'diag': d.strip(), 'orig': row['DIAGNOSIS']})
df = pd.DataFrame(single_diags)
#df['no_chars'] = df['diag'].str.replace('\W', '')
#df.drop_duplicates(subset='no_chars', inplace=True)
print(adm_diags)