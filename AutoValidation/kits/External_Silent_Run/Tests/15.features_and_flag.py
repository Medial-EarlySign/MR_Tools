#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS = ['WORK_DIR', 'CMP_FEATURE_RES', 'TOP_EXPLAIN_PERCENTAGE']
DEPENDS=[] # Dependency tests
# End Edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import pandas as pd

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:
CUTOFF = 100-int(TOP_EXPLAIN_PERCENTAGE)

print(f'Please refer to features_and_flag directory to see feature distribution among flagged and unflagged in reference and tested dataset')

def fix_feat_names1(s):
    categs=['ICD9_CODE', 'ICD10_CODE', 'ATC_CODE']
    for c in categs:
        s=s.replace(c+':', c+'_')
    return s
def fix_feat_names2(s):
    categs=['ICD9_CODE', 'ICD10_CODE', 'ATC_CODE']
    for c in categs:
        s=s.replace(c+'_', c+':')
    return s

#obj is single dataframe with 2 columns, or dict of dataaframes with 2 cols each

# prep
output = os.path.join(WORK_DIR, 'features_and_flag')
os.makedirs(output, exist_ok=True)

feat_res = CMP_FEATURE_RES.split(',')
features = list(map(lambda x: fix_feat_names2(fix_feat_names1(x).split(':')[0]), feat_res))
reso = list(map(lambda x: float(x.split(':')[-1]), feat_res))

# read feature matrix (with and without imputation/normalization)
df = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'))
df_non_norm = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity_non_norm.matrix'))
df_non_norm = df_non_norm.merge(df[['id', 'time', 'str_attr_original_id']], on=['id', 'time'], how='inner')

# prepare for later merge with scores
df = df.drop(columns='id').rename(columns={'str_attr_original_id':'id'})
df_non_norm = df_non_norm.drop(columns='id').rename(columns={'str_attr_original_id':'id'})

# read scores
test_preds = pd.read_csv(os.path.join(WORK_DIR, 'compare', '3.test_cohort.preds'), sep='\t')
ref_preds = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'reference.preds'), sep='\t')

# resolution
exact_names = []
for i,feat in enumerate(features):
    res = dict()
    exact_name = list(filter(lambda x: x.find(feat)>=0, df.columns))
    col = exact_name[0]
    exact_names = exact_names + [col]
    df[col] = (df[col].astype(float)/reso[i]).astype(int).astype(float)*reso[i]
    df_non_norm[col] = (df_non_norm[col].astype(float)/reso[i]).astype(int).astype(float)*reso[i]
    
df = df[['id', 'time'] + exact_names]
df_non_norm = df_non_norm[['id', 'time'] + exact_names]

# split the data
test = test_preds[['id', 'time', 'pred_0']].merge(df, on=['id', 'time'], how='inner')
ref = ref_preds[['id', 'time', 'pred_0']].merge(df, on=['id', 'time'], how='inner')
test_nn = test_preds[['id', 'time', 'pred_0']].merge(df_non_norm, on=['id', 'time'], how='inner')
ref_nn = ref_preds[['id', 'time', 'pred_0']].merge(df_non_norm, on=['id', 'time'], how='inner')

test_F = test[test.pred_0 >= np.percentile(test.pred_0, CUTOFF)].copy()
test_NF = test[test.pred_0 < np.percentile(test.pred_0, CUTOFF)].copy()
ref_F = ref[ref.pred_0 >= np.percentile(ref.pred_0, CUTOFF)].copy()
ref_NF = ref[ref.pred_0 < np.percentile(ref.pred_0, CUTOFF)].copy()

test_F_nn = test_nn[test_nn.pred_0 >= np.percentile(test_nn.pred_0, CUTOFF)].copy()
test_NF_nn = test_nn[test_nn.pred_0 < np.percentile(test_nn.pred_0, CUTOFF)].copy()
ref_F_nn = ref_nn[ref_nn.pred_0 >= np.percentile(ref_nn.pred_0, CUTOFF)].copy()
ref_NF_nn = ref_nn[ref_nn.pred_0 < np.percentile(ref_nn.pred_0, CUTOFF)].copy()

# basic stat - % miss_value and moments on the rest
###################################################
def get_stat(dft, dfr, dft_nn, dfr_nn):
    res = pd.DataFrame(columns=['mean_ref', 'std_ref', 'miss%_ref', 'mean_test', 'std_test', 'miss%_test'])
    for col in exact_names:
        tmp = dft_nn[['id', 'time', col]].copy()
        tmp = tmp[tmp[col] != -65336]
        res.loc[col, 'miss%_test'] = round(100 * (1 - len(tmp) / len(dft_nn)),2)
        tmp = dft[['id', 'time', col]].merge(tmp[['id', 'time']], on=['id', 'time'], how='inner')
        res.loc[col, 'mean_test'] = round(tmp[col].mean(),3)
        res.loc[col, 'std_test'] = round(tmp[col].std(),3)
        
        tmp = dfr_nn[['id', 'time', col]].copy()
        tmp = tmp[tmp[col] != -65336]
        res.loc[col, 'miss%_ref'] = round(100 * (1 - len(tmp) / len(dfr_nn)),2)
        tmp = dfr[['id', 'time', col]].merge(tmp[['id', 'time']], on=['id', 'time'], how='inner')
        res.loc[col, 'mean_ref'] = round(tmp[col].mean(),3)
        res.loc[col, 'std_ref'] = round(tmp[col].std(),3)
    return res

s1 = get_stat(test_F, ref_F, test_F_nn, ref_F_nn)
s1.columns = s1.columns + '_flagged'

s2 = get_stat(test_NF, ref_NF, test_NF_nn, ref_NF_nn)
s2.columns = s2.columns + '_not_flagged'

res = pd.concat([s1, s2], axis=1)
res.to_csv(os.path.join(output, 'features_and_flag.csv'))

# helper function
def get_ratio(total, df, col):
    
    total_counts = total[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'total_count'})
    # remove rare values accountd for 1% of the samples
    total_counts = total_counts.sort_values(by='total_count', ascending=False)
    total_counts['s'] = total_counts.total_count.cumsum()
    bar = total_counts.total_count.sum() * 0.97
    total_counts = total_counts[total_counts.total_count < bar].sort_values(by=col)
    
    counts = df[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'count'})
    
    ret = total_counts.merge(counts, on=col, how='left').fillna(0)
    ret['count'] = 100 * ret['count'] / ret['total_count']
    ret=ret.rename(columns={'count':'percentage(%)'})
    ret.drop(columns=['total_count', 's'], inplace=True)
    
    return ret

# plot graphs
#############
for col in exact_names:
    res = dict()
    res['Test_Flagged'] = test_F[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'count'})
    res['Test_Not_Flagged'] = test_NF[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'count'})
    res['Ref_Flagged'] = ref_F[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'count'})
    res['Ref_Not_Flagged'] = ref_NF[[col, 'id']].groupby(col).count().reset_index().rename(columns={'id':'count'})
    for l in ['Test_Flagged', 'Test_Not_Flagged', 'Ref_Flagged', 'Ref_Not_Flagged']:
        res[l]['count'] = 100 * res[l]['count'] / res[l]['count'].sum()
        res[l]=res[l].rename(columns={'count':'percentage(%)'})
    plot_graph(res, os.path.join(output, '%s.html'%(col)), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))

    res1 = dict()
    res1['Test_Flagged_Ratio'] = get_ratio(test, test_F, col)
    res1['Test_Not_Flagged_Ratio'] = get_ratio(test, test_NF, col)    
    res1['Ref_Flagged_Ratio'] = get_ratio(ref, ref_F, col)
    res1['Ref_Not_Flagged_Ratio'] = get_ratio(ref, ref_NF, col)
    plot_graph(res1, os.path.join(output, '%s_ratio.html'%(col)), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))
    