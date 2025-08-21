#!/nas1/Work/python-env/python38/bin/python
# prepare dictionaries for drugs in trinetx
from	Configuration	import	Configuration
import	os,sys
import	pandas	as	pd
import	numpy	as	np
from	datetime	import	datetime
sys.path.insert(0,	'/nas1/UsersData/'+os.getlogin()+'/MR/Tools/RepoLoadUtils/common')
from dicts_utils import create_dict_generic

def	create_drugs_dict(cfg):
	def_dicts=['dict.defs_rx',	'dict.atc_defs','dict.ndc_defs']
	set_dicts=['dict.atc_sets',	'dict.set_atc_rx','dict.atc_ndc_set']
	#header=['pid',	'signal',	'start_date',	'end_date',	'rx_cui',	'std_ordering_mode',	'std_order_status',	'std_quantity']
	#header=["patient_id","code","start_date"]
	header=["patient_id","signal","start_date","code"]
	#to_use_list=['rx_cui',	'std_ordering_mode',	'std_order_status']
	to_use_list=['code']
	create_dict_generic(cfg,	def_dicts,	set_dicts,	'Drug',	'Drug',	header,	to_use_list)

cfg	=Configuration()

create_drugs_dict(cfg)

