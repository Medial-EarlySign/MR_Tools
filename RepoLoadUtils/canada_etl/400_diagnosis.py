from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import re
import glob, string 
from medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--input_folder', default='/server/Data/canada_122017/IQIVA/')
parser.add_argument('--output_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

df = pd.DataFrame()
for f in glob.glob(args.input_folder + '/*/Transaction_-_Diagnosis.txt'):
    cur = read_file(f, sep = '|', limit_records=args.limit_records, quoting=3)
    cur.loc[:, 'filename'] = f
    df = pd.concat([df, cur])

eprint("before removing illegal patients", df.shape)
legal_pats = read_file(args.output_folder + "demographics_data", sep = '\t', names = ['pid', 'sig', 'val'])
df = pd.merge(df, legal_pats[['pid']].drop_duplicates(), left_on = 'PAT_ID', right_on = 'pid')
eprint("after removing illegal patients", df.shape)
    
eprint(df[df.DIAG_CD != 'RWE_UNK'].shape[0], 'non-RWE_UNK records before extracting codes of common diseases')


pattern_rectum = "rectosigmoid|sigmoid|rectal|rectum"
pattern_colon = "colon|appendix|bowel|caecun|cecum|colorectal|intstine|splenic"
pattern2 = "adenocarcinoma|cancer|carcinoma|neoplasm|tumor|tumour|(\s|^)ca(\s|$)"
pattern3 = 'fhx|family\shx|fam\shx|family\shistory|(\s|^)FH(\s|$)|fh\sfam|father|mother|brother|sister|screening|\sago|husband|dad(\s|$)'

pattern_rectum = re.compile(pattern_rectum)
pattern_colon = re.compile(pattern_colon)
pattern2 = re.compile(pattern2)
pattern3 = re.compile(pattern3)

def translate_to_code(x):
    x = str(x)
    if x in ["Hypertension", "Hypertensive Disease - Essential, benign hypertension", "HTN", "hypertension"]:
        return "401"
    if x in ["Diabetes Type II", "Diabetes Mellitus (Including Complications)", "DM"]:
        return "250"
    if "pulmonary" in x.lower() and "embol" in x.lower():
        return "415"
    if "pancreatitis" in x.lower():
        return "577"
    if "fatty" in x.lower() and "liver" in x.lower():
        return "571"
    if pattern_colon.search(x.lower()) and pattern2.search(x.lower()) and not pattern3.search(x.lower()):
        eprint("153!", x)
        return "153"
    if pattern_rectum.search(x.lower()) and pattern2.search(x.lower()) and not pattern3.search(x.lower()):
        eprint("154!", x)
        return "154"
    
    return "RWE_UNK"

idx = (df.DIAG_CD == 'RWE_UNK')
df.loc[idx, 'DIAG_CD'] = df[idx].DIAGNOSIS_DESCRIPTION.apply(translate_to_code)
df = df[df.DIAG_CD != 'RWE_UNK']
eprint(df.shape[0], 'non-RWE_UNK records after extracting codes of common diseases')

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

tbl = string.maketrans(" \t", '__')
dict_records = []
serial_id = 0
def print_dict(x):
    global serial_id
    if is_number(x['DIAG_CD']) and int(x['DIAG_CD']) < 10000:
        my_serial_id = int(x['DIAG_CD'])
    else:
        my_serial_id = 10000 + serial_id
        serial_id += 1
    dict_records.append({"def": "DEF", "order": 1, "my_serial_id": my_serial_id, "val": "ICD-9:{0}".format(x['DIAG_CD'])})    
    dict_records.append({"def": "DEF", "order": 2, "my_serial_id": my_serial_id, "val": x['DIAGNOSIS_DESCRIPTION'].translate(tbl)})
    dict_records.append({"def": "DEF", "order": 3, "my_serial_id": my_serial_id, "val": "frequency:{0}".format(x['PAT_ID'],)})
df.groupby('DIAG_CD').agg({'PAT_ID': 'nunique', 'DIAGNOSIS_DESCRIPTION': 'max'}).reset_index().apply(print_dict, axis = 1)
out_dict = pd.DataFrame(dict_records).sort_values(['my_serial_id', 'order'])
s = out_dict.to_csv(columns=['def', 'my_serial_id', 'val'], index=False, header=False, sep = '\t') 
with open(args.output_folder + '/dicts/dict.diag_defs', 'w') as f:
    print("SECTION\tRC", file=f)
    print(s, file=f)
    eprint("writing {0} into {1}".format(out_dict.shape, args.output_folder + '/dicts/dict.RC_defs'))

output_records = []
def print_data(x):
    output_records.append({"pid": x['PAT_ID'], "sig": "RC", "date": x['EVENT_DAY'], "val": "ICD-9:{0}".format(x['DIAG_CD']), "desc": x['DIAGNOSIS_DESCRIPTION']})
df.apply(print_data, axis = 1)


out_df = pd.DataFrame(output_records)
write_for_sure(out_df.sort_values(['pid', 'date']), args.output_folder + '/diag_data', columns=['pid', 'sig', 'date', 'val', 'desc'], index=False, header=False, sep = '\t') 
