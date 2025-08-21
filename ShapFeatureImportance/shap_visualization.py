# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 15:05:30 2020

@author: ron-internal
"""
import sys
sys.path.insert(0,'/nas1/Work/Users/Ron/tmp/py_pkg/')
import matplotlib
# matplotlib.use('Agg',force = True)
import argparse, pandas as pd,re,shap
import matplotlib.backends.backend_pdf
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--in_tsv', metavar = '', default= '', help = 'Input but why ')
parser.add_argument('--out_pdf', metavar = '', default= '', help = 'ouptput pdf')
parser.add_argument('--max_plots',type = int, metavar = '', default= 10, help = 'max_plots')
parser.add_argument('--ids_list', metavar = '', default= '', help = 'pids. comma delimited')
args = parser.parse_args()

# args.in_tsv = '/server/Work/Users/Ron/tmp/test_explainers.tree_iterative_cov.report.tsv'
# args.out_pdf = '/server/Work/Users/Ron/tmp/test3.pdf'
# args.ids_list = '5877353,7021577'
# args.max_plots = 5

args.pids = args.ids_list.split(',')

# pid_data = in_df.loc[in_df.pid == '20797027',:]

in_df = pd.read_csv(args.in_tsv ,sep = '\t', usecols = [0,1,2,3,4,5])
in_df.rename({in_df.columns[4] : 'shap_value', in_df.columns[5] : 'feature_value'}, axis = 1, inplace = True)

# pdf = matplotlib.backends.backend_pdf.PdfPages( args.out_pdf )
ind = 0
def convert_to_shap_format(pid_data):
    # print(pid_data.to_string())
    cols = []
    shap_values= np.array([])
    fig = plt.figure()
    for i,row in pid_data.iterrows():
        t1 = re.search('(.*):=(.*)\(', row.shap_value,re.IGNORECASE) # first part of name + shap
        if (row.feature_value == row.feature_value):
            t2 = re.search('.*?\.(.*)\.(.*)\((.*)\):=', row.feature_value, re.IGNORECASE)
            cols = cols + [t1.group(1) + '\n' + t2.group(1)+ '\n' + t2.group(2) + '\n' + '('+ t2.group(3)+ ')']
        else:
            cols = cols + [t1.group(1)]
        shap_values = np.append(shap_values, float(t1.group(2)))
    
    log_odds= np.log(float(row.pred_0)/(1 - float(row.pred_0)))
    dummy_bias = log_odds - shap_values.sum()
    shap.force_plot(dummy_bias, shap_values, feature_names = cols, matplotlib = True,figsize =(20,5) )
    txt = f"ID: {row.pid}, time:{row.time}"
    plt.text(0.001,0.1,txt, transform=fig.transFigure, size=24)
    plt.show()
    # pdf.savefig( plt.gcf(),bbox_inches='tight', pad_inches = 1)

        
in_df = in_df.loc[in_df.pid.str.isnumeric(),:]
if len(args.pids) > 0:
    in_df = in_df[in_df.pid.isin(args.pids)]
else:
    in_df = in_df[in_df.pid.isin(in_df.pid.unique()[0:args.max_plots])]
gb = in_df.groupby('pid')
gb.apply(convert_to_shap_format)
# pdf.close()
        