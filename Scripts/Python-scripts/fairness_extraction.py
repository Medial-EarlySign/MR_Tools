#!/usr/bin/env python
import os
import re
import pandas as pd
import argparse
from scipy.stats import chi2_contingency

def reformat_token(s):
    if len(s.split(':'))!=2:
        raise Exception(f'Wrong token ":" delimeter should apear once in "{s}"')
    param_name, par_rng= s.split(':')
    low, high = par_rng.split(',')
    
    return param_name + ':' + '%2.3f'%(float(low)) + ',' + '%2.3f'%(float(high)) 

def transform_from_bt_filter_to_cohrt(s):
    s=';'.join(list(map(lambda x: reformat_token(x) , s.split(';'))))
    s=s.replace(',', '-').replace(';', ',')
    
    return s

parser = argparse.ArgumentParser(description = "Get Fairness")
parser.add_argument("--bt_report", help="bootstrap report path", required=True)
parser.add_argument("--bt_cohort", help="cohort filter", default='')
parser.add_argument("--output", help="output directory",  default='.')
parser.add_argument("--cutoffs_pr", help="cutoffs",  default=[3], nargs='+')
parser.add_argument("--filter_whitelist_regex", help="regex to include groups",  default='')
parser.add_argument("--filter_blacklist_regex", help="regex to remove groups",  default='')

args = parser.parse_args()
args.cutoffs_pr = list(map(lambda x: float(x), args.cutoffs_pr))

df = pd.read_csv(args.bt_report, sep='\t', low_memory=False)
if len(df) == 0:
    raise Exception(f'Empty bootstrap file {args.bt_report}')
if len(args.bt_cohort) == 0:
    # Take shortest as bt_filter
    all_cohorts = list(df['Cohort'].unique())
    all_cohorts = sorted(all_cohorts, key=lambda x: len(x))
    bt_filter = all_cohorts[0]
    print(f'No bt_cohort - will use all bootstrap cohorts in the file with "{bt_filter}"')
else:
    bt_filter = transform_from_bt_filter_to_cohrt(args.bt_cohort)

base_cohort = bt_filter
if len(bt_filter) > 0 and len(df[df['Cohort']==bt_filter]) == 0:
    # Try other order:
    all_tokens = bt_filter.split(',')
    all_cohorts_before = list(df['Cohort'].unique())
    for token in all_tokens:
        df = df[(df['Cohort'].str.contains(token))].reset_index(drop=True)
    all_cohorts = list(df['Cohort'].unique())
    if (len(all_cohorts)==0):
        print('Cohorts:\n<{all_cohorts_print}>'.format(all_cohorts_print='>\n<'.join(all_cohorts_before)))
        raise Exception(f'No cohorts after filtering bt_filter {bt_filter} - please check syntax, filters')
    all_cohorts = sorted(all_cohorts, key=lambda x: len(x))
    base_cohort = all_cohorts[0]
    # Test if contains all:
    current_tokens = set(base_cohort.split(','))
    all_ok = True
    for token in all_tokens:
        if token not in current_tokens:
            all_ok=False
            break
    if not(all_ok):
        print('Cohorts:\n<{all_cohorts_print}>'.format(all_cohorts_print='>\n<'.join(all_cohorts_before)))
        raise Exception(f'bootstrap {args.bt_cohort} doesn\'t contains "{bt_filter}", best found: {base_cohort}')
    if len(all_tokens) != len(current_tokens):
        print(f'Warning, base cohort has additional conditions: "{base_cohort}", you asked for {args.bt_cohort}')

all_tokens = bt_filter.split(',')
for token in all_tokens:
    df = df[df['Cohort'].str.contains(token)].reset_index(drop=True)

#Filter more cohorts:
if len(args.filter_whitelist_regex) > 0:
    filter_re = re.compile(args.filter_whitelist_regex)
    df = df[df['Cohort'].apply(lambda x: x==base_cohort or len(filter_re.findall(x)) > 0)].reset_index(drop=True)
if len(args.filter_blacklist_regex) > 0:
    filter_re = re.compile(args.filter_blacklist_regex)
    df = df[df['Cohort'].apply(lambda x: x==base_cohort or len(filter_re.findall(x)) == 0)].reset_index(drop=True)

uniq_cohorts = df['Cohort'].unique()
if len(uniq_cohorts)==1:
    raise Exception(f'Filtered all cohorts and left with only {df["Cohort"].unique()}, please change bt_cohort')
print('Will analyze those cohorts:\n<{cohorts_print}>'.format(cohorts_print = '>\n<'.join(uniq_cohorts)))    

df = df[df['Measurement']!='Checksum'].reset_index(drop=True)
df['Cohort'] = df['Cohort'].apply(lambda x: 'All' if x==base_cohort else x.replace(bt_filter + ',', '').replace(',' + bt_filter, '').\
                                  replace(base_cohort + ',', '').replace(',' + base_cohort, ''))
# Remove all tokens
for token in all_tokens:
    df['Cohort'] = df['Cohort'].apply(lambda x: x.replace(token+',', '').replace(','+token, '').replace(token, ''))
df['Cohort'] = df['Cohort'].apply(lambda x: x.replace('Gender:1.000-2.000', '').replace('Gender:1.000-1.000', 'Males').replace('Gender:2.000-2.000', 'Females'))
df['Measure'] = df['Measurement'].apply(lambda x: x[:x.rfind('_')] if x.find('_')>0 else x)
df['Description'] = df['Measurement'].apply(lambda x: x[x.rfind('_')+1:] if x.find('_')>0 else '')

df_mean = df[df['Description'] =='Mean'].reset_index(drop=True).copy()
df_mean = df_mean[['Cohort', 'Measure', 'Value']].rename(columns={'Value': 'Mean'})
df_lower = df[df['Description'] =='CI.Lower.95'].reset_index(drop=True).copy()
df_lower = df_lower[['Cohort', 'Measure', 'Value']].rename(columns={'Value': 'Lower'})
df_upper = df[df['Description'] =='CI.Upper.95'].reset_index(drop=True).copy()
df_upper = df_upper[['Cohort', 'Measure', 'Value']].rename(columns={'Value': 'Upper'})
df_mean = df_mean.merge(df_lower, on=['Cohort', 'Measure']).merge(df_upper, on=['Cohort', 'Measure'])
#df_mean['Value'] = df_mean['Mean'].astype(str) + ' [' + df_mean['Lower'].astype(str) + ' - ' + df_mean['Upper'].astype(str) + ']'
df_mean['Value'] = df_mean.apply(lambda row: '%2.3f [%2.3f - %2.3f]'%(float(row['Mean']), float(row['Lower']), float(row['Upper'])) if row['Measure'] =='AUC'
                                  else '%2.1f [%2.1f - %2.1f]'%(float(row['Mean']), float(row['Lower']), float(row['Upper'])) ,axis=1)
#df_mean[['Cohort', 'Measure', 'Mean', 'Lower', 'Upper', 'Value']]

requested_pr = pd.DataFrame({'cutoff_pr': args.cutoffs_pr})
requested_pr['requested']=1

# Find in df_mean SCORE@FPR / SCORE@PR where the Mean value is close to those final_cutoffs (which is based on all) for each Cohort, cutoff_pr
suffix_search_term = 'PR_'
if len(df_mean[df_mean['Measure'].str.contains('SCORE@' + suffix_search_term)]) == 0:
    suffix_search_term = 'FPR_'
search_term = 'SCORE@' + suffix_search_term

score_cutoffs = df_mean[(df_mean['Cohort']=='All') & (df_mean['Measure'].str.startswith(search_term))].reset_index(drop=True).copy()
score_cutoffs['cutoff_pr'] = score_cutoffs['Measure'].apply(lambda x: float(x[len(search_term):]))
# Filter cutoffs_pr:
score_cutoffs = score_cutoffs.merge(requested_pr, how='right')
if len(score_cutoffs[score_cutoffs['requested'].isna()]):
    print(score_cutoffs[score_cutoffs['requested'].isna()])
    raise Exception(f'There are missing cutoffs')
score_cutoffs = score_cutoffs[['cutoff_pr', 'Mean']].rename(columns={'Mean':'global_score_cutoff_value'})
score_cutoffs['global_score_cutoff_value'] = score_cutoffs['global_score_cutoff_value'].astype(float)

# Find AUC, NPOS, NNEG, total size, incidence, freqtion from all, SENS@C_I, SPEC@C_I
npos_df = df[(df['Measure']=='NPOS') & (df['Description']=='Obs')].reset_index(drop=True).copy()
npos_df = npos_df.rename(columns={'Value':'NPOS'})
npos_df = npos_df[['Cohort', 'NPOS']]
npos_df['NPOS'] = npos_df['NPOS'].astype(float).astype(int)
nneg_df = df[(df['Measure']=='NNEG') & (df['Description']=='Obs')].reset_index(drop=True).copy()
nneg_df = nneg_df.rename(columns={'Value':'NNEG'})
nneg_df = nneg_df[['Cohort', 'NNEG']]
nneg_df['NNEG'] = nneg_df['NNEG'].astype(float).astype(int)

npos_df = npos_df.merge(nneg_df, on='Cohort')
npos_df['Cohort_Size'] = npos_df['NPOS'] + npos_df['NNEG']
npos_df['Incidence'] = (100 * npos_df['NPOS'] / npos_df['Cohort_Size']).round(2)

total_size = npos_df[npos_df['Cohort']=='All'].iloc[0]['Cohort_Size']
npos_df['Cohort_fraction'] = (100 * npos_df['Cohort_Size'] / total_size).round(2)
npos_df = npos_df.rename(columns={'NPOS':'#Cases', 'NNEG':'#Controls'})

# Use npos_df, df_mean, score_cutoffs
df_auc = df_mean[df_mean['Measure']=='AUC'].reset_index(drop=True)[['Cohort', 'Value']].rename(columns={'Value': 'AUC'}).copy()
#df_auc - Cohort, AUC
npos_df = npos_df.merge(df_auc, on='Cohort')

# Extract SCORE@PR
df_score_pr = df_mean[df_mean['Measure'].str.startswith(search_term)].reset_index(drop=True).copy()
df_score_pr['cutoff_pr'] = df_score_pr['Measure'].apply(lambda x: float(x[len(search_term):]))
df_score_pr = df_score_pr.merge(requested_pr, how='inner')
df_score_pr['Value'] = df_score_pr.apply(lambda row: '%2.5f [%2.5f - %2.5f]'%(float(row['Mean']), float(row['Lower']), float(row['Upper'])) ,axis=1)
df_score_pr = df_score_pr[['Cohort', 'Measure', 'Value']].pivot(index='Cohort', columns='Measure', values='Value').reset_index()
#df_score_pr['cutoff_pr'] = search_term + str(df_score_pr['cutoff_pr'])
npos_df = npos_df.merge(df_score_pr, on='Cohort')

# Use npos_df, score_cutoffs[['cutoff_pr', 'global_score_cutoff_value']]

#df_mean[['Cohort', 'Measure', 'Mean', 'Lower', 'Upper', 'Value']]
df_scores = df_mean[df_mean['Measure'].str.contains(search_term)].reset_index(drop=True).copy()
df_scores['pr_number'] = df_scores['Measure'].apply(lambda x: float(x[len(search_term):]))
df_scores = df_scores[['Cohort', 'pr_number', 'Mean']].rename(columns={'Mean':'score_value'})
df_scores['score_value'] = df_scores['score_value'].astype(float)
df_scores = df_scores.merge(score_cutoffs, how='cross')
df_scores['score_diff_signed'] = df_scores['global_score_cutoff_value'] - df_scores['score_value']
df_scores['score_diff'] = abs(df_scores['score_diff_signed'])

# For each cutoff_pr => sort by score_diff and take first value => fetch pr_number
df_scores = df_scores.sort_values(['Cohort','cutoff_pr', 'score_diff']).reset_index(drop=True)
df_scores_before = df_scores[df_scores['score_diff_signed']<0].groupby(['Cohort','cutoff_pr'])[['pr_number', 'score_diff']].first().reset_index()
df_scores_after = df_scores[df_scores['score_diff_signed']>=0].groupby(['Cohort','cutoff_pr'])[['pr_number', 'score_diff']].first().reset_index()
# Interpolate df_scores_before, df_scores_after in df_scores:
df_scores = df_scores_before.merge(df_scores_after, on=['Cohort', 'cutoff_pr'],suffixes=['_before','_after'],how='outer')
# Fill NA
df_scores.loc[df_scores['pr_number_before'].isna(), 'pr_number_before'] = df_scores.loc[df_scores['pr_number_before'].isna(), 'pr_number_after']
df_scores.loc[df_scores['score_diff_before'].isna(), 'score_diff_before'] = df_scores.loc[df_scores['score_diff_before'].isna(), 'score_diff_after']
df_scores.loc[df_scores['pr_number_after'].isna(), 'pr_number_after'] = df_scores.loc[df_scores['pr_number_after'].isna(), 'pr_number_before']
df_scores.loc[df_scores['score_diff_after'].isna(), 'score_diff_after'] = df_scores.loc[df_scores['score_diff_after'].isna(), 'score_diff_before']

# df_scores['Cohort','cutoff_pr', 'pr_number', 'score_diff'], so we have for each cohort and requested "cutoff_pr" the "pr_number" and the min score diff

# Fetch SENS from df_mean using df_scores:
for m in ['SENS', 'SPEC', 'OR']:
    df_sens = df_mean[df_mean['Measure'].str.contains(m + '@' + suffix_search_term)].copy()
    df_sens['pr_number'] = df_sens['Measure'].apply(lambda x: float(x[len(m+'@' + suffix_search_term):]))
    df_sens_before = df_sens.merge(df_scores[['Cohort','cutoff_pr', 'pr_number_before', 'score_diff_before']].\
                            rename(columns={'pr_number_before':'pr_number'}), on=['Cohort', 'pr_number']).drop(columns=['pr_number', 'Value'])
    df_sens_after = df_sens.merge(df_scores[['Cohort','cutoff_pr', 'pr_number_after', 'score_diff_after']].\
                            rename(columns={'pr_number_after':'pr_number'}), on=['Cohort', 'pr_number']).drop(columns=['pr_number', 'Value'])
    df_sens = df_sens_before.merge(df_sens_after, on=['Cohort', 'cutoff_pr'], suffixes=['_before', '_after'])
    # Interpolate before, after by score_diff_before, score_diff_after:
    df_sens['scores_sum'] = df_sens['score_diff_before'] + df_sens['score_diff_after']
    df_sens['Mean'] =  df_sens['Mean_before'].astype(float) * (1 - (df_sens['score_diff_before'] / df_sens['scores_sum'])) + \
        df_sens['Mean_after'].astype(float) * (1 - (df_sens['score_diff_after'] / df_sens['scores_sum']))
    df_sens['Lower'] =  df_sens['Lower_before'].astype(float) * (1 - (df_sens['score_diff_before'] / df_sens['scores_sum'])) + \
        df_sens['Lower_after'].astype(float) * (1 - (df_sens['score_diff_after'] / df_sens['scores_sum']))
    df_sens['Upper'] =  df_sens['Upper_before'].astype(float) * (1 - (df_sens['score_diff_before'] / df_sens['scores_sum'])) + \
        df_sens['Upper_after'].astype(float) * (1 - (df_sens['score_diff_after'] / df_sens['scores_sum']))
    df_sens['Value'] = df_sens.apply(lambda row: '%2.1f [%2.1f - %2.1f]'%(float(row['Mean']),float(row['Lower']),float(row['Upper']) ), axis=1)
    df_sens = df_sens[['Cohort', 'cutoff_pr', 'Value', 'score_diff_before', 'score_diff_after']]
    df_sens['score_diff_min'] = df_sens.apply(lambda row:  min(row['score_diff_before'], row['score_diff_after']), axis=1)
    
    df_sens['cutoff_name'] = df_sens['cutoff_pr'].apply(lambda x:m+'@SCORE_TH_' + str(x))
    df_sens['cutoff_name_diff'] = df_sens['cutoff_pr'].apply(lambda x:'Diff@SCORE_TH_' + str(x))

    # Pivot:
    df_sens_values = df_sens.pivot(index='Cohort', columns='cutoff_name', values='Value').reset_index()
    npos_df = npos_df.merge(df_sens_values, on='Cohort')
    if len(list(filter(lambda x: x.startswith( 'Diff@SCORE_TH_'),npos_df.columns))) == 0:
        df_sens_diff = df_sens.pivot(index='Cohort', columns='cutoff_name_diff', values='score_diff_min').reset_index()
        npos_df = npos_df.merge(df_sens_diff, on='Cohort')

npos_df['Order'] = npos_df['Cohort'].apply(lambda x: '' if x=='All' else x)
npos_df = npos_df.sort_values('Order').drop(columns=['Order']).reset_index(drop=True)
npos_df.to_csv(os.path.join(args.output, 'fairness_report.tsv'), index=False, sep='\t')
print(f'Wrote [{os.path.join(args.output, "fairness_report.tsv")}]')

# Test statisitical sginificant:
# Cohort	False Negatives	True Positives	Sensitivity
dff_all = { 'cutoff':[], 'chi_square':[], 'pval':[]}
for i in range(len(score_cutoffs)):
    dff = npos_df.copy()
    cutoff = score_cutoffs.iloc[i]['cutoff_pr']
    colname = list(filter(lambda x: x.startswith('SENS@SCORE_TH_') and float(x[len('SENS@SCORE_TH_' ):])== cutoff, dff.columns))[0]
    dff['True_Positives'] = (dff['#Cases'] * dff[colname].apply(lambda x: float(x.split('[')[0])/100)).round().astype(int)
    dff['Sensitivity'] = dff[colname].apply(lambda x: x.split('[')[0])
    dff['False_Negatives'] = (dff['#Cases'] - dff['True_Positives'] ).astype(int)
    f_path = os.path.join(args.output, f'chi_table.{cutoff}.tsv')
    dff = dff[['Cohort', 'False_Negatives', 'True_Positives', 'Sensitivity']]
    dff.to_csv(f_path, index=False, sep='\t')
    dff_all['cutoff'].append(cutoff)
    #chi_square = 0
    dff_t = dff[dff['Cohort']!='All']
    contingency =[]
    for ii in range(len(dff_t)):
        contingency.append([dff_t.iloc[ii]['False_Negatives'], dff_t.iloc[ii]['True_Positives']])
    chi_square, pvalue, dof, expected =chi2_contingency(contingency)
    dff_all['chi_square'].append(chi_square)
    dff_all['pval'].append(pvalue)
    print(f'Wrote [{f_path}]')
dff = pd.DataFrame(dff_all)
dff.to_csv(os.path.join(args.output, f'chi_table.all.tsv'), sep='\t', index=False)
print(f"Wrote [{os.path.join(args.output, f'chi_table.all.tsv')}]")

# Document in conf 