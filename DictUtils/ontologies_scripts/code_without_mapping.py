import pandas as pd
import numpy as np
import argparse
import os

################################################################
# this script get a list of icd-10 (or icd-9) codes
# and find the codes that no mapping to icd-9 (or icd-10) exists
################################################################

parser = argparse.ArgumentParser()
parser.add_argument('--input', default='/nas1/Work/Users/Eitan/estonia_missing_codes/missing_codes_pr9.csv', help='filepath for input file with codes to checkfor exsuisted mapping')
parser.add_argument('--input_icd', default=9, help='10 or 9, what is the icd ontology of the input?')
parser.add_argument('--output_path', default='/nas1/Work/Users/Eitan/estonia_missing_codes/', help='output path')

args = parser.parse_args()

# read input file
#################
df = pd.read_csv(args.input)

# df must have 'code' column
if 'code' not in df.columns:
    raise NameError("ERROR, input file must have column called 'code'")
       
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

# read exsisted sets
####################
if args.input_icd==10:
    sets = pd.read_csv('../Ontologies/ICD10/dicts/dict.set_icd10', sep='\t', names = ['SET', 'father', 'child'])
else:
    sets = pd.read_csv('../Ontologies/ICD9/dicts/dict.set_icd9dx', sep='\t', names = ['SET', 'father', 'child'])


# build the set of codes that are currently mapped
##################################################

# codes with direct mappigs
mapped_codes = set(mapping.child)

# codes with mapping of father in ontonlogy set definition
n = len(mapped_codes)
n1 = 0

while n1 < n:
    n1 = n
    sets_mapped = sets[sets.father.isin(mapped_codes)]
    new_mapped_codes = set(sets_mapped.child)
    mapped_codes = mapped_codes.union(new_mapped_codes)
    n = len(mapped_codes)
    # print(n)

# find the missing codes and save
#################################

n = len(df)
df = df[~df.code.isin(mapped_codes)]
print('Out of', n, 'codes, found', len(df), 'codes without mapping')
f = os.path.join(args.output_path, 'codes_without_mapping.csv') 
df.to_csv(f, index=False, sep='\t')








    