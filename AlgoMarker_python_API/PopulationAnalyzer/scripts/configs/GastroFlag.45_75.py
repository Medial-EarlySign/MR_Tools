#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

from config import retrieve_config
from scripts.run_multiple import DATA_DIR, ERASE_README, OUTPUT_DIR, run_all
model_to_info = retrieve_config()

# End of imports
"""
GastroFlag
THIN, ages 45-75, 0-180,0-365 days prior to LGI disorder diagnosis 
W history and w/o history (CBC in 1 Y)
Tables: TW HC Norm	THIN	Medicare norm
"""

MODEL = "GastroFlag"  
thresholds_param = []

regions = ["UK-THIN"]
cohorts = ["Age Range: 45-75, Time-window: 365", "Age Range: 45-75, Time-window: 180"]

data_manipulations = [
    {"CBC - Include All History": "CBC - Include All History"},
    {"CBC - Include 3 Years": "CBC - Include 3 Years"},
    {"CBC - Only Most Recent Measurement": "CBC - Only Most Recent Measurement"},
]
strata_data_opts = [
    os.path.join(DATA_DIR, "strats.simple.all.csv"),
    os.path.join(DATA_DIR, "final_data", "stratas.TW_HC_NORM.csv"),
    os.path.join(DATA_DIR, "final_data", "stratas.Medicare_NORM.csv"),
]

# End of params

run_all(OUTPUT_DIR, MODEL, model_to_info, ERASE_README, regions, cohorts,
        strata_data_opts, data_manipulations, thresholds_param)