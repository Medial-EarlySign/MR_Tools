# -*- coding: utf-8 -*-
"""
Created on Sun Dec  2 14:25:04 2018

@author: Ron
"""
# %%
import sys, os
sys.path.insert(0,'/nas1/UsersData/ron/MR/Projects/Shared/python')
import medpython as med
import pandas as pd
from sklearn.metrics import roc_curve, auc
import numpy as np
from common.match import Matcher
import time
import argparse
matcher = Matcher()

timestr = time.strftime("%Y%m%d-%H%M%S")
outDir = '/server/Work/Users/Ron/tmp/'
parser = argparse.ArgumentParser()
parser.add_argument('--f_model', metavar = '' , help = ' a list of .model file(s) seperated by commas')
parser.add_argument('--f_samples', metavar = '', help = 'Med Samples file')
parser.add_argument('--f_split', metavar = '', help = 'Splits file')
parser.add_argument('--f_out', metavar = '' , help = 'results file')
parser.add_argument('--handle_missing', metavar = '', default= 'ignore', help = 'ignore/keep/match. Ignore - remove all missing data per feature. Keep - matches on non-missing data, but uses them in the evaluation (with or without imputing). Match - matches also on missing-values')
parser.add_argument('--split', metavar = '', default= -1, type = int, help = 'Chooses splits to run over. Can be -1, for all splits. if more than one model is received, the splits are deduced from the list. The first model runs on split 0, the second on split 1, etc. if only one model is received, a specific split can be chosen')
parser.add_argument('--rep_dir', metavar = '', help = 'The repository location')
parser.add_argument('--missing_value', metavar = '', default= -65336)
parser.add_argument('--temp_ext', metavar = '', default= '')
parser.add_argument('--train_values', metavar = '', default= '2', help = 'A list of Train values to run on. Seperated by commas ') 

args = parser.parse_args()
args.temp_ext = str(args.temp_ext)

def getSamplesFromSplitsAndTrain(f_samples, f_split, rep_dir):
    dfSamples = pd.read_csv(f_samples,sep = '\t').drop(columns = ['split'],axis =1 )
    if ('pred_0' in dfSamples.columns):
        dfSamples.drop(columns = ['pred_0'], axis = 1)
    rep = med.PidRepository()
    rep.read_all(rep_dir,list(dfSamples.id),['TRAIN'])     
    # Read splits and join with samples
    dfTrain = rep.get_sig('TRAIN') 
    dfTrain.columns = ['id','train']
    dfSplit = pd.read_csv(f_split,sep = '\t',names=['id','split'],skiprows=1) 
    dfSamples = pd.merge(dfSamples, dfSplit, on = 'id', how = 'left')
    dfSamples = pd.merge(dfSamples, dfTrain, on = 'id', how = 'left')
    dfSamples = dfSamples[dfSamples.train.isin(train_values)]
    dfSamples.drop('train', axis = 1, inplace = True)
    return dfSamples
    
def featuresToDf(dfSamples,model_for_feat):
    # Get Matrix
    featMatFull = med.Mat()
    model_for_feat.features.get_as_matrix(featMatFull)
    featMatFullNew = featMatFull.get_numpy_copy()
    col_names = model_for_feat.features.get_feature_names()
    dfFeatures2 = pd.DataFrame(data = featMatFullNew, columns = col_names )
    
    # Get Samples
    samps = med.Samples()
    model_for_feat.features.get_samples(samps)
    # concatenate
    out = pd.concat([dfSamples,dfFeatures2],axis = 1)
    return out
    
def generateBinEdges(values, handle_missing):
    nonMissingValues = values[values != args.missing_value].unique()
    numEffectiveValues = len(nonMissingValues)
    
    if (handle_missing == 'match') and (args.missing_value in values.unique()):
        numEffectiveValues += 1
 
    if  numEffectiveValues <= 1:
        bins_edges = []
    elif numEffectiveValues == 2:    
        # binary features 
        if handle_missing == 'match' and (args.missing_value in values.unique()):
            bins_edges = [-np.inf,(values.unique()[0] + values.unique()[1])/2,np.inf]
        else:
            bins_edges = [-np.inf,(nonMissingValues[0] + nonMissingValues[1])/2,np.inf]
        
    else:
        bins_edges = generateBinEdgesForContinous(values[values != args.missing_value])
        if (handle_missing == 'match') and (args.missing_value in values.unique()):
            if bins_edges[0] < args.missing_value:
                 bins_edges[0] = args.missing_value + 0.5
                 bins_edges = [args.missing_value - 0.5] + bins_edges
        
    return bins_edges
    
def generateBinEdgesForContinous(values,lower_prec = 10, upper_prec = 90,num_bins = 12):
    lower_edge = np.percentile(values,lower_prec )
    upper_edge = np.percentile(values,upper_prec )
    int_length = upper_edge - lower_edge
    int_delta = int_length/(num_bins - 2)
    binEdgesAddition = lower_edge + int_delta*(1 + np.arange(0,num_bins - 3))
    binEdges = [-np.inf, lower_edge] +  list(binEdgesAddition) + [ upper_edge, np.inf]
    return binEdges

def get_splits(args,models):
    if len(models) > 1:
        splits = range(len(models))
    else:
        splits = [args.split]

    return splits


if __name__ == '__main__':
    
    # Extract model(s)
    models = args.f_model.replace(' ','').split(',')
    train_values = [int(value) for value in args.train_values.replace(' ','').split(',')]
    
    print(f'Models: {models}')  
    # Get Samples in the relveant 'TRAIN' signal.
    dfSamples = getSamplesFromSplitsAndTrain(args.f_samples, args.f_split, args.rep_dir)
    
    print("handle_missing :" + args.handle_missing)
    
    samples_test_file = outDir + 'samples_per_split_for_testing.txt'
    # 
    splits = get_splits(args,models)
        
    resultsDict = dict()
    split_ind = 0
    rep = med.PidRepository()
    for split in splits:
        # Gen Samples file (temp - needed to be removed when samples can be reaced directly:
        if split == -1:
            # dont filter by split
            dfSamples.to_csv(samples_test_file + args.temp_ext,sep = '\t',index = False)
        else:
            dfSamples[dfSamples.split == split].to_csv(samples_test_file + args.temp_ext,sep = '\t',index = False)
        
        modelName = models[split_ind]
        split_ind += 1
        
        ## Generate Features Matrix - one for Matching, and one for applying
        print('Generate Features Matrix')
        samples = med.Samples()
        samples.read_from_file(samples_test_file + args.temp_ext)
        dfSamplesPerSplit = pd.read_csv(samples_test_file + args.temp_ext ,sep = '\t')
        model_for_feat = med.Model()
        model_for_feat.read_from_file(modelName)
        req_signals = model_for_feat.get_required_signal_names() 
        rep.read_all(args.rep_dir,samples.get_ids(),list(req_signals))      
        model_for_feat.apply(rep,samples,med.ModelStage.APPLY_FTR_GENERATORS, med.ModelStage.APPLY_FTR_GENERATORS)
        
        dfFeaturesForMatching = featuresToDf(dfSamplesPerSplit,model_for_feat)
        model_for_feat.apply(rep,samples,med.ModelStage.APPLY_FTR_PROCESSORS, med.ModelStage.APPLY_FTR_PROCESSORS)
        dfFeatures = featuresToDf(dfSamplesPerSplit,model_for_feat)
        
        features_to_check = dfFeatures.columns.drop(['EVENT_FIELDS','outcome', 'id', 'time', 'outcomeTime', 'split'])
        
        features_to_check = features_to_check
        feat_ind = 0
        resultsDict[split] = dict()
        for feat in features_to_check:
            #feat = 'Age'
            start = time.time()
            resultsDict[split][feat] = dict()
            print(f'Split: {split}, {feat_ind}: {feat}')
            
            # generate bins:
            print('Generate Bins')
            dfFeaturesForMatchingForFtr = dfFeaturesForMatching[[feat,'outcome']]
            values = dfFeaturesForMatchingForFtr.loc[dfFeaturesForMatchingForFtr.outcome == 1 ,feat]
            
            bins_edges = generateBinEdges(values, args.handle_missing)
            
            if len(bins_edges) == 0:
                continue;
                
            # handle missing data:
            if (args.handle_missing == 'ignore') or  (args.handle_missing == 'keep'):
                # in 'keep' missing indexes are added later
                dfFeaturesForMatchingForFtr = dfFeaturesForMatchingForFtr[dfFeaturesForMatchingForFtr[feat] != args.missing_value]    
                 
            # generate new validation set:
            print('Performe Match:')
            control_ind_agg, cases_ind_agg = matcher.match(dfFeatures = dfFeaturesForMatchingForFtr.rename({'outcome':'label'}, axis = 1), feat = feat, bins_edges = bins_edges)
           
            if (args.handle_missing == 'ignore') or (args.handle_missing == 'match'):
                # in match missing values are already in cases_ind_agg/control_ind_agg
                inds = sorted(np.unique(np.concatenate([control_ind_agg, cases_ind_agg])))
            else:
                # keep
                missing_value_bool = dfFeaturesForMatching[feat] == args.missing_value
                missing_value_ind = [i for i,x in enumerate(missing_value_bool) if x]
                inds = sorted(np.unique(np.concatenate([missing_value_ind, control_ind_agg, cases_ind_agg])))
                
            dfSampledMatched = dfFeatures.loc[inds,['id','time','outcome','outcomeTime','split']]
            dfSampledMatched['EVENT_FIELDS'] = 'SAMPLE'
            dfSampledMatched = dfSampledMatched[['EVENT_FIELDS','id','time','outcome','outcomeTime','split']]
            dfSampledMatched.to_csv(outDir + 'valid_matched' + args.temp_ext + '.samples', index = False, header = True, sep = '\t')
            
            # gen Matrix:
            dfFeaturesMatched = dfFeatures.loc[inds,features_to_check]
            matMatched = med.Mat()
            matMatched.set_signals(med.StringVector(list(features_to_check)))
            matMatched.load_numpy(dfFeaturesMatched.values)
            
            # apply model with matched indexes
            print('Apply Model')
            samples_apply = med.Samples()
            samples_apply.read_from_file(outDir + 'valid_matched' + args.temp_ext + '.samples')
            
            model_apply= med.Model()
            model_apply.read_from_file(modelName)
            
            model_apply.features.set_as_matrix(matMatched)
            model_apply.features.append_samples(samples_apply)
            model_apply.apply(rep,samples_apply,med.ModelStage.APPLY_PREDICTOR,med.ModelStage.END)
            
            samples_apply.write_to_file(outDir+'valid_matched_out'+args.temp_ext+'.samples')
            # calculate AUC
            dfOutSamples =  pd.read_csv(outDir + 'valid_matched_out' + args.temp_ext + '.samples',sep = '\t')
            fpr, tpr, _ = roc_curve(dfOutSamples.outcome, dfOutSamples.pred_0)
            roc_auc = auc(fpr, tpr)  
            resultsDict[split][feat]['AUC'] = roc_auc
            
            num_cases = np.sum(dfSampledMatched.loc[inds].outcome == 1)
            num_controls = np.sum(dfSampledMatched.loc[inds].outcome == 0)
            resultsDict[split][feat]['num_cases'] = num_cases
            resultsDict[split][feat]['num_controls'] = num_controls
            end = time.time()
            time_feat = end - start
            print(f"Feature: {feat}, AUC: {roc_auc}, # Controls: {num_controls}, # Cases: {num_cases} Time: {time_feat}")
            feat_ind += 1
            
    # %%
        
    # Write Results:
    dfList = dict()
    split = 0
    tt = pd.DataFrame()
    for split in splits:
        dfList[split] = (pd.DataFrame.from_dict(resultsDict[split], orient='index',columns=['AUC','num_cases','num_controls']))
        dfList[split].rename( {'AUC' : 'AUC_' + str(split), 'num_cases' : 'num_cases_' + str(split) , 'num_controls' : 'num_controls_' + str(split)}, inplace = True,axis = 1)
        tt = pd.merge(tt, dfList[split], left_index=True, right_index=True, how = 'outer')
        
    print('Written results file: ' + args.f_out )
    tt.to_csv(args.f_out, index = True, header = True)
    
    # Temp 
    #dfList2 = [None]*4
    #dfList2[0] = pd.read_csv('/server/Work/Users/Ron/Projects/LungCancer/results/model_14_matched_new_serialization/feat_imp_S0.txt',sep = ' ',header = None, usecols= [2,4],index_col=0,names = ['feature','score_0']).sort_values(by = 'feature')
    #dfList2[1] = pd.read_csv('/server/Work/Users/Ron/Projects/LungCancer/results/model_14_matched_new_serialization/feat_imp_S1.txt',sep = ' ',header = None, usecols= [2,4],index_col=0,names = ['feature','score_1']).sort_values(by = 'feature')
    #dfList2[2] = pd.read_csv('/server/Work/Users/Ron/Projects/LungCancer/results/model_14_matched_new_serialization/feat_imp_S2.txt',sep = ' ',header = None, usecols= [2,4],index_col=0,names = ['feature','score_2']).sort_values(by = 'feature')
    #dfList2[3] = pd.read_csv('/server/Work/Users/Ron/Projects/LungCancer/results/model_14_matched_new_serialization/feat_imp_S3.txt',sep = ' ',header = None, usecols= [2,4],index_col=0,names = ['feature','score_3']).sort_values(by = 'feature')
    #tt2 = pd.merge(dfList2[0], dfList2[1], left_index=True, right_index=True, how = 'outer')
    #for split in range(2,4):
    #    tt2 = pd.merge(tt2, dfList2[split], left_index=True, right_index=True, how = 'outer')
    #timestr = time.strftime("%Y%m%d-%H%M%S")
    #tt2.to_csv(outDir + 'feature_imp_results' + timestr + '.csv', index = True, header = True)  
