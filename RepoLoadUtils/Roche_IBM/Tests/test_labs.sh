#!/bin/bash
mkdir -p /mnt/work/LGI/loading_files/outputs/lab_signals
SignalPrinter --rep /mnt/work/Repositories/IBM/ibm.repository --signal_name ALL --test_args "unit_diff_threshold=5;unit_factor_threshold=3;res_threshold=0.001;res_factor_threshold=0.3;res_tails_ignore=0.05;res_min_diff_num=100;res_max_allowed_peaks=5" --output /mnt/work/LGI/loading_files/outputs/lab_signals | tee /mnt/work/LGI/loading_files/outputs/lab_signals/run.log
