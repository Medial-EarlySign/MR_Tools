# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 14:02:12 2018

@author: Ron
"""

import numpy as np

class Matcher():
    def calcRatios(self,dfFeatures,feat,bins_edges):    
        n_controls,_ = np.histogram(dfFeatures.loc[dfFeatures.label == 0,[feat]], bins = bins_edges)
        n_cases,_ = np.histogram(dfFeatures.loc[dfFeatures.label == 1,[feat]], bins = bins_edges)
        return n_controls, n_cases
    
    def calcOptimalRatio(self,n_controls, n_cases, w = 100):
        # check price:
        ratio = n_controls/n_cases
        
        # cnt_cases, cnt_controls  - counter to throw
        opt_price = np.inf
        opt_r = 0
        for r in sorted(ratio):
            if not((r == r) & (r !=np.inf)):
                print('ratio: not valid, skipped')
                continue
            cnt_cases = 0
            cnt_controls = 0
            
            for k in range(len(n_controls)):
                if n_controls[k] == 0:
                    cnt_cases += n_cases[k]
                elif n_cases[k] == 0:
                    cnt_controls += n_controls[k]
                else:
                    iratio = n_controls[k]/n_cases[k]
                    if iratio > r:
                        cnt_controls += n_controls[k] - np.ceil(n_cases[k]*r)
                    else:
                        cnt_cases += n_cases[k] - np.ceil(n_controls[k]/r)
            
            cnt_cases = max(cnt_cases,0)
            cnt_controls = max(cnt_controls,0)
            
            curr_price = cnt_cases*w + cnt_controls
            print("ratio: {r}, cnt_cases: {cnt_cases}, cnt_controls: {cnt_controls}, price: {curr_price}".format( r=r, cnt_cases = cnt_cases, cnt_controls = cnt_controls, curr_price=curr_price))
            if curr_price < opt_price:
                opt_price = curr_price
                opt_r = r
        
        return opt_r
                
    def _match(self,opt_r , bins_edges, dfFeatures, feat):
        control_ind_agg = []
        cases_ind_agg = []
        for k in range(len(bins_edges)-1):
            low_edge = bins_edges[k]
            upper_edge = bins_edges[k +1]
            
            
            ind_values = (dfFeatures[feat].between(low_edge,upper_edge))
            controls_ind_bool = (dfFeatures.label == 0) & ind_values
            cases_ind_bool = (dfFeatures.label == 1) & ind_values
            num_cases = np.sum(cases_ind_bool)
            num_controls = np.sum(controls_ind_bool)
            if (num_cases == 0) | (num_controls == 0):
                print("SKIPPED: bin: {low_edge},{upper_edge}, num_cases: {num_cases}, num_controls: {num_controls}".format(low_edge = low_edge, upper_edge = upper_edge,num_cases = num_cases, num_controls = num_controls))
                continue

            control_ind = dfFeatures[controls_ind_bool].index.values
            cases_ind = dfFeatures[cases_ind_bool].index.values
            
            if num_controls/num_cases >= opt_r:        
                np.random.shuffle(control_ind)
                
            else:
                np.random.shuffle(cases_ind)
        
            controls_add = control_ind[0:min(num_controls,int(np.ceil(num_cases*opt_r)))]
            cases_add = cases_ind[0:min(num_cases,int(np.ceil(num_controls/opt_r)))]
            print("bin: {low_edge},{upper_edge}, ratio: {curr_ratio}".format(low_edge = low_edge, upper_edge = upper_edge,curr_ratio = len(controls_add)/len(cases_add )))
            control_ind_agg = np.append(control_ind_agg,controls_add)
            cases_ind_agg = np.append(cases_ind_agg,cases_add)
            
        return control_ind_agg, cases_ind_agg
    
    def match(self,dfFeatures,feat,bins_edges, w = 100 ):
        n_controls,n_cases = self.calcRatios(dfFeatures,feat, bins_edges)
        opt_r = self.calcOptimalRatio(n_controls, n_cases, w)
        control_ind_agg, cases_ind_agg = self._match(opt_r , bins_edges, dfFeatures, feat)
        return control_ind_agg, cases_ind_agg 
        

#if __name__ == '__main__':      
#    samples_file = '/server/Work/Users/Ron/Projects/AAA/aaa_testMatched.samples'
#    dfSamples = pd.read_csv(samples_file , sep = '\t')
#    dirName =  ('/server/Work/Users/Ron/Projects/AAA/results/model_4_gen_matrix/')
#    #filesListTrain = [dirName + 'model_4_gen_matrix_x_0.csv', dirName + 'model_4_gen_matrix_x_1.csv',dirName + 'model_4_gen_matrix_x_2.csv',dirName + 'model_4_gen_matrix_x_3.csv']
#    #filesListVal = [dirName + 'model_4_gen_matrix_test_x_0.csv', dirName + 'model_4_gen_matrix_test_x_1.csv',dirName + 'model_4_gen_matrix_test_x_2.csv',dirName + 'model_4_gen_matrix_test_x_3.csv']
#    dfFeatures = pd.read_csv(dirName + 'model_4_gen_matrix_test_x_0.csv')
#    
#    signal = 'Age'
#    value_bins = np.arange(45,120)
#    w = 100
#    
#    delta = (value_bins[1] - value_bins[0])
#    bins_edges = np.append((value_bins - delta/2) , [value_bins[-1] + delta/2])
#    
