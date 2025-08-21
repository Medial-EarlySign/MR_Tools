#!/usr/bin/env python
import os
import pandas as pd
from ETL_Infra.etl_process import *
from parser import generic_file_fetcher, big_data_fetcher

# END of imports

WORK_DIR = ""  # where we are going to work and output results of tests
FINAL_REP_PATH = ""  # Final repository path
# End of environment setup

# Process Loading files - 1 by 1
batch_size = 1
prepare_final_signals(
    generic_file_fetcher(".*"), WORK_DIR, "data", batch_size, override="n"
)


# Finalize
finish_prepare_load(WORK_DIR, FINAL_REP_PATH, "test")
