#!/usr/bin/env python
import sys, os
sys.path.insert(0, os.environ['ETL_LIB_PATH']) #Add common to path
import pandas as pd
from etl_process import *
from file_api_parser import *

#Initialize Environment parameters from env.sh file:
sys.path.insert(0, os.path.join(os.environ['AUTOTEST_LIB'], 'resources') )
from lib.PY_Helper import *
init_env(sys.argv, locals())
#Test for parameters
REQ_PARAMETERS=['WORK_DIR', 'SILENCE_RUN_INPUT_FILES_PATH']
res=test_existence(locals(), REQ_PARAMETERS , TEST_NAME)
if not(res):
    sys.exit(1)

#Start ETL
ORIG_WORK_DIR=WORK_DIR
WORK_DIR=os.path.join(WORK_DIR, 'ETL')
os.makedirs(WORK_DIR, exist_ok=True)
#If true, the batching will be by reading file rows and not by reading files. Usefull when single file can't fit into memory
very_big_file_split_by_rows=False
batch_sz=0 # 0 means no batching - read all and process all data together.

#Load All - all signals are in the same "data source" format:
#First load demographic:
#prepare_final_signals(data_fetcher_file_api(SILENCE_RUN_INPUT_FILES_PATH, batch_file_rows=very_big_file_split_by_rows), WORK_DIR,\
#                      'GENDER,BDATE,MEMBERSHIP', batch_size=batch_sz, editor = None, map_editor=None, override='n', interactive=False)
#Load all the rest
#all_signals='smoking,labs,DIAGNOSIS,DEATH,cancer_registry'
all_signals='all'
succ=prepare_final_signals(data_fetcher_file_api(SILENCE_RUN_INPUT_FILES_PATH, batch_file_rows=very_big_file_split_by_rows), WORK_DIR,\
                      all_signals, batch_size=batch_sz, editor = None, map_editor=None, override='n', interactive=False)

if not(succ):
    raise NameError('Failed!')
#if Cancer is given by "codes" and we need to map codes into meaning: (can be also done after loading)
#prepare_dicts(WORK_DIR, 'Cancer_Location', pd.read_csv(os.path.join(os.path.dirname(__file__), 'configs', 'cancer_map.tsv'), sep='\t'))

#Finalize:
finish_prepare_load(WORK_DIR, os.path.join(ORIG_WORK_DIR, 'rep'), 'test')

