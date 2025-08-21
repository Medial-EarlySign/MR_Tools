#!/opt/medial/dist/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 18:47:04 2019

@author: ron-internal
"""
import matplotlib
matplotlib.use('Agg')
# %matplotlib auto
import pandas as pd
import med
import matplotlib.pyplot as plt
import datetime, argparse
import shap
import matplotlib.backends.backend_pdf
import numpy as np

# import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import iplot, init_notebook_mode
import plotly.offline as py


def filterByTimeWindow(df, min_time_window, max_time_window):
    min_time_window = datetime.timedelta(days = min_time_window)
    max_time_window = datetime.timedelta(days = max_time_window)
    df.loc[:,'time'] = pd.to_datetime(df.time.apply(str), format = '%Y%m%d',errors = 'coerce')
    df.loc[:,'outcomeTime'] = pd.to_datetime(df.outcomeTime.apply(str), format = '%Y%m%d',errors = 'coerce')
    ind_cases1 = df.outcome == 1
    ind_cases2 = ((df['outcomeTime'] - df['time']) <= max_time_window) & ((df['outcomeTime'] - df['time']) >= min_time_window)
    ind_controls1 = df.outcome == 0
    ind_controls2 = ((df['outcomeTime'] - df['time']) > max_time_window)
    return ((ind_cases1 & ind_cases2) | (ind_controls1 & ind_controls2))

def featuresToDf(model):
    # Get Matrix
    featMatFull = med.Mat()
    model.features.get_as_matrix(featMatFull)
    featMatFullNew = featMatFull.get_numpy_copy()
    col_names = model.features.get_feature_names()
    dfFeatures2 = pd.DataFrame(data = featMatFullNew, columns = col_names )
    
    # Get Samples
    samps = med.Samples()
    model.features.get_samples(samps)
    # concatenate
    out = pd.concat([samps.to_df(),dfFeatures2],axis = 1)
    return out

def fix_normalization(feat_df, features ):
    for feat in feat_df:
        if feat in  model.features.attributes:
            if  model.features.attributes[feat].normalized:
                feat_df.loc[:,feat] = feat_df.loc[:,feat] * model.features.attributes[feat].denorm_sdv +  model.features.attributes[feat].denorm_mean;
                
            
    
def get_trace(missing_value,feat, feat_df, shap_df, feat_no_impute,bins, ind , min_bin_size):
 # feat = 'FTR_000027.BMI.last.win_0_180'
    
    # feat = feat_df.columns[feat_df.columns.str.contains(feat, regex = False)][0]
    add_missing = False
    if (np.sum(feat_df[feat] == missing_value) > 0):
        add_missing = True
        bins = np.append([missing_value - 1], bins)
     
    gb_index_tmp = pd.cut(feat_df[feat],bins)
    
    num = feat_df[feat].groupby(gb_index_tmp).count()
    num.index  = pd.IntervalIndex(num.index)
    delta = bins[1]-bins[0]

    # merge small bins
    curr_ind = 0
    new_bins = np.array([],dtype=np.float64)
        
    while (curr_ind < len(num)):
        while (num[num.index[curr_ind].mid] <= min_bin_size) and (curr_ind < len(num) - 1):
            curr_ind += 1
        #new_bins= np.append(new_bins, num.index[curr_ind].left)
        new_bins = np.append(new_bins, bins[curr_ind])
        curr_ind += 1
    new_bins = np.append(new_bins, bins[-1])   
        
        
    gb_index = pd.cut(feat_df[feat],new_bins)
    num = feat_df[feat].groupby(gb_index).count()
    
    
    # mean values:
    tt = shap_df[feat].groupby(gb_index)           
    ttt = (tt.mean().sort_index())

    # outcome prob
    outcome = feat_df['outcome'].groupby(gb_index)
    prob = outcome.sum()/num +  1e-7;
    log_odds_prob = np.log(prob/(1-prob));

    # score
    score = feat_df['pred_0'].groupby(gb_index).mean()
    log_odds_score = np.log(score/(1-score));
    # number of missing
    
    if not(feat in feat_no_impute.columns):
        ind_missing = [False]*len(feat_no_impute)
    else:
        ind_missing = feat_no_impute[feat] == missing_value
    gb_index_missing = pd.cut(feat_df.loc[ind_missing,:][feat],new_bins)
    missing_num =  feat_df.loc[ind_missing,:][feat].groupby(gb_index_missing).count()/num
  
    # number in each bin
    dist = num/len(feat_df)
    
    trace = list()
    if add_missing:
        x_values = ['MISSING VALUE'] + list(ttt.index[1:].astype(str))
    else:
        x_values =  list(ttt.index.astype(str))
    trace += [{'x': x_values, 'y': ttt.values ,'name': f'{ind}: {feat} - SHAP'}]
    trace += [{'x': x_values, 'y': log_odds_prob.values, 'yaxis':'y','name': f'{ind}: {feat} - log odds outcome'}]
    trace += [{'x': x_values, 'y': log_odds_score.values, 'yaxis':'y','name': f'{ind}: {feat} - log odds score'}]
    trace += [{'x': x_values, 'y': dist.values, 'yaxis':'y2' ,'name': f'{ind}: {feat} - distribution'}]
    trace += [{'x': x_values, 'y': missing_num.values, 'yaxis':'y2' ,'name': f'{ind}: {feat} - missing prob'}]
    trace += [{'x': x_values, 'y': prob.values, 'yaxis':'y2','name': f'{ind}: {feat} - outcome'}]
    trace += [{'x': x_values, 'y': score.values, 'yaxis':'y2','name': f'{ind}: {feat} - score'}]
    return trace

def print_html_graphs(missing_value,important_feats, html_dir, feat_df, shap_df, feat_no_impute, min_bin_size, nbins):

    py.init_notebook_mode(connected=False)
    for feat  in important_feats:
        feat_1 =  feat_df.columns[feat_df.columns.str.contains(feat,regex=False)][0]
    
        if feat_df[feat_1].std() == 0:
            print(f'{feat} : std is 0')
            continue
        
        # Binning
        min_val = feat_df[feat_1][feat_df[feat_1] != missing_value].min()
        max_val = feat_df[feat_1][feat_df[feat_1] != missing_value].max()
        bins = np.linspace(min_val, max_val,nbins+1)
        bins[0] = bins[0] - np.finfo(np.float32).eps
        
        trace_1 = get_trace(missing_value,feat_1, feat_df, shap_df, feat_no_impute ,bins, 1 , min_bin_size)
        # trace_2 = get_trace(feat_2, feat_df_2, shap_df_2, feat_no_impute_2 ,bins, 2 )
        
        # data = trace_1 + trace_2
        data = trace_1 
        layout = go.Layout( yaxis = {
                'title' : 'SHAP/log(Odds)'
                 }, yaxis2 = {
                'title' : 'Distribution',
                'overlaying' :'y',
                'side' : 'right',
                'anchor'  : 'free',
                'position' : 1
                 }  )
        fig = go.Figure(data=data, layout=layout)
        py.plot(fig, filename = f'{html_dir}/{feat}.html' )
        # data = [trace1, trace2]
        # py.plot(data, filename = f'/server/Work/Users/Ron/tmp/lc_plots/{feat}.html' )

################################################################################################################################################
## MAIN
################################################################################################################################################

med.logger_use_stdout()
missing_value = -65336
print(matplotlib.get_backend())

parser = argparse.ArgumentParser()
parser.add_argument('--samples_file', metavar = '', default= '', help = 'Input samples ')
parser.add_argument('--rep_file', metavar = '', default= '', help = 'Repository file')
parser.add_argument('--model_file_json_filter', metavar = '', default= '', help = 'Model to use for generating filters. (optional) ')
parser.add_argument('--model_file', metavar = '', default= '' , help = 'Model')
parser.add_argument('--output_file', metavar = '', default= '', help = 'ouput directory')
parser.add_argument('--filter_params', metavar = '', default= '', help = 'params for filtering')
parser.add_argument('--sig_rename_dict', metavar = '', default= '', help = 'renaming dictionary')
parser.add_argument('--num_samples', metavar = '', default= -1 , help = 'Bound the number of samples - for faster running')
parser.add_argument('--pre_process_file', metavar = '', default= '' , help = 'Pre processors file')
parser.add_argument('--html_graphs_dir', metavar = '', default= '' , help = 'if not empty - place to save html graphs')
parser.add_argument('--num_important_signals', metavar = '', type=int,  default= 10 , help = 'num of important signals to save in html graphs')
parser.add_argument('--single_sample', default= '', metavar = '', help = 'format: id,time')

args = parser.parse_args()
#args = parser.parse_args('--sig_rename_dict LDL_over_HDL:LDLoverHDL,category_set_ATC_C10A____:Drug-LIPIDMODIFYINGAGENTS --samples_file /server/Work/AlgoMarkers/AAA/aaa_1.0.0.2/RegistryAndSamples/aaa_train_age_matched_matched.samples --rep_file /home/Repositories/THIN/thin_2018/thin.repository --model_file_json_filter /server/UsersData/ron-internal/MR/Projects/Shared/AlgoMarkers/aaa/configs/analysis/ever_smokers_json.json --model_file /server/Work/AlgoMarkers/AAA/aaa_1.0.0.2/Performance/model_6_S4.model --output_file /server/Work/Users/Ron/tmp/shap_4.pdf --filter_params Time-Window:30,180;Age:65,75;Gender:2,2;Ex_or_Current_Smoker:0.5,1.5'.split())

# ron-internal@node-04:/nas1/UsersData/ron/MR/Tools/ShapFeatureImportance$ python shap_feature_importance_tool.py --num_samples 10000 --samples_file /nas1/Work/AlgoMarkers/LungCancer/lc_4_270119/CohortAndSamples/data_NSCLC_AllStages_rand_controls_train_ever_smokers_Matched.samples --rep_file /server/Work/CancerData/Repositories/KP/kp.repository --model_file_json_filter /nas1/UsersData/ron/MR/Projects/Shared/AlgoMarkers/lungcancer/configs/analysis/bootstrap/bootstrap.json --model_file /server/Work/AlgoMarkers/LungCancer/lc_4_270119/Model/model_30_es_S10.model --output_file /server/Work/Users/Ron/tmp/shap_lc_2.pdf --filter_params "Time-Window:30,180;Age:55,80;Gender:1,2;Ex_or_Current_Smoker:0.5,1.5" --num_samples 2000
# args = parser.parse_args('--num_samples 10000 --samples_file /nas1/Work/AlgoMarkers/LungCancer/lc_4_270119/CohortAndSamples/data_NSCLC_AllStages_rand_controls_train_ever_smokers_Matched.samples --rep_file /server/Work/CancerData/Repositories/KP/kp.repository --model_file_json_filter /nas1/UsersData/ron/MR/Projects/Shared/AlgoMarkers/lungcancer/configs/analysis/bootstrap/bootstrap.json --model_file /server/Work/AlgoMarkers/LungCancer/lc_4_270119/Model/model_30_es_S10.model --output_file /server/Work/Users/Ron/tmp/shap_lc_2.pdf --filter_params Time-Window:270,365;Age:55,80;Gender:1,2;Ex_or_Current_Smoker:0.5,1.5'.split())
# args = parser.parse_args('--num_samples 1000 --samples_file /nas1/Work/AlgoMarkers/LungCancer/lc_4_270119/CohortAndSamples/data_NSCLC_AllStages_rand_controls_train_Matched.samples --rep_file /server/Work/CancerData/Repositories/KP/kp.repository --model_file_json_filter /nas1/UsersData/ron/MR/Projects/Shared/AlgoMarkers/lungcancer/configs/analysis/bootstrap/bootstrap.json --model_file /server/Work/AlgoMarkers/LungCancer/lc_4_270119/Model/model_30_S10.model --output_file /server/Work/Users/Ron/tmp/shap_lc17.pdf --filter_params Time-Window:270,365;Age:55,80;Gender:1,2;Ex_or_Current_Smoker:0.5,1.5 --num_samples 2000'.split())
# args.sig_rename_dict = "Smoking-Never_Smoker:Smoking-Never Smoker status,category_set_CHRONIC_OBSTRUCTIVE_PULMONARY_DISEASE_AND_ALLIED_CONDITIONS-category_set_CHRONIC_OBSTRUCTIVE_PULMONARY_DISEASE_AND_ALLIED_CONDITIONS:COPD history,category_set_Cancers-category_set_Cancers:Cancer history"
# args.html_graphs_dir = "/server/Work/Users/Ron/tmp/"
#args = parser.parse_args('--num_important_signals 20 --num_samples 50000 --samples_file /server/Work/Users/Ron/Projects/nba/thin_flow_samples_insulins_first_train.samples  --rep_file /home/Repositories/THIN/thin_2018/thin.repository --model_file /server/Work/Users/Ron/Projects/nba/insulins_start/basic_model_7/insulins_start_S1.model --output_file /server/Work/Users/Ron/Projects/nba/insulins_start/basic_model_7/shap.pdf --html_graphs_dir /server/Work/Users/Ron/Projects/nba/insulins_start/basic_model_7/'.split())
# args = parser.parse_args('--num_important_signals 20 --num_samples 50000 --samples_file /server/Work/AlgoMarkers/nba/results/metformin_start/basic_model_7/metformin_start_test.preds --rep_file /home/Repositories/THIN/thin_2018/thin.repository --model_file /server/Work/AlgoMarkers/nba/results/metformin_start/basic_model_7/metformin_start_S1.model --output_file /server/Work/AlgoMarkers/nba/results/metformin_start/basic_model_7/shap.pdf --html_graphs_dir /server/Work/AlgoMarkers/nba/results/metformin_start/basic_model_7/'.split())
samples_file = args.samples_file
rep_file = args.rep_file
model_file_json_filter = args.model_file_json_filter
model_file = args.model_file
output_file = args.output_file
filter_params = args.filter_params
pre_process_file = args.pre_process_file
num_samples = int(args.num_samples)
html_graphs_dir = args.html_graphs_dir
num_important_signals = args.num_important_signals
if args.single_sample != '':
    single_sample = args.single_sample.split(',');
else:
    single_sample = ''
        

min_bin_size = args.min_bin_size
nbins = args.nbins

if (len(args.sig_rename_dict) > 0):
    rename_dict = {k.split(':')[0] : k.split(':')[1]  for k in args.sig_rename_dict.split(',')}
else:
    rename_dict = dict()
    
pdf = matplotlib.backends.backend_pdf.PdfPages(args.output_file)

if len(single_sample) > 0:
    samps_df = pd.DataFrame({'id':[int(single_sample[0])], 'time':[int(single_sample[1])]})
else:  
    samps_df = pd.read_csv(samples_file, sep = '\t', index_col = False)

if not(filter_params == ''):
# parse filter_params:
    filter_dict = {x.split(':')[0] : x.split(':')[1] for x in filter_params.split(';') }
    
    model_filter = med.Model()
    if not(model_file_json_filter == ''):
        model_filter.init_from_json_file(model_file_json_filter)
    else:
        model_filter.add_age()
        model_filter.add_gender()
        
    req_signals = model_filter.get_required_signal_names()
    
    samples = med.Samples()
    samples.read_from_file(samples_file)
    
    rep = med.PidRepository()
    ids = samps_df.id.unique().astype('int32')
    rep.read_all(rep_file,ids ,req_signals)
    
    model_filter.learn(rep, samples)
    model_filter.apply(rep, samples)
    
    # filter by age and 
    feat_df = featuresToDf(model_filter)
    
    # filter by filter_params
    def filter_feat_mat(feat_df, filter_dict ):
        ind = [True]*len(feat_df)
        for filt_param in filter_dict:
            min_val = float(filter_dict[filt_param].split(',')[0])
            max_val = float(filter_dict[filt_param].split(',')[1])
            if filt_param == 'Time-Window':
                ind &= filterByTimeWindow(feat_df.copy(), min_val, max_val)
            
            else:
                col_name = list(feat_df.columns[feat_df.columns.str.contains(filt_param)])
                if (len(col_name) > 1):
                    raise ValueError(f'{filt_param} has More than one column: ' + " ".join(col_name))
                
                if (len(col_name) == 0):
                    raise ValueError(f'{filt_param} columns not found')
                    
                col_name = col_name[0]
                ind &= (feat_df[col_name] >= min_val) & (feat_df[col_name] <= max_val)
                
        return ind
    
    ind = filter_feat_mat(feat_df, filter_dict)
else:
    ind = [True]*len(samps_df)
      
    
# prepare samples
    ####

#####

ind2 = np.where(ind)[0]
samps_filterd_df = samps_df.loc[np.random.permutation(ind2), :].copy()
# samps_filterd_df.drop_duplicates('id','last', inplace = True)
print('Removed remove duplicates!!!!!!!!!')
samps_filterd_df.reset_index(drop = True, inplace = True)
if (not(num_samples == -1 ) and (len(samps_filterd_df) > num_samples)):
    samps_filterd_df = samps_filterd_df.iloc[0:num_samples]

samples_filterd = med.Samples()
#samps_filterd_df.drop(columns = ['split'], inplace = True) # in case on split = Nan
samples_filterd.from_df(samps_filterd_df)

##
print('Calculate SHAP values')
rep = med.PidRepository()
rep.init(rep_file)
model = med.Model()
model.read_from_file(model_file)
if not(pre_process_file == ''):
    model.add_pre_processors_json_string_to_model("", pre_process_file);
model.fit_for_repository(rep)
req_signals = model.get_required_signal_names()
ids = samps_filterd_df.id.unique().astype('int32')
rep.read_all(rep_file,ids ,req_signals)
model.apply(rep,samples_filterd)

shap_mat = med.Mat()
feat_mat = med.Mat()
model.features.get_as_matrix(feat_mat)
model.calc_contribs(feat_mat, shap_mat)

shap_mat_py = shap_mat.get_numpy_copy()
feat_df_orig = featuresToDf(model) 
feat_df = feat_df_orig.copy()
fix_normalization(feat_df, model.features )
ind = np.where(feat_df.columns == 'Age')[0][0]
feat_only_df = feat_df[feat_df.columns[ind:]]

################################################################################################################################################

shap_final = shap_mat_py[:,0:-1]
X = feat_only_df
X_nan = X.copy()
fig = plt.figure()
X_nan[X_nan == missing_value] = np.nan
if len(single_sample) == 0:
    print("Plotting features SHAP")
    shap.summary_plot(shap_final, X_nan,max_display = 30)
    plt.text(0.05,0.95,'Importance of single features' , transform=fig.transFigure, size=24)
    pdf.savefig(fig, bbox_inches="tight")
    
    fig = plt.figure()
    shap.summary_plot(shap_final, X_nan, plot_type="bar")
    plt.text(0.05,0.95,'Importance of single features' , transform=fig.transFigure, size=24)
    pdf.savefig(fig, bbox_inches="tight")

################################################################
# Group by signal
################################################################


# generate list of groups
from collections import defaultdict
group_dict = defaultdict(list)
feat2ind = dict()

dct = defaultdict(list)
for ind in range(len(X_nan.columns)):
    feat = X_nan.columns[ind]
    feat2ind[feat] = ind
    
    feat_split = feat.split('.')
    if len(feat_split) >=2:
        if (feat_split[1] in {'RC_Diagnosis', 'Drug', 'ICD9_Diagnosis','ICD9_Hospitalization'}):
            group_dict[feat_split[2]].append(feat)
        else:
            group_dict[feat_split[1]].append(feat)
    else:
        group_dict[feat_split[0]].append(feat)
    

group_names = list(group_dict.keys())

shap_es_for_group = shap_final

# Aggregate by signal groups
group_shap = np.empty((shap_es_for_group.shape[0], 0))
group_missing = dict()
for group in group_dict:
    n_missing = 0
    vec = np.zeros([1,shap_es_for_group.shape[0]])
    for feat in group_dict[group]:
        
        vec += shap_es_for_group[:,feat2ind[feat]]
        n_missing += np.sum(X[feat] == missing_value)
        
    group_missing[group] = n_missing/len(group_dict[group])/shap_es_for_group.shape[0]
    group_shap = np.append(group_shap, vec.transpose(), axis = 1)  

# ndataframe with mean(|abs|)
group_mean_abs_shap = (np.abs(group_shap)).mean(axis = 0)
abs_shap_with_names = {group_names[i] : group_mean_abs_shap[i] for i in range(len(group_mean_abs_shap)) }
df_mean_abs_shap = pd.DataFrame.from_dict(abs_shap_with_names,orient = 'index')
df_mean_abs_shap.columns = ['mean_abs_shap_values']
df_mean_abs_shap.sort_values(by = 'mean_abs_shap_values',inplace = True,  ascending=False )

if len(single_sample) == 0:
    ax = df_mean_abs_shap.iloc[0:25].plot(kind = 'barh', legend = False,grid = True )
    ax.invert_yaxis() 
    fig =  ax.get_figure()
    plt.ylabel('Model Parameter')
    plt.xlabel('mean(|SHAP|)')
    plt.grid(axis = 'y')
    plt.text(0.05,0.95,'Importance of signals' , transform=fig.transFigure, size=24)
    pdf.savefig(fig, bbox_inches="tight")


# Aggregate by signal groups + value/trend/time
################################################
# ftrs_groups = {'value' : {'last','avg','max','min'}, 'trend' : {'slope', 'win_delta','last_delta','max_diff','range_width'}, 'time' : {'last_time'},
#                'std': {'std'}, 'Smoking status' : {'Current_Smoker','Ex_Smoker','Never_Smoker','Passive_Smoker'}, 'Time Since Quitting' : {'Smok_Days_Since_Quitting'}, 
#                'Pack years': {'Smok_Pack_Years_Last', 'Smok_Pack_Years_Max'}, 'Smoking Intensity' : {'Smoking_Intensity'}, 'Smoking duration': {'Smoking_Years'}}

ftrs_groups = {'value' : {'last','avg','max','min'}, 'trend' : {'slope', 'win_delta','last_delta','max_diff'}, 'time' : {'last_time'},
                'flactuations': {'std','range_width'}, 'Time Since Quitting' : {'Smok_Days_Since_Quitting'}, 
                'Pack years': {'Smok_Pack_Years_Last', 'Smok_Pack_Years_Max'}, 'Smoking Intensity' : {'Smoking_Intensity'}, 'Smoking duration': {'Smoking_Years'}}

tmp_dict = {k:list(ftrs_groups[k]) for k in list(ftrs_groups.keys())}
ftrs_groups_rev = dict()
for k in  ftrs_groups.keys():
    for v in ftrs_groups[k]:
        ftrs_groups_rev[v] = k  

for feat in X_nan.columns:
    ftr_split = ftr_type = feat.split('.')
    if len(ftr_split) >= 3:
        ftr_type = ftr_split[2]
        if not (ftr_type in ftrs_groups_rev):
            ftrs_groups_rev[ftr_type] = ftr_type
            
            
    

# Group By Signal and type (Value, trend, etc.) 

# Category Variables
cat_ftrs = dict()

#n_ftrs_original = len(X_nan.columns)
#for ftr in X_nan.columns:
#    if (ftr.find('category_set_') >= 0) or (ftr.find('Registry') >= 0):
#        ftr_split = ftr.split('.')
#        if (len(ftr_split)>2):
#            cat_ftrs[ftr_split[2]] = ftr_split[2].replace('category_set_','')

# run  model without imputations:
######################################
model_no_imp = med.Model()
model_no_imp.read_from_file(model_file)
model_no_imp.apply(rep,samples_filterd, med.ModelStage.APPLY_FTR_GENERATORS, med.ModelStage.APPLY_FTR_GENERATORS)
feat_df_no_imp = model_no_imp.features.to_df()
X_no_imp = feat_df_no_imp[feat_df_no_imp.columns[np.where(feat_df_no_imp.columns == 'Age')[0][0]:]]

#initialize dicts
shap_dict = dict()
X_dict = dict()

# 
for group in group_dict:
    for feat in group_dict[group]:
         feat_split = feat.split('.')
         
         if len(feat_split) <= 2:
             shap_dict[group] = np.zeros(shap_final.shape[0])
             X_dict[group] = (np.zeros(shap_final.shape[0]), np.empty(shap_final.shape[0]),np.zeros(shap_final.shape[0]))
                  
         if len(feat_split) >= 3:
             if (feat_split[2] in ftrs_groups_rev):
                 feat_type = ftrs_groups_rev[feat_split[2]]
                 shap_dict[group, feat_type] = np.zeros(shap_final.shape[0])
                 X_dict[group, feat_type] = (np.zeros(shap_final.shape[0]), np.empty(shap_final.shape[0]),np.zeros(shap_final.shape[0]))
             else:  
                 print(f'not good: {feat}')
                 shap_dict[group] = np.zeros(shap_final.shape[0])
                 X_dict[group] = (np.zeros(shap_final.shape[0]), np.empty(shap_final.shape[0]),np.zeros(shap_final.shape[0]))
             

add_ftrs = set()  
def get_time_delta(win_part):
    win_split = win_part.split('_')
    return (int(win_split[-1]) - int(win_split[-2]))/500 # slope is muliplied by 500 in the feature generator itself
    
    
for group in group_dict:
    for feat in group_dict[group]:
        feat_split = feat.split('.')
        if (len(feat_split) >=3) and (feat_split[2] in ftrs_groups_rev):
            feat_type = ftrs_groups_rev[feat_split[2]]

            shap_dict[group, feat_type] += shap_final[:,feat2ind[feat]]
            add_ftrs.add(feat)
            # set feature value to ne the feature with maximum importanec in the group
            ind = np.abs(shap_final[:,feat2ind[feat]]) > np.abs(X_dict[group, feat_type][0])
            if (feat_split[2] == 'slope'):
                time_delta = get_time_delta(feat_split[3])
            else:
                time_delta = 1
                           
            X_dict[group, feat_type][1][ind] = X_nan.loc[ind,feat].values*time_delta
            X_dict[group, feat_type][0][ind] = np.abs(shap_final[:,feat2ind[feat]])[ind]
            
            if feat in X_no_imp.columns:
                X_dict[group, feat_type][2][ind] = X_no_imp.loc[ind,feat] == missing_value
            elif ".".join(feat_split[0:-1]) in X_no_imp.columns:
                X_dict[group, feat_type][2][ind] = X_no_imp.loc[ind,".".join(feat_split[0:-1])] == missing_value
                    
        
        else:
            add_ftrs.add(feat)
            X_dict[group]= X_nan[feat].values
            shap_dict[group] = shap_final[:,feat2ind[feat]]
   
            
num_ftrs_in_shap = len(add_ftrs)
n_ftrs_original = len(X.columns)
if not(n_ftrs_original == num_ftrs_in_shap):
    raise ValueError(f'Check Shap grouping - expected num features {n_ftrs_original}, shap num features {num_ftrs_in_shap}')


# Construct Matrices
shap_mat = np.empty((shap_final.shape[0], 0))
X_mat = np.empty((shap_final.shape[0], 0))
Xtypes = pd.DataFrame()
for key in shap_dict.keys():
    shap_mat = np.append(shap_mat,shap_dict[key].reshape(shap_mat.shape[0],1), axis = 1)
    if type(key) == tuple:
        new_key = "-".join(key)
        v =  X_dict[key][1]
    else:
        new_key = key
        v =  X_dict[key]
        
    if new_key in rename_dict:
        new_key = rename_dict[new_key]
    
    Xtypes[new_key] = v 
        # Xtypes["-".join(new_key) + f' ({ np.sum(X_dict[key][2])/len(shap_mat)})'] = X_dict[key][1]

      
if len(single_sample) == 0:
    fig = plt.figure()
    #Xtypes.rename({'category_set_CHRONIC_OBSTRUCTIVE_PULMONARY_DISEASE_AND_ALLIED_CONDITIONS': 'COPD History', 'Smoke_Days_Since_Quitting' : 'Smoking-Time Since Quitting', 'category_set_Cancers': 'Cancer History', 'Never_Smoker': 'Never Smoker Status', 'Current_Smoker': 'Current Smoker Status','Smoking': 'Smoking-Pack Years'},inplace = True, axis = 1)
    shap.summary_plot(shap_mat, Xtypes, max_display  = 20)
    plt.text(0.05,0.95,'Importance of signals - grouped by type' , transform=fig.transFigure, size=24)
    pdf.savefig(fig, bbox_inches="tight")
    pdf.close()  
    print(f'{args.output_file} saved')


# def get_shap_feat(model):
#     shap_mat = med.Mat()
#     feat_mat = med.Mat()
#     model.features.get_as_matrix(feat_mat)
#     model.calc_contribs(feat_mat, shap_mat)
#     shap_mat_py = shap_mat.get_numpy_copy()
#     feat_df = model.features.to_df()
#     ind = np.where(feat_df.columns == 'Age')[0][0]
#     feat_only_df = feat_df[feat_df.columns[ind:]]
#     shap_df = pd.DataFrame(shap_mat_py[:,0:-1])
#     shap_df.columns = feat_only_df.columns
#     return shap_df, feat_only_df

if html_graphs_dir != '':
    ind = np.where(feat_df.columns == 'Age')[0][0]
    feat_only_df = feat_df[feat_df.columns[ind:]]
    shap_df = pd.DataFrame(shap_final)    
    shap_df.columns = feat_only_df.columns
    tt = shap_df.head().abs().mean()
    important_feats = tt.sort_values(ascending=False)[0:num_important_signals].index
    feat_no_impute = X_no_imp

    print_html_graphs(missing_value,important_feats, html_graphs_dir, feat_df, shap_df, feat_no_impute)
    
if len(single_sample) > 0:
    ind = 0 
    digits = 1
    shap.force_plot(shap_mat_py[ind][-1], shap_mat[ind,:], np.round(10**digits*Xtypes.iloc[ind,:])/10**digits, matplotlib = True)
    out_df = pd.DataFrame(np.round(10**digits*Xtypes.iloc[ind,:])/10**digits).transpose()
    out_df.loc[1,:] = shap_mat[ind,:]
    out_df.loc[2,:] = abs(shap_mat[ind,:])
    out_df.sort_values(by = 2,axis = 1,ascending=False,inplace= True)
    txt = f"ID: {int(feat_df.iloc[ind]['id'])}\nDate: {int(feat_df.iloc[ind]['time'])}\nOutcome date: {int(feat_df.iloc[ind]['outcomeTime'])}\nCase: { int(feat_df.iloc[ind]['outcome'])}\nAge: {int(feat_df.iloc[ind]['Age'])}\nGender : {int(feat_df.iloc[ind]['Gender'])}"

    print(txt)
    print(out_df.transpose())
     
##########
#dd = {ftr : len(ftr.split('.')) for ftr in X_nan.columns}
#ttt = pd.Series(dd)
#ttt.sort_values()
#pdf = matplotlib.backends.backend_pdf.PdfPages('/server/Work/Users/Ron/tmp/shap_lc17.pdf')
#cnt = 0
#ind = 0
#digits = 1

#while (cnt < 30):
#    print("%d %d" % (ind, cnt))
#    # if (feat_df.iloc[ind]['outcome'] == 1):
#    shap.force_plot(shap_mat_py[ind][-1], shap_mat[ind,:], np.round(10**digits*Xtypes.iloc[ind,:])/10**digits, matplotlib = True)
#    txt = f"ID: {int(feat_df.iloc[ind]['id'])}\nDate: {int(feat_df.iloc[ind]['time'])}\nOutcome date: {int(feat_df.iloc[ind]['outcomeTime'])}\nCase: { int(feat_df.iloc[ind]['outcome'])}\nAge: {int(feat_df.iloc[ind]['Age'])}\nGender : {int(feat_df.iloc[ind]['Gender'])}"
#    plt.text(0.05,0.9,txt, transform=fig.transFigure, size=24)
#   pdf.savefig( plt.gcf(),bbox_inches='tight', pad_inches = 1)
#   cnt += 1 
#   ind += 1
#pdf.close()
