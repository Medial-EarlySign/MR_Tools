#!/usr/bin/env python
import pandas as pd
import med, argparse

parser = argparse.ArgumentParser(description = "merge")

parser.add_argument("--input", help="input cohort file", required=True)
parser.add_argument("--output", help="output preds file", required=True)
parser.add_argument("--eligible_with_preds" ,help="file with outcomes and just eligible samples", required=True)

args = parser.parse_args()

samples = pd.read_csv(args.input, sep='\t')
print('Adding preds to', args.input)
print(f'Input has {len(samples)} samples')

eligible = pd.read_csv(args.eligible_with_preds, sep='\t')

output = samples.merge(eligible[['id', 'time', 'pred_0']], on=['id', 'time'], how='inner')
print(f'Output has {len(output)} eligible samples')
print('')

output.to_csv(args.output, index=False, sep='\t')

