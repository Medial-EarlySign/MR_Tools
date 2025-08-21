#!/usr/bin/env python
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)

from config import retrieve_config
from scripts.run_multiple import DATA_DIR, ERASE_README, OUTPUT_DIR, run_all

model_to_info = retrieve_config()

# End of imports
"""
LungFlag
KPSC, ages 50-80 USPSTF, 90-365 days prior to LungCancer diagnosis 
Tables: G USPSTF N-MDCR	KPSC	MDCR x USPSTF norm
"""

MODEL = "LungFlag"
thresholds_param = []

regions = ["US-KP"]
cohorts = ["USPSTF Age 50-80 (20 pack years, less then 15 years quit)"]

data_manipulations = [{"Smoking": True, "Labs": True, "BMI": True, "Spirometry": True}]
strata_data_opts = [
    os.path.join(DATA_DIR, "strats.simple.all.csv"),
    os.path.join(DATA_DIR, "final_data", "stratas.G_USPSTF_N_MDCR.csv"),
    os.path.join(DATA_DIR, "final_data", "stratas.MDCR_X_USPSTF_NORM.csv"),
]

# End of params

run_all(
    OUTPUT_DIR,
    MODEL,
    model_to_info,
    ERASE_README,
    regions,
    cohorts,
    strata_data_opts,
    data_manipulations,
    thresholds_param,
)
