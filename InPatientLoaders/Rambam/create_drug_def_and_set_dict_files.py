#!/usr/bin/env python
# imports
import pandas as pd
import numpy as np

working_directory = '/nas1/UsersData/reutf/MR/Tools/InPatientLoaders/Rambam/'
repository_directory = '/nas1/Work/CancerData/Repositories/Rambam/rambam_nov2018/'

orig_atc_def = pd.read_csv(repository_directory + 'dicts/dict.atc_defs', sep='\t', names=['DEF','def_num','code'])
def_start_num = int(orig_atc_def.iloc[-1,1]) + 1 # should be 112661

def append_underscore_n(code, num = 7):
    num_to_append = num - len(code)
    return code + '_'*num_to_append 

# load atc codes (Pini's file - to be used as a baseline)
act_codes = pd.read_csv( working_directory + 'atc.csv')

# remove duplicates
act_codes = act_codes.drop_duplicates(subset='ATC code')

# create list of base atc values
atc_code_list = act_codes['ATC code'].values.tolist()

# show results
atc_code_list

#atc_code_list = sorted(list(set(atc_code_list)))

atc_code_name_list = act_codes['ATC level name'].values.tolist()


# load Rambam definitions (Ido's definitions)
rambam_codes = pd.read_csv(repository_directory + 'dicts/dict.atc_defs', sep='\t', header=0, names=['in_code','atc_desc' ])

# select code portion of atc description
rambam_codes['code'] = rambam_codes.atc_desc.str.extract(r'ATC:([_|A-Z0-9]*)DESC:*')

# create list of codes per description
rambam_codes['code_list'] = list(filter(bool,rambam_codes.code.str.findall(r'[_|]*([A-Z0-9]*)[_|]*')))

# remove trailing empty string from list
rambam_codes['code_list_short'] = [[ y for y in x[:-1]] for x in rambam_codes.code_list]

rambam_codes

# seperate codes to different rows
set_df = pd.DataFrame(rambam_codes.set_index('atc_desc').code_list_short.apply(pd.Series).stack())

# column name correction
set_df = set_df.rename(columns={0:'code'})

# is code in the atc list?
set_df['is_atc'] = [ x in atc_code_list for x in set_df.code]

# clean up
set_df = set_df.reset_index()
del set_df['level_1']

set_df['SET'] = 'SET'

set_df


# lookup code that seem like atc codes but were not found in the act file
set_df[(set_df['is_atc'] == False) & (set_df['code'].str.contains(r'[0-9_]*([A-Z])[0-9_]*'))]


act_alterations = pd.read_csv(working_directory + 'ATC_alterations_from_2005-2018.txt', sep='\t')
act_alterations

# fix alterations file
act_alterations['Previous ATC code fixed'] = act_alterations['Previous ATC code'].str.extract(r'([A-s0-9]*)[\s]*[()0-9]*')
act_alterations['New ATC code fixed'] = act_alterations['New ATC code'].str.extract(r'([A-s0-9]*)[\s]*[()0-9]*')

act_alterations

# fix atc resembling codes
set_df['old_code'] = set_df[(set_df['is_atc'] == False) & (set_df['code'].str.contains(r'[0-9_]*([A-Z])[0-9_]*'))].code
new_code_dict = pd.Series(act_alterations['New ATC code fixed'].values, index=act_alterations['Previous ATC code fixed']).to_dict()
set_df.code.replace(new_code_dict, inplace=True)

set_df

# recalculate is_atc
set_df['is_atc'] = [ x in atc_code_list for x in set_df.code]

# create prefix
set_df['prefix'] = np.where(set_df['is_atc'], 'ATC_', 'RMB_')


# codes resembling atc left after fixing alterations
set_df[(set_df['is_atc'] == False) & (set_df['code'].str.contains(r'[0-9_]*([A-Z])[0-9_]*'))]

# unfmiliar codes
set_df[(set_df['is_atc'] == False) & (set_df['code'].str.contains(r'[0-9_]*([A-Z])[0-9_]*') == False)].atc_desc.values

# create set file format
set_df['code_format'] = set_df.code.apply(append_underscore_n)
set_df['code_format_2'] = set_df.code_format.str.slice(0,4) + '_' +  set_df.code_format.str.slice(4)
set_df['code_full'] = set_df.prefix + set_df.code_format_2


# ## act hierarcy set file


# create act hierarchy df from act list
atc_code_dataframe = pd.DataFrame(columns=['atc_desc', 'code'])
for x in atc_code_list:
    code_len = len(x)
    if code_len == 1:
        sub_1 = x
    elif code_len == 3:
        if sub_1 not in x:
            print("ERROR")
            break
        sub_3 = x
        atc_code_dataframe = atc_code_dataframe.append({'atc_desc':x, 'code':sub_1}, ignore_index=True)
    elif code_len == 4:
        if sub_3 not in x:
            print("ERROR")
            break
        sub_4 = x
        atc_code_dataframe = atc_code_dataframe.append({'atc_desc':x, 'code':sub_3}, ignore_index=True)
    elif code_len == 5:
        if sub_4 not in x:
            print("ERROR")
            break
        sub_5 = x
        atc_code_dataframe = atc_code_dataframe.append({'atc_desc':x, 'code':sub_4}, ignore_index=True)
    elif code_len == 7:
        if sub_5 not in x:
            print("ERROR")
            break
        atc_code_dataframe = atc_code_dataframe.append({'atc_desc':x, 'code':sub_5}, ignore_index=True)


# create set file format
atc_code_dataframe['code_format'] = atc_code_dataframe.code.apply(append_underscore_n)
atc_code_dataframe['atc_desc_format'] = atc_code_dataframe.atc_desc.apply(append_underscore_n)
atc_code_dataframe['code_format_2'] = atc_code_dataframe.code_format.str.slice(0,4) + '_' +  atc_code_dataframe.code_format.str.slice(4)
atc_code_dataframe['atc_desc_format_2'] = atc_code_dataframe.atc_desc_format.str.slice(0,4) + '_' +  atc_code_dataframe.atc_desc_format.str.slice(4)
atc_code_dataframe['SET'] = 'SET'
atc_code_dataframe['prefix'] = 'ATC_'
atc_code_dataframe['code_full'] = atc_code_dataframe.prefix + atc_code_dataframe.code_format_2
atc_code_dataframe['atc_desc_full'] = atc_code_dataframe.prefix + atc_code_dataframe.atc_desc_format_2

atc_code_dataframe


atc_code_name_list


# ## act def file


# create def file format
atc_code_def = pd.DataFrame({'code':atc_code_list,'code_name':atc_code_name_list})
atc_code_def['code_format'] = atc_code_def.code.apply(append_underscore_n)
atc_code_def['code_format_2'] = atc_code_def.code_format.str.slice(0,4) + '_' +  atc_code_def.code_format.str.slice(4)
atc_code_def['prefix'] = 'ATC_'
atc_code_def['code_full'] = atc_code_def.prefix + atc_code_def.code_format_2
atc_code_def['def_num'] = range(def_start_num,(def_start_num + len(atc_code_def)))
atc_code_def['DEF'] = 'DEF'
atc_code_def['empty'] = np.nan


atc_code_def


# create additional line for each code containing the description
atc_code_def_melted = atc_code_def.melt(id_vars=['code_full','def_num','DEF'], value_vars=['code_name','empty'])
atc_code_def_melted = atc_code_def_melted.sort_values(['def_num','variable'],ascending=[True, False])
atc_code_def_melted['code_and_desc'] = atc_code_def_melted.code_full
atc_code_def_melted.loc[atc_code_def_melted.value.isnull() == False,'code_and_desc'] = atc_code_def_melted.code_full + ': ' + atc_code_def_melted.value
atc_code_def_melted


# ## rambam codes def file

set_df[set_df['is_atc'] == False]


def_rmb_df = pd.DataFrame(data=list(set(set_df[set_df['is_atc'] == False].code_full)),columns=['code_full'])


def_rmb_start_num = def_start_num + len(atc_code_def)
def_rmb_df['def_num'] = range(def_rmb_start_num,(def_rmb_start_num + len(def_rmb_df)))
def_rmb_df['DEF'] = 'DEF'
def_rmb_df


# ## write to file

def write_dict(df, path, columns, first_line='SECTION	DRUG_ADMINISTERED_RATE,DRUG_BACKGROUND,DRUG_RECOMMENDED,DRUG_ADMINISTERED,DRUG_PRESCRIBED\n'):
    df.to_csv(path, sep='\t', columns=columns, index=False, header=False)
    with open(path,'r') as contents:
        save = contents.read()
    with open(path,'w') as contents:
        contents.write(first_line)
    with open(path,'a') as contents:
        contents.write(save)

write_dict(set_df, working_directory + 'dict.atc_sets_2', ['SET', 'code_full', 'atc_desc'])
write_dict(atc_code_def_melted, working_directory + 'dict.atc_defs_2', ['DEF','def_num', 'code_and_desc'])
write_dict(atc_code_dataframe, working_directory + 'dict.atc_sets_hierarchy', ['SET', 'code_full', 'atc_desc_full'])
write_dict(def_rmb_df, working_directory + 'dict.atc_defs_rambam', ['DEF','def_num', 'code_full'])



