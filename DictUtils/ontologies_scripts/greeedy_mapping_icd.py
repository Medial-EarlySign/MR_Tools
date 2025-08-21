import pandas as pd
import numpy as np
import argparse
import os

##########################################################################
# this script map icd-10 (or icd-9) codes with high hierarchy to all
# icd-9 codes (or icd-10) that any child of the high hierarchy code is mapped
##########################################################################

parser = argparse.ArgumentParser()
parser.add_argument('--input', default='/nas1/Work/Users/Eitan/dict10missing.csv', help='filepath for input file with code to map')
parser.add_argument('--input_icd', default=10, help='10 or 9, what is the icd ontology of the input?')
parser.add_argument('--output_path', default='/nas1/Work/Users/Eitan/', help='output path')

args = parser.parse_args()

# read input file
#################
df = pd.read_csv(args.input)

# df must have 'code' column
if 'code' not in df.columns:
    raise NameError("ERROR, input file must have column called 'code'")
    
# 'count' is an optional column, just for reporting
if 'count' not in df.columns:
    df['cont'] = np.nan
    
# code format should be ICD10_CODE:... or ICD9_CODE:...
if args.input_icd==10:
    code_is_OK = df.code.map(lambda x: x[:11] == 'ICD10_CODE:')
else:
    code_is_OK = df.code.map(lambda x: x[:10] == 'ICD9_CODE:')

if code_is_OK.sum()!=len(df):
    raise NameError("ERROR, check code format in input file")

df.code = df.code.replace('.','')

# read exsisted mapping
#######################
try:
    if args.input_icd==10:
        mapping = pd.read_csv('../Ontologies/ICD9_TO_ICD10/dicts/dict.set_icd9_2_icd10', sep='\t', names = ['SET', 'father', 'child'])
    else:
        mapping = pd.read_csv('../Ontologies/ICD10_TO_ICD9/dicts/dict.set_icd10_2_icd9', sep='\t', names = ['SET', 'father', 'child'])
except:
    raise NameError("ERROR, please run the script from MR/Tools/DictUtils/ontologies_scripts or check existed mapping file name")

# main loop on code length
##########################
df['ones'] = 1
mapping['ones'] = 1
df['just_code'] = df.code.map(lambda x: x.split(':')[1])
df['code_len'] = df.just_code.map(len)
res={}

for i in df.code_len.unique():
    df1 = df[df.code_len==i].copy()
    mapping['short_code'] = mapping.child.map(lambda x: x.split(':')[1][0:i])
    df1 = df1.merge(mapping[['ones', 'short_code', 'father', 'child']])
    df1 = df1[df1.just_code == df1.short_code]
    res[i] = df1.copy()
    
# solved
########
solved = pd.concat([res[i] for i in df.code_len.unique()])
solved['SET'] = 'SET'
f = os.path.join(args.output_path, 'dict.greedy_mapping') 
solved[['SET', 'father', 'code']].to_csv(f, index=False, header=False, sep='\t')

# not solved
############
not_solved = df[~df.code.isin(solved.code)].copy()

if args.input_icd==10:
    full_dict = pd.read_csv('../Ontologies/ICD10/dicts/dict.icd10', sep='\t', names=['DEF', 'DEF_NUM', 'code'])
else:
    full_dict = pd.read_csv('../Ontologies/ICD9/dicts/dict.icd9dx', sep='\t', names=['DEF', 'DEF_NUM', 'code'])
    full_dict = full_dict[~(full_dict.code.map(lambda x: '.' in x))]
    
not_solved = not_solved.merge(full_dict.drop_duplicates(subset=['code']), on='code', how='left')

not_solved_not_known = not_solved[not_solved.DEF_NUM.isna()].copy()
not_solved_not_known['DEF_NUM'] = 'new code, not in our dictionary'

full_dict = full_dict[full_dict.code.map(lambda x: 'DESC' in x)].drop_duplicates(subset='DEF_NUM')
full_dict.rename(columns={'code':'desc'}, inplace=True)

not_solved_known = not_solved[not_solved.DEF_NUM.notna()].copy()
not_solved_known = not_solved_known.merge(full_dict, on='DEF_NUM', how='left')

not_solved = pd.concat([not_solved_not_known, not_solved_known]) 

if len(not_solved) > 0:
    f = os.path.join(args.output_path, 'codes_still_without_mapping.csv')
    not_solved[['code', 'count', 'DEF_NUM', 'desc']].sort_values(by='count', ascending=False).to_csv(f, index=False)
    
# report
########
print('---------------------')
print('Input have', len(df), 'codes.')
print('Solved:', solved.code.nunique(), 'codes, with', len(solved), 'greedy mappings')
print('Not Solved:', len(not_solved), 'codes, where', len(not_solved_not_known), 'are also new codes')








    