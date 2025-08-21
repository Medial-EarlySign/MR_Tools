import os, sys, math
import pandas as pd
import numpy as np

from PY_Helper import *

init_env(sys.argv, locals())

#Test for parameters
REQ_PARAMETERS = ['WORK_DIR']
res = test_existence(locals(), REQ_PARAMETERS, test_name='compare_scores.sh')
if not(res):
    sys.exit(1)

#read sample
sample = pd.read_csv(os.path.join(WORK_DIR, 'compare.no_overfitting', 'labeled_weights.preds'), sep='\t')

#bring age and gender

mat = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'), usecols=['outcome', 'time', 'str_attr_original_id', 'Age', 'Gender'])
mat = mat[mat.outcome == 0]
mat.drop(columns=['outcome'], inplace=True)
mat.rename(columns={'str_attr_original_id':'id'}, inplace=True)

sample = sample.merge(mat, on=['id', 'time'], how='inner')

# calculate incidence in the sample

sample['ag'] = 45 + ((sample.Age - 44.5) / 5).astype(int) * 5
sample.loc[sample.ag==75, 'ag'] = 70

tmp = sample.groupby(['ag', 'Gender', 'outcome']).attr_weight.sum().unstack()
tmp.columns = ['ctrls', 'cases']

tmp['bin'] = tmp['ctrls'] + tmp['cases']
tmp['rate'] = 100000 * tmp['cases'] / tmp['bin']

# target rate
# source: https://seer.cancer.gov/statistics-network/explorer/application.html?site=20&data_type=1&graph_type=3&compareBy=sex&chk_sex_3=3&chk_sex_2=2&rate_type=2&race=1&advopt_precision=1&advopt_show_ci=on&hdn_view=0

ir = [{'ag':45, 'Gender':1, 'target_rate': 39.1},
      {'ag':45, 'Gender':2, 'target_rate': 31.9},
      {'ag':50, 'Gender':1, 'target_rate': 72.0},
      {'ag':50, 'Gender':2, 'target_rate': 55.6},
      {'ag':55, 'Gender':1, 'target_rate': 81.2},
      {'ag':55, 'Gender':2, 'target_rate': 54.9},
      {'ag':60, 'Gender':1, 'target_rate': 106.7},
      {'ag':60, 'Gender':2, 'target_rate': 69.9},
      {'ag':65, 'Gender':1, 'target_rate': 138.4},
      {'ag':65, 'Gender':2, 'target_rate': 93.2},
      {'ag':70, 'Gender':1, 'target_rate': 161.0},
      {'ag':70, 'Gender':2, 'target_rate': 115.0}
     ]
ir = pd.DataFrame(ir).set_index(['ag', 'Gender'], drop=True)

tmp = tmp.join(ir)
tmp['target_cases'] = tmp['target_rate'] * tmp['bin'] / 100000
tmp['target_ctrls'] = tmp['bin'] - tmp['target_cases']

tmp['ctrls_factor'] = tmp['target_ctrls'] / tmp['ctrls']
tmp['cases_factor'] = tmp['target_cases'] / tmp['cases']

print('########## incidence in labeled sample - original vs target')
print(tmp)

# update the sample
sample = sample.merge(tmp.reset_index()[['ag', 'Gender', 'cases_factor', 'ctrls_factor']], on=['ag', 'Gender'])
sample['attr_weight'] = sample.apply(lambda r: r['attr_weight'] * r['ctrls_factor'] if r['outcome']==0 else r['attr_weight'] * r['cases_factor'], axis=1)


# save
sample[['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'pred_0', 'attr_weight']].sort_values(by=['id', 'time']).to_csv(os.path.join(WORK_DIR, 'compare.no_overfitting', 'labeled_weights_calibrated.preds'), sep='\t', index=False)

sample[sample.Age.between(45,54)][['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'pred_0', 'attr_weight']].sort_values(by=['id', 'time']).to_csv(os.path.join(WORK_DIR, 'compare.no_overfitting', 'labeled_weights_calibrated.45_55.preds'), sep='\t', index=False)

sample[sample.Age.between(55,64)][['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'pred_0', 'attr_weight']].sort_values(by=['id', 'time']).to_csv(os.path.join(WORK_DIR, 'compare.no_overfitting', 'labeled_weights_calibrated.55_65.preds'), sep='\t', index=False)

sample[sample.Age.between(65,75)][['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split', 'pred_0', 'attr_weight']].sort_values(by=['id', 'time']).to_csv(os.path.join(WORK_DIR, 'compare.no_overfitting', 'labeled_weights_calibrated.65_75.preds'), sep='\t', index=False)
