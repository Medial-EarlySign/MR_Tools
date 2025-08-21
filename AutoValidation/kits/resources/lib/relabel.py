#!/usr/bin/env python
import pandas as pd
import med, argparse

#Assumes all patients are members
parser = argparse.ArgumentParser(description = "Relabel samples")
#Assumes cases has "start_time" with diagnosis code. contros has "end_time" as end of follow up
parser.add_argument("--registry", help="registry path", required=True)
parser.add_argument("--samples" ,help="input samples to relabel", required=True)
parser.add_argument('--follow_up_controls', type=int, required=True, help='follow up for control in days')
parser.add_argument('--time_window_case_minimal_before', type=int, default=0, help='minimal time before case in days')
parser.add_argument('--time_window_case_maximal_before', type=int, required=True, help='maximal time before case in days')
parser.add_argument('--future_cases_as_control', type=int, required=True, help='should we consider cases as control more than cases_max_time_before_cancer years?')
parser.add_argument("--output", help="output sampples after relabeling", required=True)
parser.add_argument("--output_dropout", help="output samples excluded", required=True)
parser.add_argument("--sub_codes", help="list of sub codes groups", default='')

args = parser.parse_args()

samples = pd.read_csv(args.samples, sep='\t')
print(f'Input has {len(samples)} samples')
registry = pd.read_csv(args.registry, sep='\t', names=['id', 'start_time', 'end_time', 'value', 'diag'])
print(f'registry has {registry.id.nunique()} IDs with {registry[registry.value==1].id.nunique()} cases')
dropout = pd.DataFrame({'EVENT_FIELDS':[], 'id':[], 'time':[], 'outcome':[], 'outcomeTime':[], 'split':[], 'str_attr_reason':[]})
dropout_ls = [dropout]
samples['id_time'] = samples['id'].astype(str)+'_' + samples['time'].astype(str)

reg_cases = registry[registry['value']>0].reset_index(drop=True)
potential_cases = samples.set_index('id').join(reg_cases[['id', 'start_time' ,'diag']].set_index('id')).reset_index()
potential_cases['start_time_dt'] = pd.to_datetime(potential_cases['start_time'], format='%Y%m%d')
potential_cases['time_dt'] = pd.to_datetime(potential_cases['time'], format='%Y%m%d')
potential_cases['time_win'] = (potential_cases['start_time_dt']-potential_cases['time_dt']).dt.days
cases = potential_cases[(potential_cases['time_win'] >= args.time_window_case_minimal_before) & \
                                (potential_cases['time_win'] <= args.time_window_case_maximal_before)].reset_index(drop=True).copy()
far_cases = potential_cases[potential_cases['time_win'] > args.time_window_case_maximal_before].reset_index(drop=True).copy()
close_cases = potential_cases[(potential_cases['time_win'] >= 0) & (potential_cases['time_win'] < args.time_window_case_minimal_before)].reset_index(drop=True).copy()
after_cases = potential_cases[potential_cases['time_win'] < 0].reset_index(drop=True).copy()
far_cases['outcomeTime'] = far_cases['start_time']
close_cases['outcomeTime'] = close_cases['start_time']
after_cases['outcomeTime'] = after_cases['start_time']

cases['outcome'] = 1
cases['outcomeTime'] = cases['start_time']
#remove those samples from further evaluation:
samples = samples[~samples['id_time'].isin(cases['id_time'])].reset_index(drop=True)
samples = samples[~samples['id_time'].isin(far_cases['id_time'])].reset_index(drop=True)
samples = samples[~samples['id_time'].isin(close_cases['id_time'])].reset_index(drop=True)
samples = samples[~samples['id_time'].isin(after_cases['id_time'])].reset_index(drop=True)

after_cases['str_attr_reason'] = 'cases, sample after diagnosis'
after_cases = after_cases[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason', 'diag']]
dropout_ls.append(after_cases)

close_cases['str_attr_reason'] = 'cases, too_close_to_outcome'
close_cases = close_cases[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason', 'diag']]
dropout_ls.append(close_cases)

cases = cases[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'diag']]
if args.future_cases_as_control:
    far_cases['outcome'] = 0
    ex_follow_up = far_cases[far_cases['time_win']<args.follow_up_controls].reset_index(drop=True).copy()
    ex_follow_up['str_attr_reason'] = 'cases, case_not_enough_follow_up_to_be_control'
    ex_follow_up = ex_follow_up[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason', 'diag']]
    dropout_ls.append(ex_follow_up)
    far_cases = far_cases[far_cases['time_win']>=args.follow_up_controls].reset_index(drop=True)
    far_cases = far_cases[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split']]
    #Check minimal followup till start_time:
    
    cases = pd.concat([cases, far_cases], ignore_index=True)
else:
    far_cases['str_attr_reason'] = 'cases, too_far_from_outcome'
    far_cases = far_cases[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason', 'diag']]
    dropout_ls.append(far_cases)
    
#continue for controls analysis:
#1. take as controls all patients with enough followup:
reg_controls = registry[registry['value']<1].reset_index(drop=True)
potential_controls = samples.set_index('id').join(reg_controls[['id', 'start_time', 'end_time']].set_index('id')).reset_index()
potential_controls = potential_controls[potential_controls['start_time']<= potential_controls['time']].reset_index(drop=True).copy()

potential_controls['end_time_dt'] = pd.to_datetime(potential_controls['end_time'], format='%Y%m%d')
potential_controls['time_dt'] = pd.to_datetime(potential_controls['time'], format='%Y%m%d')
potential_controls['time_win'] = (potential_controls['end_time_dt']-potential_controls['time_dt']).dt.days

controls = potential_controls[potential_controls['time_win'] >= args.follow_up_controls].reset_index(drop=True)
controls['outcome'] = 0
controls['outcomeTime'] = controls['end_time']
#Remove from samples
samples = samples[~samples['id_time'].isin(controls['id_time'])].reset_index(drop=True)

#Mark not enough followup for controls
dropped_controls = potential_controls[potential_controls['time_win'] < args.follow_up_controls].reset_index(drop=True).copy()
dropped_controls['outcome'] = 0
dropped_controls['outcomeTime'] = dropped_controls['end_time']
dropped_controls['str_attr_reason'] = 'controls, not_enough_follow_up'
controls = controls[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split']]

samples = samples[~samples['id_time'].isin(dropped_controls['id_time'])].reset_index(drop=True)
dropped_controls = dropped_controls[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason']]
dropout_ls.append(dropped_controls)

#Mark all what's left in controls: not in registry or no registry before prediction time
samples['outcome'] = -1
samples['outcomeTime'] = -1
samples['str_attr_reason'] = 'not_in_registry'
samples = samples[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'str_attr_reason']]
dropout_ls.append(samples)

#finish
dropout = pd.concat(dropout_ls, ignore_index=True).sort_values(['id', 'time']).reset_index(drop=True)
dropout.to_csv(args.output_dropout, sep='\t', index=False)
print(f'Wrote {len(dropout)} in {args.output_dropout}')
print(dropout.str_attr_reason.value_counts())
print('')

if len(args.sub_codes) > 0:
    groups = args.sub_codes.split(',')
    for g in groups:
        samples = pd.concat([controls, cases[cases.diag.map(lambda d: g in d)]], ignore_index=True).sort_values(['id', 'time']).reset_index(drop=True)
        samples.drop(columns='diag', inplace=True)
        fout = args.output + '.' + g
        print(f'Wrote {len(samples)} samples in {fout} with {samples[samples.outcome==1].id.nunique()} unique cases and {samples[samples.outcome==0].id.nunique()} unique controls')
        samples.to_csv(fout, sep='\t', index=False)

final_samples = pd.concat([controls, cases], ignore_index=True).sort_values(['id', 'time']).reset_index(drop=True)
final_samples.drop(columns='diag', inplace=True)
final_samples.to_csv(args.output, sep='\t', index=False)
print(f'Wrote {len(final_samples)} in {args.output} with {final_samples[final_samples.outcome==1].id.nunique()} unique cases and {final_samples[final_samples.outcome==0].id.nunique()} unique controls')