#!/usr/bin/env python
"""
A Script to run multiple, cross join analysis for a model with script

LGI-Flag 
THIN, ages 45-75, 0-180,0-365 days prior to LGI disorder diagnosis 
W history and w/o history (CBC in 1 Y)
Tables: TW HC Norm	THIN	Medicare norm

GastroFlag
THIN, ages 45-75, 0-180,0-365 days prior to LGI disorder diagnosis 
W history and w/o history (CBC in 1 Y)
Tables: TW HC Norm	THIN	Medicare norm

LGI-Flag 
THIN, ages 40-90, 0-180,0-365 days prior to LGI disorder diagnosis 
W history and w/o history (CBC in 1 Y)
Tables: TW HC Norm	THIN	JP Norm

GastroFlag
THIN, ages 40-90, 0-180,0-365 days prior to LGI disorder diagnosis 
W history and w/o history (CBC in 1 Y)
Tables: TW HC Norm	THIN	JP Norm

LungFlag
THIN, EVER Smokers, ages 40-89, 90-365 days prior to LungCancer disorder diagnosis 
Tables: TW HC ES norm	THIN	MDCR x USPSTF norm

LungFlag
KPSC, ages 50-80 USPSTF, 90-365 days prior to LungCancer diagnosis 
Tables: G USPSTF N-MDCR	KPSC	MDCR x USPSTF norm

"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from typing import Dict, List
import pandas as pd
from tqdm import tqdm
from config import retrieve_config
from file_csv_parser import parse_file_content
from logic import StrataStats, full_run, get_incidence
from logic_med import (
    ReferenceInfo_minimal,
    get_final_scores,
    process_res,
    norm_names_lower,
    filter_data_bt,
)
from models import ModelInfo
import asyncio


def get_strata_data(strata_file_path: str) -> List[StrataStats]:
    MIN_OBS = 200
    with open(strata_file_path, "r") as file_reader:
        file_content = file_reader.read()
        strata_data = parse_file_content(file_content, min_obs=MIN_OBS)
    return strata_data


def get_results_for_settings(
    specific_model_info: ModelInfo,
    region: str,
    cohort: str,
    strata_data: List[StrataStats],
    missing_signals_options: Dict[str, str | bool],
    thresholds_values: List[float] | None = None,
    top_n_value: List[int] | None = None,
    selected_model_data: pd.DataFrame | None = None,
) -> pd.DataFrame:

    print(f"Read {specific_model_info.model_name} for region {region}")
    if selected_model_data is None:
        selected_model_data = pd.read_csv(
            specific_model_info.model_references[region].matrix_path
        )
        selected_model_data = norm_names_lower(selected_model_data)
    found_cohorts = list(
        filter(
            lambda x: x.cohort_name == cohort,
            specific_model_info.model_references[region].cohort_options,
        )
    )
    assert len(found_cohorts) == 1
    cohort_info = found_cohorts[0]
    bt_filter = cohort_info.bt_filter
    selected_model_data_filter = selected_model_data.copy()
    len_before = len(selected_model_data_filter)
    selected_model_data_filter = filter_data_bt(selected_model_data_filter, bt_filter)
    len_after = len(selected_model_data_filter)
    print(
        f"After filtering cohort left with {len_after}, was {len_before} - removed {len_before - len_after}({100*(len_before - len_after)/len_before:2.2f}%)"
    )

    sample_per_pid = specific_model_info.sample_per_pid
    control_weight = specific_model_info.model_references[region].control_weight
    cases_weight = None
    incidence_ref = get_incidence(
        selected_model_data_filter,
        sample_per_pid,
        control_weight,
        cases_weight,
        SET_COHORT_SIZE,
    )
    if thresholds_values is None:
        thresholds_values = []
    if top_n_value is None:
        top_n_value = []
    # Prepare model if not in cache:
    cache_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "cache"
    )
    reference_info = ReferenceInfo_minimal(
        repository_path=specific_model_info.model_references[region].repository_path,
        model_cv_path=specific_model_info.model_references[region].model_cv_path,
        model_cv_format=specific_model_info.model_references[region].model_cv_format,
    )
    selected_model_data_filter, mask = asyncio.run(
        get_final_scores(
            selected_model_data,
            selected_model_data_filter,
            cache_dir,
            specific_model_info.model_name,
            specific_model_info.model_path,
            region,
            cohort,
            reference_info,
            missing_signals_options,
            specific_model_info.signals_info,
        )
    )

    res, prob_not_represented = full_run(
        selected_model_data_filter,
        strata_data,
        None,
        control_weight,
        cases_weight,
        sample_per_pid,
        top_n_value,
        thresholds_values,
    )
    res, npos, nneg = process_res(res)
    general_text = (
        f"Note: cohort has {npos:1.0f} cases and {nneg:1.0f} controls, incidence is {100*npos/(npos+nneg):2.2f}%"
        f" reference cohort incidence before matching was {100*incidence_ref:2.2f}%. "
        f"Note: The population data uploaded has a {100*prob_not_represented:2.2f}% "
        "unrepresented population\n"
    )

    print(general_text)

    # Get Age distribution!
    return res, mask, general_text


def run_all(
    OUTPUT_DIR: str,
    MODEL: str,
    model_to_info,
    ERASE_README: bool,
    regions: List[str],
    cohorts: List[str],
    strata_data_opts: List[str],
    data_manipulations: List[Dict[str, str | bool]],
    thresholds_param:List[float]|None = None
):
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, MODEL)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    specific_model_info = model_to_info[MODEL]

    # Erase file
    if ERASE_README:
        with open(os.path.join(OUTPUT_DIR, "README"), "w") as fw:
            fw.write("")
    total_runs = (
        len(regions) * len(cohorts) * len(strata_data_opts) * len(data_manipulations)
    )
    progress_bar = tqdm(total=total_runs, desc="progress")

    for region in regions:
        for cohort in cohorts:
            for starta_opt in strata_data_opts:
                for par_manipulation in data_manipulations:
                    file_strata_name = os.path.basename(starta_opt)
                    strata_data = get_strata_data(starta_opt)
                    res, mask, general_text = get_results_for_settings(
                        specific_model_info,
                        region,
                        cohort,
                        strata_data,
                        par_manipulation,
                        thresholds_param,
                    )
                    # Store results
                    if mask:
                        mask = "_" + mask
                    if file_strata_name.endswith(".csv"):
                        file_strata_name = file_strata_name[:-4]
                    file_strata_name = "." + file_strata_name

                    file_name = f"{MODEL}_{region}_{cohort}{mask}{file_strata_name}.csv"
                    full_path_save = os.path.join(OUTPUT_DIR, file_name)
                    res.to_csv(full_path_save, sep="\t", index=False)
                    # Store general_text
                    with open(os.path.join(OUTPUT_DIR, "README"), "a") as fw:
                        fw.write(
                            f"{MODEL} - {region} - {cohort} - {mask} " + general_text
                        )
                    progress_bar.update()


# Global
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "tests", "data"
)
OUTPUT_DIR = "/nas1/Work/Users/Alon/LGI/outputs/cutoff_simulations"
model_to_info = retrieve_config()
SET_COHORT_SIZE = 1e6
ERASE_README = False

# Specific
if __name__ == '__main__':
    MODEL = "LGIFlag"  # GastroFlag
    thresholds_param = [0.12, 0.13, 0.14]
    # MODEL = "GastroFlag"
    # thresholds_param = []

    regions = ["UK-THIN"]
    cohorts = ["Age Range: 45-75, Time-window: 365", "Age Range: 45-75, Time-window: 180"]
    # cohorts = ["Age Range: 40-90, Time-window: 365", "Age Range: 40-90, Time-window: 180"]

    data_manipulations = [
        {"CBC - Include All History": "CBC - Include All History"},
        {"CBC - Include 3 Years": "CBC - Include 3 Years"},
        {"CBC - Only Most Recent Measurement": "CBC - Only Most Recent Measurement"},
    ]
    strata_data_opts = [
        os.path.join(DATA_DIR, "strats.simple.all.csv"),
        os.path.join(DATA_DIR, "final_data", "stratas.TW_HC_NORM.csv"),
        os.path.join(DATA_DIR, "final_data", "stratas.Medicare_NORM.csv"),
        # os.path.join(DATA_DIR, "final_data", "stratas.Japan_NORM.csv"),
    ]

    # End of params
    run_all(OUTPUT_DIR, MODEL, model_to_info, ERASE_README, regions, cohorts,
            strata_data_opts, data_manipulations, thresholds_param)