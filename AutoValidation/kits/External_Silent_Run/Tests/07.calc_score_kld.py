#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR']
DEPENDS=[6]
# End edit

import sys, os
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import pandas as pd

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

print(f'Please refer to {WORK_DIR} to see KLD diff')

eps=1e-4
df=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'score_dist.tsv'), sep='\t')
sim_p=df[df['Test']=='Reference'].reset_index(drop=True).drop(columns=['Test'])
sil_q=df[df['Test']=='Test_Run'].reset_index(drop=True).drop(columns=['Test'])
bins_sz,kld_res, kld_res_d, entropy_p =calc_kld(sim_p, sil_q, 'score', 'Percentage')

print('KLD (%d)= %f, KLD_to_Uniform=%f, entory_p=%f'%(bins_sz, kld_res, kld_res_d, entropy_p))
