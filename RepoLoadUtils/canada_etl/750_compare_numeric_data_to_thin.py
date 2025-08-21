from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import pandas as pd
import glob
from medial_tools.medial_tools import eprint, read_file, write_for_sure
import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import plot
from plotly.graph_objs import XBins

parser = argparse.ArgumentParser()
parser.add_argument('--thin_folder', default='/server/Temp/Thin_2017_Loading/')
parser.add_argument('--canada_folder', default='/server/Work/Users/Ido/canada_122017_loading/')
parser.add_argument('--thin_instructions_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/Instructions.txt')
parser.add_argument('--thin_codes_to_signals_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/codes_to_signals')
parser.add_argument('--canada_limit_records', type=int, default=-1)
parser.add_argument('--thin_limit_records', type=int, default=100000)
parser.add_argument('--sig_substring', type=str, default='')
args = parser.parse_args()

canada1 = read_file(args.canada_folder + '/numeric_lab_data', names=['pid', 'sig', 'date', 'val', 'orig_sig', 'uom', 'orig_val'], sep = '\t', 
	dtype={'pid':int, 'date': int, 'val': float}, na_values=['bbb'], limit_records=args.canada_limit_records) 
canada1.loc[:, 'source'] = 'LAB_DATA'
canada2 = read_file(args.canada_folder + '/numeric_vital_data', names=['pid', 'sig', 'date', 'val', 'orig_sig', 'uom', 'orig_val'], sep = '\t', 
	dtype={'pid':int, 'date': int, 'val': float}, na_values=['bbb'], limit_records=args.canada_limit_records) 
canada2.loc[:, 'source'] = 'VITAL_DATA'
canada3 = read_file(args.canada_folder + '/panel_completer_completed.csv', names=['pid', 'sig', 'date', 'val', 'orig_sig'], sep = '\t', 
	dtype={'pid':int, 'date': int, 'val': float}, na_values=['bbb'], limit_records=args.canada_limit_records) 
canada3.loc[:, 'source'] = 'PANEL_COMPLETER'

canada = pd.concat([canada1, canada2, canada3])

canada.fillna('NA', inplace=True)

thin_instructions = read_file(args.thin_instructions_file, sep = '\t')
thin_codes_to_signals = read_file(args.thin_codes_to_signals_file, sep = '\t', names=['thin_name', 'sig'])

def dict_with_main_stats(df, suffix):
	units = df.uom.value_counts() / df.uom.count()
	return {"sig": sig, "count" + suffix: df.val.count(), "mean" + suffix: df.val.mean(), "median" + suffix: df.val.quantile(.5), "std" + suffix: df.val.std(), "units" + suffix: units[units > 0.1]}
def sample_if_not_empty(series, sample_size):
	if series.empty:
		return series
	else:
		return series.sample(min(sample_size, series.size), replace=True)
			
thin_plots = {}
thin_records = []
xbins = {}
my_files = []
for t in [args.thin_folder + '/Fixed/*', args.thin_folder + '/clinical/*GHT', args.thin_folder + '/clinical/BMI', args.thin_folder + '/Completions/thin_completed.csv']:
	my_files.extend(glob.glob(t))
for f in my_files:
	if args.sig_substring.lower() not in f.lower() and 'thin_completed' not in f.lower():
		continue
	thin = read_file(f, sep = '\t', names=['pid', 'sig', 'date', 'val', 'orig_sig', 'uom'], dtype={'pid':int, 'date': int, 'val': float}, 
		na_values=[''], limit_records=args.thin_limit_records)
	thin.fillna('NA', inplace=True)
	for sig in thin.sig.unique():
		if args.sig_substring.lower() not in sig.lower():
			continue
		eprint("thin", sig)
		cur_thin = thin[thin.sig == sig]
		final_unit = thin_instructions[thin_instructions.Name == sig].FinalUnit.min()
		if sig in thin_codes_to_signals.thin_name.values:
			new_sig = thin_codes_to_signals[thin_codes_to_signals.thin_name == sig].sig.min()
			eprint('converting thin_name [{0}] to sig [{1}]'.format(sig, new_sig))
			sig = new_sig
		if sig not in xbins:
			xbins[sig] = XBins(start = cur_thin.val.quantile(.01), end = cur_thin.val.quantile(.99), size = (cur_thin.val.quantile(.99) - cur_thin.val.quantile(.01))/100.0)
			d = dict_with_main_stats(cur_thin, "_thin")
			d["units_thin"] =  final_unit
			thin_records.append(d)
			thin_plots[sig] = []
		thin_plots[sig].append(go.Histogram(x=sample_if_not_empty(cur_thin.val, 10000), histnorm='probability', xbins=xbins[sig], name='thin_' + str(cur_thin.orig_sig.max())))
thin_df = pd.DataFrame(thin_records)

canada_plots = {}
canada_records = []
for sig in canada.sig.unique():
	if args.sig_substring.lower() not in sig.lower():
		continue
	eprint("canada", sig)
	cur_canada = canada[canada.sig == sig]
	if sig not in xbins:
		xbins[sig] = XBins(start = cur_canada.val.quantile(.01), end = cur_canada.val.quantile(.99), size = (cur_canada.val.quantile(.99) - cur_canada.val.quantile(.01))/100.0)
	d = dict_with_main_stats(cur_canada, "_canada")
	canada_records.append(d)
	canada_plots[sig] = [go.Histogram(x=sample_if_not_empty(cur_canada.val, 10000), histnorm='probability', xbins=xbins[sig], name='canada')]
	def print_all(x):
		source, orig_sig, uom = x['source'], x['orig_sig'], x['uom']
		eprint(source, orig_sig, uom)
		my_slice = cur_canada[(cur_canada.orig_sig == orig_sig) & (cur_canada.uom == uom) & (cur_canada.source == source)]
		my_slice_size = 1.0 * my_slice.shape[0] / cur_canada.shape[0]
		if my_slice_size > 0.05:
			canada_plots[sig].append(go.Histogram(x=sample_if_not_empty(my_slice.val, 10000), histnorm='probability', xbins=xbins[sig], name=str(source) + '_' + str(orig_sig) + '_' + str(uom) + ":" + 
				str(my_slice_size)))
	cur_canada[['source', 'orig_sig', 'uom']].drop_duplicates().apply(print_all, axis = 1)
canada_df = pd.DataFrame(canada_records)

compare_df = pd.merge(thin_df, canada_df, on = 'sig', how = 'outer')
compare_df.loc[:, 'dist'] = (compare_df.mean_thin - compare_df.mean_canada).abs() / compare_df.std_thin
for sig in compare_df.sig.values:
	eprint("plotting", sig)
	figs = []
	if sig in thin_plots:
		figs.extend(thin_plots[sig])
	if sig in canada_plots:
		figs.extend(canada_plots[sig])
	layout = go.Layout(showlegend=True)
	fig = go.Figure(data=figs, layout=layout)
	plot(fig, filename= args.canada_folder + "/plots/{0}.html".format(sig,), auto_open=False)

write_for_sure(compare_df.sort_values('dist', ascending = False), args.canada_folder + "/stats/compare_numeric_data_thin_canada.csv", index=False)
	

