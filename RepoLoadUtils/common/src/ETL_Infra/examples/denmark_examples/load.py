#!/usr/bin/env python
import os
import pandas as pd
from ETL_Infra.etl_process import *
from denmark_parser import generic_file_fetcher, labs_data_fetcher
#END of imports

WORK_DIR='/nas1/Work/Users/Alon/LungCancer/External_Validation/Denmark/outputs/ETL' # where we are going to work
FINAL_REP_PATH='/nas1/Work/CancerData/Repositories/Denmark' #Final repository path
#End of environment setup

# Process Loading files
batch_size=0
prepare_final_signals(generic_file_fetcher('Pop2_datasetA\.'), WORK_DIR, \
                      'GENDER,BDATE,measurements,smoking,FEV1,cancer_registry,INDEX_DATE', batch_size, override='n')

prepare_final_signals(labs_data_fetcher, WORK_DIR, 'labs', batch_size, override='n')

prepare_final_signals(generic_file_fetcher('Pop2_DatasetD_comorbidity'), WORK_DIR, 'DIAGNOSIS', \
                      batch_size, start_write_batch=10, override='n')

prepare_final_signals(generic_file_fetcher('overlap171priorLC_ifkeepallLC'), WORK_DIR, 'additional_cancers',\
                      batch_size, start_write_batch=11, override='n')

#External Dicts if we have:
prepare_dicts(WORK_DIR, 'Cancer_Pathology', pd.read_csv(os.path.join( os.path.dirname(__file__), \
                                                                      'configs', 'pathology_dict.tsv'), sep='\t'))

#Finalize
finish_prepare_load(WORK_DIR, FINAL_REP_PATH, 'denmark')
