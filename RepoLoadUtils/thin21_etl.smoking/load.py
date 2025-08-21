import sys, os
sys.path.insert(0,'/nas1/UsersData/eitan/MR/Tools/RepoLoadUtils/common/ETL_Infra') #Add common to path
import pandas as pd
import numpy as np
from etl_process import *
from etl_loading_status import *
from helper import *
#END of imports
 
WORK_DIR='/nas1/Work/Users/Eitan/thin_2021_loading' # where we are going to work
logfile = WORK_DIR + '/log.txt'
 
#init - load defined signals from global + generate empty template file for defining more
# signals in first run time, or load additional signals definitions from WORK_DIR
sig_types = read_signals_defs(workdir=WORK_DIR) #The first method you need to remember from etl_process library
 
#Read data - your specific code of reading part of data - to be improved to have an ability/API to fetch batch from the data, wrapper to file system, DB, etc.
DATA_DIR='/nas1/Data/THIN2101/THINDB2101'

# Demography
sigs='demographic'
#map_fetch_and_process(thin_patient_data_fetcher, WORK_DIR, sigs, batch_size=1, editor = 'vim', map_editor='gedit', override='y')
    
# smoking
sigs='smoking'
#map_fetch_and_process(thin_smoking_data_fetcher, WORK_DIR, sigs, batch_size=1, editor = None, map_editor='gedit', override='y')

# medical
sigs = 'DIAGNOSIS'
# map_fetch_and_process(thin_medical_data_fetcher, WORK_DIR, sigs, batch_size=1, editor = None, map_editor='gedit', override='y')

# ahd/labs
sigs = "labs"
map_fetch_and_process(thin_ahd_lab_data_fetcher, WORK_DIR, sigs, batch_size=1, editor = None, map_editor='gedit', override='y')
  
#example of handling specific signal
#df_hgb=df[df['signal']=='Hemoglobin'].copy()
#fetch_signal(df_hgb, 'Hemoglobin', WORK_DIR, sig_types, editor = '/home/apps/thonny/bin/thonny', override='n')