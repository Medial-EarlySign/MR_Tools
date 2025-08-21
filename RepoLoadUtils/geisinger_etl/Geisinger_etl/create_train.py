import os, sys
from Configuration import Configuration
#sys.path.append(os.path.join('/opt/medial/tools/bin/', 'RepoLoadUtils','common'))
sys.path.append('/opt/medial_sign/med_scripts/ETL/common')
from train_signal import create_train_signal

cfg=Configuration()
create_train_signal(cfg, ['/opt/medial_sign/LOADING_PROCESS/geisinger_load_2021/TRAIN'])

