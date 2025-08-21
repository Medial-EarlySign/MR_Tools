#!/usr/bin/env python
import pandas as pd
import med, argparse, os

parser = argparse.ArgumentParser(description="Create registry")
parser.add_argument("--rep", help="repo path", required=True)
parser.add_argument("--codes_list", help="codes list file name", required=True)
parser.add_argument("--codes_dir", help="codes list file path", required=True)
parser.add_argument("--sub_codes", help="list of sub codes files", default='')
parser.add_argument("--signal", default='DIAGNOSIS', help="signal name")
parser.add_argument("--output", help="output path", required=True)
parser.add_argument("--end_of_data", help="last date for controls", default=20230101)

args = parser.parse_args()

REP = args.rep
signal = args.signal
lut_codes_path = os.path.join(args.codes_dir, args.codes_list)
OUT = args.output
END_OF_DATA = args.end_of_data

fr = open(lut_codes_path,'r')
codes = list(filter(lambda x: len(x)>0, map(lambda x: x.strip(), fr.readlines())))
fr.close()

rep = med.PidRepository()
rep.read_all(REP, [], ['BDATE', signal])
lut = rep.dict.prep_sets_lookup_table(rep.dict.section_id(signal), codes)
sig = rep.get_sig(signal, translate=False)
bdate = rep.get_sig('BDATE').rename(columns={'val0':'bdate'})

cases = sig[(lut[sig.val0] != 0)].sort_values('time0').drop_duplicates(subset=['pid'])[['pid', 'time0']].rename(columns={'time0':'start_time'})
cases['end_time'] = 30000101
cases['value'] = 1
cases = cases[['pid', 'start_time', 'end_time', 'value']]

cases_cntrl = cases.copy()
cases_cntrl = cases_cntrl.set_index('pid').join(bdate.set_index('pid')).reset_index()

cases_cntrl['value'] = 0
cases_cntrl['end_time'] = cases_cntrl['start_time']
cases_cntrl['start_time'] = cases_cntrl['bdate']
cases_cntrl = cases_cntrl[['pid', 'start_time', 'end_time', 'value']]

# if the list of codes is splitted to sub groups, for each cases save the group
cases['diag'] = [[] for _ in range(cases.shape[0])] # start with empty list
if len(args.sub_codes) > 0:
    groups = args.sub_codes.split(',')
    for g in groups:
        fr = open(os.path.join(args.codes_dir, g + '.list'), 'r')
        codes = list(filter(lambda x: len(x) > 0, map(lambda x: x.strip(), fr.readlines())))
        fr.close()
        lut = rep.dict.prep_sets_lookup_table(rep.dict.section_id(signal), codes)
        sig = rep.get_sig(signal, translate=False)
        sig = sig[(lut[sig.val0] != 0)].sort_values('time0').drop_duplicates(subset=['pid'])[['pid', 'time0']].rename(columns={'time0':'group_time'})
        cases_g = cases[cases.pid.isin(sig.pid.tolist())].copy()
        cases_ng = cases[~cases.pid.isin(sig.pid.tolist())]
        cases_g = cases_g.merge(sig, on='pid')
        cases_g['diag'] = cases_g.apply(lambda r: r['diag'] + [g] if r['start_time']==r['group_time'] else r['diag'], axis=1)
        cases = pd.concat([cases_g.drop(columns='group_time'), cases_ng])

controls = bdate[~bdate['pid'].isin(cases['pid'])].copy()
controls['value'] = 0
controls = controls.rename(columns={'bdate':'start_time'})
controls['end_time'] = END_OF_DATA
controls = controls[['pid', 'start_time', 'end_time', 'value']]

full_reg = pd.concat([cases, cases_cntrl, controls], ignore_index=True)

# fix dates - should happen in load
def fix_date(df, col):
    df[col] = df[col].map(lambda x: x + 1 if str(x)[-2:]=='00' else x)
    df[col] = df[col].map(lambda x: x + 101 if str(x)[-4:-2]=='00' else x)
    return df
full_reg = fix_date(full_reg, 'start_time')
full_reg = fix_date(full_reg, 'end_time')

full_reg.to_csv(OUT, index=False, header=False, sep='\t')
print(f'Wrote {OUT}')