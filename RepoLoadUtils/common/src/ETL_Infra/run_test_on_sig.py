#!/usr/bin/env python
import sys, argparse
import pandas as pd
import numpy as np
from ETL_Infra.define_signals import load_signals_map
from ETL_Infra.dict_utils import load_final_sig
from ETL_Infra.test_signals import test_df

from ETL_Infra.env import *

parser = argparse.ArgumentParser(description = "Run test on signal")
parser.add_argument("--workdir",help="workdir", required=True)
parser.add_argument("--codedir",help="codedir", required=True)
parser.add_argument("--signal",help="signal", default='Hemoglobin')

args = parser.parse_args() 

codedir=args.codedir
workdir=args.workdir
sig_name=args.signal

sig_types=load_signals_map(FULL_SIGNALS_TYPES, codedir)
sig_list=sig_name.split(',')
for sig in sig_list:
    print(f'Loading final signal {sig}', flush=True)
    df_final = load_final_sig(workdir, sig_types, sig)
    test_df(df_final, sig, sig_types, None, workdir, codedir)
