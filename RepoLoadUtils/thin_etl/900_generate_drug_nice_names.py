
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import random
import math
import pandas as pd
import datetime
#from datetime.datetime import strptime

from IPython.display import display

d = pd.read_csv('/server/Work/Users/Ido/THIN_ETL/dictionaries/dict.drugs_defs', sep='\t', names = ['d', 'drug_id', 'drug_thin_id'])
s = pd.read_csv('/server/Work/Users/Ido/THIN_ETL/dictionaries/dict.drugs_sets', sep='\t', names = ['s', 'set_id', 'drug_thin_id'])
print (d.shape, s.shape)

drug_2_atc = s[s.set_id.apply(lambda x: str(x)[:3] == 'ATC')][['drug_thin_id', 'set_id']]
print(drug_2_atc.tail())

drugs = d[d.drug_thin_id.apply(lambda x: str(x)[:2] == "dc")]
drugs.loc[:, 'short_name'] = drugs.drug_thin_id.apply(lambda x: str(x)[2] != ':')
drugs_ids = drugs[drugs.short_name][['drug_id', 'drug_thin_id']]
drugs_desc = drugs[~drugs.short_name][['drug_id', 'drug_thin_id']]
drugs_desc.columns = ['drug_id', 'drug_desc']
drugs = pd.merge(drugs_ids, drugs_desc, on = 'drug_id')
print(drugs.tail())

print (drugs.groupby('drug_thin_id').size().value_counts())

atc = d[d.drug_thin_id.apply(lambda x: str(x)[:3] == "ATC")]
atc.loc[:, 'short_name'] = atc.drug_thin_id.apply(lambda x: len(str(x)) <= 13)
atc_ids = atc[atc.short_name][['drug_id', 'drug_thin_id']]
atc_ids.columns = ['atc_set_id', 'atc_set']
atc_desc = atc[~atc.short_name][['drug_id', 'drug_thin_id']]
atc_desc.columns = ['atc_set_id', 'atc_desc']
atc = pd.merge(atc_ids, atc_desc, on = 'atc_set_id')[['atc_set', 'atc_desc']]
print(atc.tail())

print(atc.groupby('atc_set').size().value_counts())

j = pd.merge(drugs,drug_2_atc, on = 'drug_thin_id')
j = pd.merge(j, atc, left_on = 'set_id', right_on = 'atc_set')
j = j.groupby('drug_id').first().reset_index()
print(j.shape)

j.loc[:, 'nice_name'] = j.drug_desc + ', ' + j.atc_desc
j.loc[:, 'd'] = 'DEF'

j[['d', 'drug_id', 'nice_name']].to_csv('/server/Work/Users/Ido/THIN_ETL/dictionaries/dict.drugs_nice_names', 
                                        sep = '\t', index = False, header = False)