#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import pandas as pd, numpy as np, os
from datetime import datetime
from  medial_tools.medial_tools import eprint, read_file, write_for_sure
from common import write_as_dict, rambam_str_to_dict

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/Ido/rambam_load/')
parser.add_argument('--limit_records', type=int, default=-1)
args = parser.parse_args()

# create MRF dict for all combinations of 'medicationcode', 'routecode', 'formcode'
all_drug = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/rambam_drugs', sep = '\t', limit_records=args.limit_records, dtype = str)

mrf = ['medicationcode', 'routecode', 'formcode']
for a in ['frequencycode', 'quantitiy_unitcode'] + mrf:
	dic = read_file(args.work_folder + '/raw_tables_extracted_from_xmls/dict.' + a, sep = '\t',
		names = [a, a + '_desc'], dtype=str)
	all_drug = all_drug.merge(dic, on = a, how = 'left')
	all_drug.fillna({a+'_desc': ''}, inplace=True)
all_drug.loc[:, 'quantity_value_orig'] = all_drug.quantity_value
all_drug.loc[all_drug.quantity_value == 'Null', 'quantity_value'] = -998
all_drug.loc[:, 'quantity_value'] = all_drug.quantity_value.astype(float)
all_drug.loc[:, 'mrf_code'] = 'DRUG:' + all_drug.medicationcode + '|' + all_drug.routecode + '|' + all_drug.formcode

# DRUG_ADMINISTERED_RATE is its own signal since we cant convert it to dosage (we dont have endtime)
rate_units = {'0: 2066662~1: ml/day':[1.0/24, '0: 798394~1: cc/h'],
			 '0: 2066663~1: lit/day':[1000.0/24, '0: 798394~1: cc/h'],
			 '0: 798394~1: cc/h': [1.0, '0: 798394~1: cc/h'], 
			 '0: 805152~1: mg/h': [1.0, '0: 805152~1: mg/h'],
			 '0: 2616119~1: U/h': [1.0, '0: 2616119~1: U/h']}
drug_rate = all_drug[all_drug.quantitiy_unitcode_desc.isin(rate_units.keys()) & (all_drug.ev_type == 'ev_medications_administered')]

# first try and consolidate some units with simple translations 
def consolidate_units(drug, tr):
	drug.loc[:, 'units_factor'] = drug.quantitiy_unitcode_desc.apply(lambda x: tr[x][0] if x in tr else 1.0)
	drug.loc[:, 'quantity_value'] = drug.quantity_value * drug.units_factor
	drug.loc[:, 'quantitiy_unitcode_desc'] = drug.quantitiy_unitcode_desc.apply(lambda x: tr[x][1] if x in tr else x)
	return drug
drug_rate = consolidate_units(drug_rate, rate_units)

# then remove values with unpopular units per MRF
def keep_only_most_popular_unit_per_mrf(drug):
	s = drug.groupby(mrf + [c + '_desc' for c in mrf] + ['quantitiy_unitcode_desc']).pid.count().reset_index(name = 'cnt_mrf_unit')
	s.loc[:, 'cnt_mrf'] = s.groupby(mrf).cnt_mrf_unit.transform('sum')
	s.loc[:, 'unit_pct_of_mrf'] = 1.0 * s.cnt_mrf_unit / s.cnt_mrf
	s = s.sort_values(mrf + ['unit_pct_of_mrf'], ascending=False)
	s_head = s.groupby(mrf).head(1)
	eprint('all entries [{0}] after dropping exotic quantitiy_unitcode entries [{1}]... '.format(s_head.cnt_mrf.sum(), s_head.cnt_mrf_unit.sum()))
	drug = drug.merge(s_head[mrf + ['quantitiy_unitcode_desc']], 
		on = mrf, how = 'left', suffixes = ['', '_largest'])
	drug.loc[drug.quantitiy_unitcode_desc_largest != drug.quantitiy_unitcode_desc, 'quantity_value'] = -999
	return drug, s
drug_rate, s = keep_only_most_popular_unit_per_mrf(drug_rate)
write_for_sure(s, args.work_folder + '/drug_rate_units.csv')
eprint(drug_rate.frequencycode_desc.value_counts()[:10])
drug_rate.loc[:, 'sig'] = 'DRUG_ADMINISTERED_RATE'
write_for_sure(drug_rate.sort_values(['pid', 'ev_time']), args.work_folder + '/repo_load_files/rambam_drugs_rate', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'ev_time', 'ev_time', 'mrf_code', 'quantity_value', 'quantity_value_orig', 'quantitiy_unitcode_desc', 'frequencycode_desc'])

# all other units are DRUG quantities, do the same for them
drug_quantity = all_drug[~all_drug.quantitiy_unitcode_desc.isin(rate_units.keys())]

amt_units = {'0: 7862~1: gr': [1000.0, '0: 7858~1: mg'], 
			'0: 7860~1: MCG': [0.001, '0: 7858~1: mg'],
			'0: 7857~1: ml': [1.0, '0: 7859~1: cc'],
			'0: 7861~1: Lit': [1000.0, '0: 7859~1: cc']
			}
drug_quantity = consolidate_units(drug_quantity, amt_units)
drug_quantity, s = keep_only_most_popular_unit_per_mrf(drug_quantity)
write_for_sure(s, args.work_folder + '/drug_quantity_units.csv')
eprint(drug_quantity.frequencycode_desc.value_counts()[:10])

# de-duplicate daily repeats, and multiply quantity by frequencycode 
# analysis showed that most of the entries are repeated daily exactly according to their frequencycode (1/d, 2/d, etc.), so we assume that's always should be the case
drug_quantity.loc[:, 'ev_date'] = drug_quantity.ev_time.apply(lambda x: str(x)[:10])
drug_quantity.loc[:, 'repeats_in_this_date'] = drug_quantity.groupby(['pid', 'ev_type', 'medicationcode', 'ev_date']).ev_time.transform('count')
drug_quantity = drug_quantity.sort_values(['pid', 'ev_time']).groupby(['pid', 'ev_type', 'medicationcode', 'ev_date']).head(1)
freq_to_factor = {'0: 877~1: 1/d':1.0,'0: 878~1: 2/d':2.0, '0: 879~1: 3/d':3.0, '0: 880~1: 4/d':4.0, '0: 881~1: 5/d': 5.0, '0: 7871~1: 6/d': 6.0}
drug_quantity.loc[:, 'frequencycode_factor'] = drug_quantity.frequencycode_desc.apply(lambda x: freq_to_factor[x] if x in freq_to_factor else 1.0)
drug_quantity.loc[drug_quantity.quantity_value > 0, 'quantity_value'] = drug_quantity.quantity_value * drug_quantity.frequencycode_factor

tr_sig_name = {'ev_medications_administered':'DRUG_ADMINISTERED', 'ev_medications_adm': 'DRUG_BACKGROUND', 'ev_medications_orders': 'DRUG_PRESCRIBED', 'ev_medications_recom': 'DRUG_RECOMMENDED', 'fake_key_just_so_val_can_be_here': 'DRUG_ADMINISTERED_RATE'}
drug_quantity.loc[:, 'sig'] = drug_quantity.ev_type.apply(lambda x: tr_sig_name[x])
write_for_sure(drug_quantity.sort_values(['pid', 'ev_time']), args.work_folder + '/repo_load_files/rambam_drugs', sep = '\t', index = False, header = False,
	columns = ['pid', 'sig', 'ev_time', 'ev_time', 'mrf_code', 'quantity_value', 'quantity_value_orig', 'quantitiy_unitcode_desc', 'frequencycode_desc'])

# extract ATC, routecode and formcode descriptions for every MRF in the dict
dc = all_drug.groupby(mrf + [c + '_desc' for c in mrf]).pid.count().reset_index(name = 'pid_count')

dc.loc[:, 'numeric_code'] = range(1000, 1000 + dc.shape[0])
dc.loc[:, 'mrf_code'] = dc.medicationcode + '|' + dc.routecode + '|' + dc.formcode

	
def extract_desc(x):
	desc = "DRUG:" + x["mrf_code"] 
	if "~" in x["medicationcode_desc"]:
		d = rambam_str_to_dict(x["medicationcode_desc"])
		desc += "_ATC:" + d[4] + "_DESC:" + d[5] + "_M:" + d[1]
	if "~" in x["routecode_desc"]:
		d = rambam_str_to_dict(x["routecode_desc"])
		desc += "_R:" + d[1]
	if "~" in x["formcode_desc"]:
		d = rambam_str_to_dict(x["formcode_desc"])
		desc += "_F:" + d[1]
	return desc
dc.loc[:, 'full_desc'] = dc.apply(extract_desc, axis = 1)

outme = pd.DataFrame({'numeric_code': dc.numeric_code, 'desc':'DRUG:' + dc.mrf_code, 'pri': 0})
outme = pd.concat([outme, pd.DataFrame({'numeric_code': dc.numeric_code, 'desc':'DRUG_DESC:' + dc.full_desc, 'pri': 1})])
write_as_dict(outme, "SECTION\t"+",".join(tr_sig_name.values()), args.work_folder + '/repo_load_files/dicts/dict.mrfcode')

# build ATC hierarchy 
seen_codes = set([])
defs = []
hier = []
i = 10000
def build_hier(x):
	global i
	if "~" not in x["medicationcode_desc"]:
		return
	prev_code = 'DRUG:' + x['mrf_code']
	d = rambam_str_to_dict(x["medicationcode_desc"])
	for lev in range(4,14,2):
		code = 'ATC:' + str(d[lev]) + 'DESC:' + str(d[lev+1])
		if code != prev_code:
			hier.append({'numeric_code': code, 'desc': prev_code, 'pri': 0})
		if code not in seen_codes:
			seen_codes.add(code)
			defs.append({'numeric_code': i, 'desc': code, 'pri': 0})
			i+=1
		prev_code = code
	return
print(dc.shape)
dc.apply(build_hier, axis = 1)		 

defs = pd.DataFrame(defs)
hier = pd.DataFrame(hier)
write_as_dict(defs, "SECTION\t"+",".join(tr_sig_name.values()), args.work_folder + '/repo_load_files/dicts/dict.atc_defs')
write_as_dict(hier, "SECTION\t"+",".join(tr_sig_name.values()), args.work_folder + '/repo_load_files/dicts/dict.atc_sets', prefix='SET')

