#!/usr/bin/env python
import argparse
import pandas as pd
import med

parser=argparse.ArgumentParser(description='filter')
parser.add_argument("--rep",help="the repository",required=True, type=str)
parser.add_argument("--input_samples",help="the file path to full input MedSamples without filters",required=True, type=str)
parser.add_argument("--signal_name",help="the name of the signal to filter by",default='DIAGNOSIS', type=str)
parser.add_argument("--filter_file",help="the file path to list of diagnosis codes to filter if they happend in the past",required=True, type=str)
parser.add_argument("--output_samples",help="the file path to output samples with exclusion attribute columns",required=True, type=str)

args = parser.parse_args()

samples=pd.read_csv(args.input_samples, sep='\t')
all_ids=list(set(samples['id']))
fr=open(args.filter_file, 'r')
lines=fr.readlines()
fr.close()
sets=list(filter(lambda x: len(x)>0, map(lambda x:x.strip(), lines)))

rep=med.PidRepository()
rep.read_all(args.rep, all_ids, [ args.signal_name ])

lut = rep.dict.prep_sets_lookup_table(rep.dict.section_id(args.signal_name),sets)

sig=rep.get_sig(args.signal_name, pids=all_ids, translate=False)
#keep only exclusion events - and keep first event for each patient
sig = sig[(lut[sig.val0]!=0)].sort_values(['pid', 'time0']).drop_duplicates(subset=['pid']).reset_index(drop=True)[['pid', 'time0']].rename(columns={'time0':'first_time'})
samples=samples.set_index('id').join(sig.rename(columns={'pid':'id'}).set_index('id'), how='left').reset_index()
samples.loc[samples.first_time.isnull(), 'first_time']= 30000101

#mark samples that has "first_time" before "time" to exclude
samples['attr_exclude_reason']=''
samples['attr_exclude_date']=''
samples.loc[samples['first_time']<=samples['time'], 'attr_exclude_reason']= 'Past_Diagnosis'
samples.loc[samples['first_time']<=samples['time'], 'attr_exclude_date']= samples.loc[samples['first_time']<=samples['time'], 'first_time']
samples=samples.drop(columns=['first_time'])
samples=samples[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'attr_exclude_reason', 'attr_exclude_date']]

samples.to_csv(args.output_samples, sep='\t', index=False)
