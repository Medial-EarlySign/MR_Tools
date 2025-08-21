import subprocess
import pandas as pd
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True, help='all comperator preds')
parser.add_argument('--cohort', type=str, required=True, help='reference cohort')
parser.add_argument('--output', type=str, required=True, help='output path')

args, unparsed = parser.parse_known_args()

comperator = pd.read_csv(args.input,sep='\t')
cohort = pd.read_csv(args.cohort,sep='\t')

print('length of comperator preds file', len(comperator))
print('length of cohort file', len(cohort))

ret_result = comperator.drop(columns=['outcome', 'outcomeTime']).merge(cohort[['id', 'time', 'outcome', 'outcomeTime']], on=['id', 'time'], how='inner')
ret_result = ret_result[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'pred_0']]
ret_result = ret_result.sort_values(['id', 'time']).reset_index(drop=True)

if len(ret_result) < len(cohort):
	print('NO comperator preds for', len(cohort) - len(ret_result), 'samples')

#if (len(ret_result) / len(cohort) < 1-0.01):
#	raise NameError('Dropped too many samples, size missmatched %2.1f%%'%(100-100*len(ret_result) / len(cohort)))

ret_result.to_csv(args.output, sep='\t', index=False)
