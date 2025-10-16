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

#read predictions
ref = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'reference.preds'), sep='\t')
test = pd.read_csv(os.path.join(WORK_DIR, 'compare', '3.test_cohort.preds'), sep='\t')

ref['pred_1'] = round(ref['pred_0'] * 2, 2) / 2
test['pred_1'] = round(test['pred_0'] * 2, 2) / 2

#bring age

mat = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'), usecols=['outcome', 'time', 'str_attr_original_id', 'Age'])
mat.rename(columns={'str_attr_original_id':'id'}, inplace=True)

ref = ref.merge(mat[mat.outcome == 0], on=['id', 'time'], how='inner')
test = test.merge(mat[mat.outcome == 1], on=['id', 'time'], how='inner')

#output - all in
res = dict()
res['Reference'] = ref.groupby('pred_1').id.count().reset_index().rename(columns={'id':'count'})
res['Reference']['count'] = 100 * res['Reference']['count'] / res['Reference']['count'].sum()

res['Test'] = test.groupby('pred_1').id.count().reset_index().rename(columns={'id':'count'})
res['Test']['count'] = 100 * res['Test']['count'] / res['Test']['count'].sum()

plot_graph(res, os.path.join(WORK_DIR, 'compare', 'compare_scores.html'), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))

#output, per age range

df = pd.DataFrame(columns = ['source', 'age_range', 'count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']).set_index( ['source', 'age_range'])

for i in range(0, 120, 5):
    i_ref = ref[ref.Age.between(i, i+4)]
    i_test = test[test.Age.between(i, i+4)]

    if len(i_test) > 100:
        res = dict()
        res['Reference'] = i_ref.groupby('pred_1').id.count().reset_index().rename(columns={'id':'count'})
        res['Reference']['count'] = 100 * res['Reference']['count'] / res['Reference']['count'].sum()
        
        res['Test'] = i_test.groupby('pred_1').id.count().reset_index().rename(columns={'id':'count'})
        res['Test']['count'] = 100 * res['Test']['count'] / res['Test']['count'].sum()
        
        plot_graph(res, os.path.join(WORK_DIR, 'compare', 'score_dist_by_age', 'score_in_age_range_' + str(i) + '_' + str(i+4) + '.html'), mode='bar', plotly_js_path = os.path.join('..', '..', 'js', 'plotly.js'))

        df.loc[('ref', str(i) + '_' + str(i+4)), df.columns] = i_ref.pred_0.describe().T
        df.loc[('test', str(i) + '_' + str(i+4)), df.columns] = i_test.pred_0.describe().T
        
df.round(3).to_csv(os.path.join(WORK_DIR, 'compare', 'score_dist_by_age', 'compare_score_dist_by_age.tsv'), sep='\t')
