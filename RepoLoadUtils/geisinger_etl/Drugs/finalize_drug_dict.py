#!/opt/medial/dist/usr/bin/python
import sys
import pyreadstat
import numpy as np
import pandas as pd
import time
import re

###################################
## globals
###################################
ndc_key = 'NDC2'


#############################################################################
### functions
#############################################################################
# parses the ndc and adds a (int):(int) representation on its 2 first fields as
# key. We need this to work in all tables
def add_ndc_key(df, ndc_col, key_col, sp='-'):
	h_col = "split_my_ncd"
	df_new = df[ndc_col].str.split(sp, expand=True)
	
	df[key_col] = df_new[0].str.lstrip('0')+":"+df_new[1].str.lstrip('0')
	#df[key_col] = df_new[key_col]
	#print(df_new)
	
def prep_dict_from_cols(df, col1, col2):
	d = {}
	for i,row in df.iterrows():
		k = row[col1]
		v = row[col2]
		k.rstrip('\n')
		v.rstrip('\n')
		if (k in d.keys()):
			print("DUPLICATE!!!====>", col1 , " <=> " , k , v , d[k])
			if (not "MISSING" in v):
				# means we have to add it after removing all MISSING
				to_del = []
				for w in d[k]:
					if ("MISSING" in w):
						to_del.append(w)
				for w in to_del:
					d[k].remove(w)
				d[k].add(v)
			print("after fix: d[k] is: ", d[k])
		else:
			d[k] = set([v])
	return d

def prep_dict_from_cols_simple(df, col1, col2):
	d = {}
	for i,row in df.iterrows():
		k = row[col1]
		v = row[col2]
		k.rstrip('\n')
		v.rstrip('\n')
		if (k in d.keys()):
			d[k].add(v)
		else:
			d[k] = set([v])			
	return d
	
#############################################################################
#### M A I N 
#############################################################################

def main(argv):
	drug_names_file = sys.argv[1]
	ndc2atc_file = sys.argv[2]
	kp_names_file = sys.argv[3]

	# reading all files to pandas

	df_names = pd.read_csv(drug_names_file, sep='\t', header=None, names=["Count","NDC","Drug_Name"])
	df_ndc2atc = pd.read_csv(ndc2atc_file, sep='\t', header=None, names=[ndc_key,"ATC"])
	df_name_id = pd.read_csv(kp_names_file, sep='\t') # drug_name, drugid
	df_names = df_names.astype(str)
	df_ndc2atc = df_ndc2atc.astype(str)
	df_name_id = df_name_id.astype(str)

	add_ndc_key(df_names,'NDC',ndc_key)
	df_names = df_names.astype(str)
	
	d_names2id = prep_dict_from_cols(df_name_id, "drug_name", "drugid")
	d_names2ndc = prep_dict_from_cols(df_names, "Drug_Name", ndc_key)
	d_ndc2atc = prep_dict_from_cols_simple(df_ndc2atc, ndc_key, "ATC")
	
	# ready for work, going over official names and preparing the dictionary
	for i,row in df_name_id.iterrows():
		name = row['drug_name']
		name.rstrip('\n')
		id = row['drugid']
		if (name in d_names2ndc.keys()):
			ndcs = d_names2ndc[name]
			non_miss = set([])
			for	ndc in ndcs:
				if (not "MISSING" in ndc):
					non_miss.add(ndc)
			if (len(non_miss) > 0):
				ndcs = non_miss
			atcs = set([])
			for ndc in ndcs:
				if (ndc in d_ndc2atc.keys()):
					for w in d_ndc2atc[ndc]:
						atcs.add(w)
				else:
					print("MISSING NDC ERROR:", ndc , name)
			print("MAP\t%s\t%s\t%s\t%s" % (name, id, ndcs, atcs))
		else:
			print("MISSING NAME ERROR: ", "#"+name+"#")
			sys.exit(1)
	
if __name__ == "__main__":
	main(sys.argv[1:])
