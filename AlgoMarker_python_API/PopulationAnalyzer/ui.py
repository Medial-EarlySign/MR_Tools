#!/usr/bin/env python
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from io import StringIO
import json
import os
import re
import sys
import traceback
from typing import Tuple
import pandas as pd
from logger import logger, logging_cache
from logic import StrataStats, full_run, get_bt, get_incidence, get_weights
from nicegui import run, ui, events, app
from models import *
from config import retrieve_config, unfix_name
from file_csv_parser import (
    parse_file_content,
    ErrorFewObs,
    ErrorNotDistribution,
    parse_file_content_non_dist,
)
from logic_med import (
    ReferenceInfo_minimal,
    compare_feature_matrices,
    filter_data_bt,
    generate_clients_matrix,
    get_exact_names,
    get_final_matrix,
    get_final_scores,
    get_samples_from_recent_lab,
    norm_names_lower,
    process_res,
)
import plotly.graph_objects as go


global strata_data
global strata_name
global selected_model
global selected_region
global selected_cohort
global model_to_info
global model_to_data
global last_run_params
global strata_data_inc
global strata_name_inc
global strata_data_raw

model_to_data = {}
selected_model = None
strata_data: List[StrataStats] = None
selected_region = None
selected_cohort = None
last_run_params = None
strata_name: str = None
strata_data_inc: List[StrataStats] = None
strata_name_inc: str = None
strata_data_raw: pd.DataFrame | None = None
strata_name_raw: str = None

model_to_info = retrieve_config()

# sys.stdout = global_logger
# obj_logger = redirect_stdout(global_logger)
# obj_logger_stderr = redirect_stderr(global_logger)
# _ = obj_logger.__enter__()
# obj_logger_stderr.__enter__()
# sys.stderr = global_logger


async def get_age_from_info(strata_data: List[StrataStats]) -> pd.DataFrame:
    all_data = []
    for s in strata_data:
        age_bin_s = list(filter(lambda x: x.feature_name.lower() == "age", s.stratas))
        if len(age_bin_s) == 0:
            continue
        age_bin_s = age_bin_s[0]
        all_data.append(
            {
                "age.min": age_bin_s.min_range,
                "age.max": age_bin_s.max_range,
                "c": s.prob,
            }
        )
        # a
    df = pd.DataFrame(all_data)
    df["age_range"] = df["age.max"] - df["age.min"] + 1
    # Assume no overlap - all same resulotion?
    # Break to 1 resulution:
    all_age_range = pd.DataFrame({"age": range(100)})
    df = (
        df.assign(key=1)
        .merge(all_age_range.assign(key=1), on="key")
        .drop(columns="key")
    )
    df = df[(df["age"] >= df["age.min"]) & (df["age"] <= df["age.max"])].reset_index(
        drop=True
    )
    df["c"] = df["c"] / df["age_range"]
    df = df.groupby("age")["c"].sum().reset_index()
    df["p"] = 100 * (df["c"] / df["c"].sum())
    df = df[["age", "p"]]
    df.columns = ["Age", "weight"]

    return df


async def get_age_from_info_avg(
    age_density: pd.DataFrame, strata_data_inc: List[StrataStats]
) -> pd.DataFrame:
    all_data = []
    for s in strata_data_inc:
        age_bin_s = list(filter(lambda x: x.feature_name.lower() == "age", s.stratas))
        if len(age_bin_s) == 0:
            continue
        age_bin_s = age_bin_s[0]
        all_data.append(
            {
                "age.min": age_bin_s.min_range,
                "age.max": age_bin_s.max_range,
                "c": s.prob,
            }
        )
        # a
    df = pd.DataFrame(all_data)
    df["age_range"] = df["age.max"] - df["age.min"] + 1
    df["c_weight"] = 1 / df["age_range"]
    # Assume no overlap - all same resulotion?
    # Break to 1 resulution:
    all_age_range = pd.DataFrame({"age": range(100)})
    df = (
        df.assign(key=1)
        .merge(all_age_range.assign(key=1), on="key")
        .drop(columns="key")
    )
    df = df[(df["age"] >= df["age.min"]) & (df["age"] <= df["age.max"])].reset_index(
        drop=True
    )
    df["c_val"] = df["c"] * df["c_weight"]
    df_max_w = df.groupby("age")["c_weight"].sum().reset_index()
    df = df.groupby("age")["c_val"].sum().reset_index()
    df = df.merge(df_max_w, on="age")
    df["c_val"] = df["c_val"] / df["c_weight"]
    df = df[["age", "c_val"]]
    df.columns = ["Age", "weight"]

    return df


def get_incidence_for_graphs(
    selected_model_data_filter: pd.DataFrame,
    weights: List[float],
    control_weight: float | None,
    resolution: float | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    data = (
        selected_model_data_filter[["age", "outcome"]]
        .rename(columns={"age": "Age"})
        .copy()
    )
    if resolution:
        data["Age"] = (data["Age"] / resolution).astype(int) * resolution
    data["weight"] = weights
    plt_data_before_cases = (
        data[data["outcome"] > 0].groupby(["Age"])["weight"].count().reset_index()
    ).rename(columns={"weight": "cases"})
    plt_data_before_controls = (
        data[data["outcome"] < 1].groupby(["Age"])["weight"].count().reset_index()
    ).rename(columns={"weight": "controls"})
    plt_data_before = plt_data_before_controls.merge(
        plt_data_before_cases, on="Age", how="outer"
    ).fillna(0)
    if control_weight:
        plt_data_before["controls"] = plt_data_before["controls"] * control_weight
    plt_data_before["weight"] = (
        plt_data_before["cases"]
        / (plt_data_before["cases"] + plt_data_before["controls"])
        * 1e5
    )
    plt_data_after_cases = (
        data[data["outcome"] > 0]
        .groupby(["Age"])["weight"]
        .sum()
        .reset_index()
        .rename(columns={"weight": "cases"})
    )
    plt_data_after_controls = (
        data[data["outcome"] < 1]
        .groupby(["Age"])["weight"]
        .sum()
        .reset_index()
        .rename(columns={"weight": "controls"})
    )
    plt_data_after = plt_data_after_controls.merge(
        plt_data_after_cases, on="Age", how="outer"
    ).fillna(0)
    plt_data_after["weight"] = (
        plt_data_after["cases"]
        / (plt_data_after["cases"] + plt_data_after["controls"])
        * 1e5
    )
    return plt_data_before, plt_data_after


def get_data_for_graphs(
    selected_model_data_filter: pd.DataFrame,
    weights: List[float],
    columns_name: str,
    rename_col: str,
    resolution: float | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    data = (
        selected_model_data_filter[[columns_name, "outcome"]]
        .rename(columns={columns_name: rename_col})
        .copy()
    )
    if resolution:
        data[rename_col] = (data[rename_col] / resolution).astype(int) * resolution

    data["weight"] = weights
    plt_data_before = data.groupby(rename_col)["weight"].count().reset_index()
    tot = plt_data_before["weight"].sum()
    # logger.info(f'data {rename_col} {len(data)} size, tot sum {tot}')
    plt_data_before["weight"] = plt_data_before["weight"] / tot * 100
    plt_data_after = data.groupby(rename_col)["weight"].sum().reset_index()
    tot = plt_data_after["weight"].sum()
    plt_data_after["weight"] = plt_data_after["weight"] / tot * 100
    return plt_data_before, plt_data_after


def main():

    PREFIX_CHECKBOX_EXISTS = "Availability of analytes: "

    def file_upload(e: events.UploadEventArguments):
        MIN_OBS = 200
        global strata_data
        global strata_name
        file_content = e.content.read().decode("utf-8")
        has_error = True
        try:
            res = parse_file_content(file_content, min_obs=MIN_OBS)
            strata_data = res
            upload_status.set_text(f"Loaded completed for {e.name}")
            err_file_upload.set_visibility(False)
            has_error = False
            strata_name = e.name
        except ErrorFewObs as e:
            res = None
            strata_data = None
            error_msg = f"CSV File doesn't Has too few observation {e.tot_count} (<1000) - please upload file based on larger population"
        except ErrorNotDistribution as e:
            res = None
            strata_data = None
            error_msg = f"CSV File doesn't seems to be a distribution. distribution must sum up all probabilities to 1 or 100. Got {e.tot_prob}"
        except:
            res = None
            strata_data = None
            error_msg = "Bad file format error: \n" + traceback.format_exc()
            upload_status.style("white-space: pre-wrap")

        upload_status.classes.clear()
        if has_error:
            upload_status.set_text(error_msg)
            upload_status.tailwind("text-red-600")
        upload_status.set_visibility(True)

    def select_model(mdl: str):
        # logger.info(f'Clicked {mdl}, value:{model_selection_dropdown.value}')
        global selected_model
        selected_model = mdl
        # ui.notify(f'You Selected model: {selected_model}')
        if selected_model not in model_to_info:
            raise Exception(f"Model {selected_model} not found")
        region_paths = model_to_info[selected_model].model_references
        all_regions = list(region_paths.keys())

        region_options.clear()
        # Add region options:
        region_options.set_options(all_regions)
        # If 1 select option
        if len(all_regions) == 1:
            region_options.set_value(all_regions[0])
        else:
            if (
                model_to_info[selected_model].default_region
                and model_to_info[selected_model].default_region
                in model_to_info[selected_model].model_references
            ):
                region_options.set_value(model_to_info[selected_model].default_region)
            else:
                optional_features.set_visibility(False)
                table_options.set_visibility(False)
                cohort_label.set_visibility(False)
                cohort_options.set_visibility(False)
                missing_signals_card.set_visibility(False)

        err_model_selection.set_visibility(False)
        # region_options.on_value_change = lambda e: select_ref_region()
        region_options.set_visibility(True)
        region_label.set_visibility(True)
        select_ref_region()

    def select_ref_region():
        global selected_region
        global selected_model
        selected_region = region_options.value
        if selected_region is None:
            return
        # ui.notify(f'You Selected model {selected_model} and region: {selected_region}')
        sel_model_label.set_text(f"Selected: {selected_model}")
        additional_info = ""
        if model_to_info[selected_model].additional_info:
            additional_info = model_to_info[selected_model].additional_info
        sel_model_info.set_text(additional_info)
        try:
            df = fetch_data(selected_model, selected_region)
            cols = sorted(
                list(
                    set(df.columns)
                    - set(
                        [
                            "id",
                            "time",
                            "outcome",
                            "outcometime",
                            "split",
                            "pred_0",
                            "Time-Window",
                            "outcome_time",
                        ]
                    )
                )
            )
            table_options.columns = [
                {"field": "name", "label": "Feature Name", "sortable": True}
            ]
            table_options.rows = [{"name": x} for x in cols]
            optional_features.set_text(f"You can use the following features:")
            table_options.set_visibility(True)

            all_cohorts = list(
                map(
                    lambda x: x.cohort_name,
                    model_to_info[selected_model]
                    .model_references[selected_region]
                    .cohort_options,
                )
            )
            cohort_label.set_visibility(True)
            cohort_options.clear()
            cohort_options.set_options(all_cohorts)
            # Select default:
            if len(all_cohorts) == 1:
                cohort_options.set_value(all_cohorts[0])
            else:
                if (
                    model_to_info[selected_model]
                    .model_references[selected_region]
                    .default_cohort
                ):
                    cohort_options.set_value(
                        model_to_info[selected_model]
                        .model_references[selected_region]
                        .default_cohort
                    )

            cohort_options.set_visibility(True)
        except:
            logger.error(traceback.format_exc())
            optional_features.set_text(
                f"Error retrieving data: {traceback.format_exc()}"
            )
            table_options.set_visibility(False)
            cohort_label.set_visibility(False)
            missing_signals_card.set_visibility(False)
            cohort_options.clear()
            cohort_options.set_visibility(False)
        optional_features.set_visibility(True)
        logger.info(f"Set {selected_model} and region {selected_region}")
        # Add options:
        missing_signals_card.set_visibility(True)
        missing_signals_card.clear()
        optional_signals = model_to_info[selected_model].signals_info
        with missing_signals_card:
            ui.label("Define Model Input Settings:")
            for ii, opt_sig in enumerate(optional_signals):
                if ii != 0:
                    ui.separator()
                if isinstance(opt_sig, InputSignalsExistence):
                    eee = ui.checkbox(
                        PREFIX_CHECKBOX_EXISTS + opt_sig.signal_name, value=True
                    )
                    if opt_sig.tooltip_str:
                        eee.tooltip(opt_sig.tooltip_str)
                elif isinstance(opt_sig, InputSignalsTime):
                    dict_opt = {}
                    dict_opt[0] = f"{opt_sig.signal_name} - Include All History"
                    for op_i, opt_num in enumerate(opt_sig.max_length_in_years):
                        dict_opt[op_i + 1] = (
                            f"{opt_sig.signal_name} - Include {opt_num} Years"
                        )
                    if opt_sig.include_only_last:
                        dict_opt[len(opt_sig.max_length_in_years) + 1] = (
                            f"{opt_sig.signal_name} - Only Most Recent Measurement"
                        )
                    ui.radio(dict_opt, value=0)
                else:
                    logger.info("Unsupported InputSignal")
                    raise Exception("Unsupported InputSignal")
        # Show cohort options:

    def fetch_data(selected_model, selected_region) -> pd.DataFrame:
        global model_to_data
        if selected_model not in model_to_info:
            raise Exception(f"Model {selected_model} not found")
        if selected_region not in model_to_info[selected_model].model_references:
            raise Exception(
                f"Region {selected_region} for Model {selected_model} not found"
            )
        if selected_model not in model_to_data:
            model_to_data[selected_model] = {}
        if selected_region not in model_to_data[selected_model]:
            logger.info(f"Read {selected_model} for region {selected_region}")
            model_to_data[selected_model][selected_region] = pd.read_csv(
                model_to_info[selected_model]
                .model_references[selected_region]
                .matrix_path
            )
            model_to_data[selected_model][selected_region] = norm_names_lower(
                model_to_data[selected_model][selected_region]
            )
        df = model_to_data[selected_model][selected_region]
        return df

    def fetch_model_info(selected_model) -> ModelInfo:
        if selected_model not in model_to_info:
            raise Exception(f"Model {selected_model} not found")
        return model_to_info[selected_model]

    def fetch_selected_cohort():
        global selected_model
        global selected_region
        selected_cohort = None
        specific_model_info = fetch_model_info(selected_model)
        if selected_region not in specific_model_info.model_references:
            res_label.set_text("Please select valid region!")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            return
        if cohort_options.visible:
            found_cohorts = list(
                filter(
                    lambda x: x.cohort_name == cohort_options.value,
                    specific_model_info.model_references[
                        selected_region
                    ].cohort_options,
                )
            )
            if len(found_cohorts) == 1:
                selected_cohort = cohort_options.value
            else:
                logger.info(f"Matches: {found_cohorts}")
        return selected_cohort, found_cohorts

    def get_missing_signals():
        missing_signals_options = {}
        for item in missing_signals_card.descendants():
            if isinstance(item, ui.label) or isinstance(item, ui.separator):
                continue
            if isinstance(item, ui.checkbox):
                missing_signals_options[item.text[len(PREFIX_CHECKBOX_EXISTS) :]] = (
                    item.value
                )
            elif isinstance(item, ui.radio):
                radio_opts = item.options
                selected_opt_ext = radio_opts[item.value]
                missing_signals_options[selected_opt_ext] = selected_opt_ext
        return missing_signals_options

    async def plot_graph(
        selected_model_data_filter: pd.DataFrame,
        weights: List[float],
        control_weight: float | None = None,
        additional_info_data: dict[str, pd.DataFrame] | None = None,
    ):
        graph_titles = ["Reference Population", "Matching To Your Uploaded Population"]
        plt_data_before, plt_data_after = await run.cpu_bound(
            get_data_for_graphs, selected_model_data_filter, weights, "age", "Age"
        )

        fig_age.data = []
        fig_age.add_trace(
            go.Bar(
                x=plt_data_before["Age"],
                y=plt_data_before["weight"],
                name=graph_titles[0],
            )
        )
        fig_age.add_trace(
            go.Bar(
                x=plt_data_after["Age"],
                y=plt_data_after["weight"],
                name=graph_titles[1],
            )
        )
        if "Age" in additional_info_data:
            data_d = additional_info_data["Age"]
            fig_age.add_trace(
                go.Bar(
                    x=data_d["Age"],
                    y=data_d["weight"],
                    name="Actual Uploaded Age Distribution",
                )
            )
        ui_figure_age.update()

        # Update sex info:
        col_sex_name = "gender"
        if col_sex_name not in selected_model_data_filter.columns:
            col_sex_name = "sex"
        plt_data_before, plt_data_after = await run.cpu_bound(
            get_data_for_graphs,
            selected_model_data_filter,
            weights,
            col_sex_name,
            "Sex",
        )
        sex_ratio.set_text(
            f"Male ratio in the reference population is {plt_data_before[plt_data_before['Sex']==1]['weight'].iloc[0]:0.2f}%, but after matching to your uploaded population, it is {plt_data_after[plt_data_after['Sex']==1]['weight'].iloc[0]:0.2f}%."
        )
        # Update Preds info:
        plt_data_before, plt_data_after = await run.cpu_bound(
            get_data_for_graphs,
            selected_model_data_filter,
            weights,
            "pred_0",
            "Score",
            0.01,
        )
        fig_preds.data = []
        fig_preds.add_trace(
            go.Bar(
                x=plt_data_before["Score"],
                y=plt_data_before["weight"],
                name=graph_titles[0],
            )
        )
        fig_preds.add_trace(
            go.Bar(
                x=plt_data_after["Score"],
                y=plt_data_after["weight"],
                name=graph_titles[1],
            )
        )
        if "Pred" in additional_info_data:
            data_dd = additional_info_data["Pred"]
            fig_preds.add_trace(
                go.Bar(
                    x=data_dd["Score"],
                    y=data_dd["weight"],
                    name="Actual Clients Scores",
                )
            )

        ui_figure_preds.update()
        # Add incidence rate by age graphs - fig_inc_age
        plt_data_before, plt_data_after = await run.cpu_bound(
            get_incidence_for_graphs,
            selected_model_data_filter,
            weights,
            control_weight,
        )
        fig_inc_age.data = []
        fig_inc_age.add_trace(
            go.Scatter(
                x=plt_data_before["Age"],
                y=plt_data_before["weight"],
                name=graph_titles[0],
                mode="markers+lines",
            )
        )
        fig_inc_age.add_trace(
            go.Scatter(
                x=plt_data_after["Age"],
                y=plt_data_after["weight"],
                name=graph_titles[1],
                mode="markers+lines",
            )
        )
        if "Age_inc" in additional_info_data:
            data_dd = additional_info_data["Age_inc"]
            fig_inc_age.add_trace(
                go.Scatter(
                    x=plt_data_after["Age"],
                    y=plt_data_after["weight"],
                    name="Actual Uploaded Age Incidence",
                    mode="markers+lines",
                )
            )

        ui_figure_age_incidence.update()

        for ele in graphic_elements:
            ele.set_visibility(True)
            if type(ele) == ui.plotly:
                ele.classes.clear()
                ele.classes("w-full h-400")

    def clear_result_form():
        res_table.clear()
        res_table.set_visibility(False)
        go_button.enable()
        for ele in graphic_elements:
            ele.set_visibility(False)
        download_button.set_visibility(False)
        res_icon.props("name=warning")
        res_icon.set_visibility(True)

    async def process_exact_data(
        selected_model_data: pd.DataFrame,
        save_selected_model: str,
        save_selected_region: str,
        save_selected_cohort: str,
        found_cohorts,
    ):
        STORE_MATRIX = False
        global strata_data_raw
        global strata_name_raw
        current_file_name = str(strata_name_raw)
        if strata_data_raw is None:
            err_file_upload_data.set_visibility(True)
            upload_status_data.set_visibility(False)
            res_label.set_text("Please fill in all required inputs")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            clear_result_form()
            return
        specific_model_info = fetch_model_info(save_selected_model)
        clients_data = strata_data_raw.copy()
        if specific_model_info.match_important_features is None:
            res_label.set_text(
                "Please ask MES to define match_important_features in this model"
            )
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            clear_result_form()
            return
        cohort_info = found_cohorts[0]
        bt_filter = cohort_info.bt_filter
        selected_model_data_filter = selected_model_data.copy()
        len_before = len(selected_model_data_filter)
        selected_model_data_filter = filter_data_bt(
            selected_model_data_filter, bt_filter
        )
        len_after = len(selected_model_data_filter)
        logger.info(
            f"After filtering cohort left with {len_after}, was {len_before} - removed {len_before - len_after}({100*(len_before - len_after)/len_before:2.2f}%)"
        )

        missing_signals_options = get_missing_signals()
        logger.info(missing_signals_options)
        res_label.set_text(
            f"Calculating for {save_selected_model}, {save_selected_region}, {save_selected_cohort}..."
        )
        sample_per_pid = specific_model_info.sample_per_pid
        control_weight = specific_model_info.model_references[
            save_selected_region
        ].control_weight
        cases_weight = None

        res_label.classes.clear()
        res_label.tailwind("font-bold").text_color("blue-800")
        res_table.set_visibility(False)

        for ele in graphic_elements:
            ele.set_visibility(False)
        ui_notifcation = ui.notification(
            timeout=None, spinner=True, message="Start caluclation"
        )
        top_n_value = top_n_input.value
        if len(top_n_value) == 0 or not (test_input_topn(top_n_value)):
            top_n_value = []
        else:
            top_n_value = top_n_value.split(",")
            # Convert to integer:
            top_n_value = list(map(lambda x: int(x), top_n_value))

        thresholds_values = threshold_input.value
        if len(thresholds_values) == 0 or not (test_input_threshold(thresholds_values)):
            thresholds_values = []
        else:
            thresholds_values = thresholds_values.split(",")
            # Convert to integer:
            thresholds_values = list(map(lambda x: float(x), thresholds_values))
        sensitivity_values  = sensitivity_input.value
        if len(sensitivity_values) == 0 or not (test_input_threshold(sensitivity_values)):
            sensitivity_values = []
        else:
            sensitivity_values = sensitivity_values.split(",")
            # Convert to integer:
            sensitivity_values = list(map(lambda x: float(x), sensitivity_values))

        logger.info(f"top_n_value = {top_n_value}, thresholds = {thresholds_values}")
        incidence_ref = get_incidence(
            selected_model_data_filter,
            sample_per_pid,
            control_weight,
            cases_weight,
            SET_COHORT_SIZE,
        )
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        reference_info = ReferenceInfo_minimal(
            repository_path=specific_model_info.model_references[
                save_selected_region
            ].repository_path,
            model_cv_path=specific_model_info.model_references[
                save_selected_region
            ].model_cv_path,
            model_cv_format=specific_model_info.model_references[
                save_selected_region
            ].model_cv_format,
        )
        # use missing_signals_options to create reference matrix and new scores
        current_ref_matrix, mask, full_model_output = await get_final_matrix(
            selected_model_data_filter,
            cache_dir,
            save_selected_model,
            specific_model_info.model_path,
            save_selected_region,
            save_selected_cohort,
            reference_info,
            missing_signals_options,
            specific_model_info.signals_info,
            ui_notifcation,
        )
        if STORE_MATRIX:
            base_pt = os.path.join(
                cache_dir, "matrices", unfix_name(save_selected_model), save_selected_region
            )
            os.makedirs(base_pt, exist_ok=True)
            full_pt = os.path.join(base_pt, f"{mask}.matrix")
            current_ref_matrix.to_csv(full_pt, index=False)
        # create samples for client - TODO: be more generic
        ui_notifcation.message = "Setting Samples for client"
        samples = get_samples_from_recent_lab(clients_data, "Hemoglobin")
        smp = samples.to_df()
        # create clients matrix
        ui_notifcation.message = "Create matrix for client"
        clients_matrix = await run.cpu_bound(
            generate_clients_matrix,
            full_model_output,
            reference_info.repository_path,
            clients_data,
            smp,
            True,
        )
        # generate weights
        ui_notifcation.message = "Generating weights using propensity model"
        final_names = get_exact_names(
            current_ref_matrix, specific_model_info.match_important_features
        )
        ref_matrix_weighted, not_represented = await run.cpu_bound(
            compare_feature_matrices,
            current_ref_matrix,
            clients_matrix,
            final_names,
        )
        # Call bt
        weights = ref_matrix_weighted["weight"].copy()
        ref_matrix_weighted = ref_matrix_weighted.drop(columns=["weight"])
        # clear nan's:
        prob_not_represented = sum(weights.isna()) + not_represented
        ref_matrix_weighted = ref_matrix_weighted[weights.notna()].reset_index(
            drop=True
        )
        weights = weights[weights.notna()]
        if control_weight:
            change_indicies = selected_model_data_filter["outcome"] <= 0
            logger.info(f"Set control weight to {control_weight}")
            weights[change_indicies] = weights[change_indicies] * control_weight
        ui_notifcation.message = "Running Bootstrap"
        res = await run.cpu_bound(
            get_bt,
            ref_matrix_weighted,
            weights,
            sample_per_pid,
            top_n_value,
            thresholds_values,
            sensitivity_values,
        )
        # generate graphs, update UI:
        additional_info = {}
        additional_info["Age"] = (
            clients_matrix.groupby("Age")["outcome"]
            .count()
            .reset_index()
            .rename(columns={"outcome": "weight"})
        )
        additional_info["Age"]["weight"] = (
            100
            * additional_info["Age"]["weight"]
            / additional_info["Age"]["weight"].sum()
        )
        additional_info["Pred"] = (
            clients_matrix["pred_0"]
            .round(2)
            .value_counts()
            .reset_index()
            .rename(columns={"count": "weight", "pred_0": "Score"})
        )
        additional_info["Pred"]["weight"] = (
            100
            * additional_info["Pred"]["weight"]
            / additional_info["Pred"]["weight"].sum()
        )

        await update_results_table(
            res,
            selected_model_data_filter,
            prob_not_represented,
            save_selected_model,
            save_selected_region,
            save_selected_cohort,
            mask,
            incidence_ref,
            ui_notifcation,
            f"RAW_INPUT_{current_file_name}",
            None,
            weights,
            control_weight,
            additional_info,
        )

    async def show_res():
        global selected_model
        global strata_data
        global selected_region
        global strata_name
        global strata_name_inc
        global strata_data_inc

        has_error = False
        if selected_model is None:
            err_model_selection.set_visibility(True)
            res_label.set_text("Please fill in all required inputs")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            has_error = True
        if selected_model is not None and selected_region is None:
            res_label.set_text("Please select region!")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            has_error = True
        selected_cohort, found_cohorts = fetch_selected_cohort()
        if selected_cohort is None:
            res_label.set_text(f"Please select cohort! {cohort_options.value}")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            has_error = True
        if has_error:
            clear_result_form()
            return

        if ex_tabs.value != "Exact Input Data Sample":
            if strata_data is None:
                err_file_upload.set_visibility(True)
                upload_status.set_visibility(False)
                res_label.set_text("Please fill in all required inputs")
                res_label.classes.clear()
                res_label.tailwind("font-bold").text_color("red-600")
                has_error = True
            if has_error:
                clear_result_form()
                return

        specific_model_info = fetch_model_info(selected_model)
        download_button.set_visibility(False)
        err_file_upload.set_visibility(False)
        err_model_selection.set_visibility(False)
        res_icon.set_visibility(False)
        go_button.disable()
        try:
            selected_model_data = fetch_data(selected_model, selected_region)
        except:
            go_button.enable()
            res_label.set_text(f"Error {traceback.format_exc()}")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            res_icon.props("name=running_with_errors")
            res_icon.set_visibility(True)
            raise

        save_selected_model = str(selected_model)
        save_selected_region = str(selected_region)
        save_selected_cohort = str(selected_cohort)
        # print(f"Model {save_selected_model}")
        if ex_tabs.value == "Exact Input Data Sample":
            await process_exact_data(
                selected_model_data,
                save_selected_model,
                save_selected_region,
                save_selected_cohort,
                found_cohorts,
            )
            return
        strata_data_copy = list(strata_data)
        strata_data_inc_copy = None
        if strata_data_inc:
            strata_data_inc_copy = list(strata_data_inc)
        missing_signals_options = get_missing_signals()
        logger.info(missing_signals_options)

        cohort_info = found_cohorts[0]
        bt_filter = cohort_info.bt_filter
        selected_model_data_filter = selected_model_data.copy()
        len_before = len(selected_model_data_filter)
        # Filter "selected_model_data_filter" by "bt_filter"
        # selected_model_data_filter = await run.cpu_bound(filter_data_bt, selected_model_data_filter,bt_filter)
        selected_model_data_filter = filter_data_bt(
            selected_model_data_filter, bt_filter
        )
        len_after = len(selected_model_data_filter)
        logger.info(
            f"After filtering cohort left with {len_after}, was {len_before} - removed {len_before - len_after}({100*(len_before - len_after)/len_before:2.2f}%)"
        )

        sample_per_pid = specific_model_info.sample_per_pid
        control_weight = specific_model_info.model_references[
            selected_region
        ].control_weight
        cases_weight = None

        res_label.set_text(
            f"Calculating for {selected_model}, {selected_region}, {selected_cohort}..."
        )
        strata_file_name = str(strata_name)
        strata_file_name_inc = None
        if strata_name_inc:
            strata_file_name_inc = str(strata_name_inc)
        logger.info(f"Strata file name is {strata_file_name}")
        res_label.classes.clear()
        res_label.tailwind("font-bold").text_color("blue-800")
        res_table.set_visibility(False)

        for ele in graphic_elements:
            ele.set_visibility(False)
        ui_notifcation = ui.notification(
            timeout=None, spinner=True, message="Start caluclation"
        )
        top_n_value = top_n_input.value
        if len(top_n_value) == 0 or not (test_input_topn(top_n_value)):
            top_n_value = []
        else:
            top_n_value = top_n_value.split(",")
            # Convert to integer:
            top_n_value = list(map(lambda x: int(x), top_n_value))

        thresholds_values = threshold_input.value
        if len(thresholds_values) == 0 or not (test_input_threshold(thresholds_values)):
            thresholds_values = []
        else:
            thresholds_values = thresholds_values.split(",")
            # Convert to integer:
            thresholds_values = list(map(lambda x: float(x), thresholds_values))

        sensitivity_values  = sensitivity_input.value
        if len(sensitivity_values) == 0 or not (test_input_threshold(sensitivity_values)):
            sensitivity_values = []
        else:
            sensitivity_values = sensitivity_values.split(",")
            # Convert to integer:
            sensitivity_values = list(map(lambda x: float(x), sensitivity_values))

        logger.info(f"top_n_value = {top_n_value}, thresholds = {thresholds_values}")
        incidence_ref = get_incidence(
            selected_model_data_filter,
            sample_per_pid,
            control_weight,
            cases_weight,
            SET_COHORT_SIZE,
        )
        # use missing_signals_options

        # Prepare model if not in cache:
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        reference_info = ReferenceInfo_minimal(
            repository_path=specific_model_info.model_references[
                selected_region
            ].repository_path,
            model_cv_path=specific_model_info.model_references[
                selected_region
            ].model_cv_path,
            model_cv_format=specific_model_info.model_references[
                selected_region
            ].model_cv_format,
        )
        selected_model_data_filter, mask = await get_final_scores(
            selected_model_data,
            selected_model_data_filter,
            cache_dir,
            specific_model_info.model_name,
            specific_model_info.model_path,
            selected_region,
            selected_cohort,
            reference_info,
            missing_signals_options,
            specific_model_info.signals_info,
            ui_notifcation,
        )

        # Run simulation
        await run_and_update(
            selected_model_data_filter,
            strata_data_copy,
            strata_data_inc_copy,
            save_selected_model,
            save_selected_region,
            save_selected_cohort,
            mask,
            incidence_ref,
            control_weight,
            cases_weight,
            sample_per_pid,
            top_n_value,
            thresholds_values,
            sensitivity_values,
            ui_notifcation,
            strata_file_name,
            strata_file_name_inc,
        )
        # background_tasks.create(run_and_update(selected_model_data_filter,   strata_data, save_selected_model,
        # save_selected_region, save_selected_cohort,mask, incidence_ref,control_weight, cases_weight, sample_per_pid, top_n_value, thresholds_values, #ui_notifcation))

    async def run_and_update(
        selected_model_data_filter: pd.DataFrame,
        strata_data: List[StrataStats],
        strata_data_inc: List[StrataStats] | None,
        save_selected_model: str,
        save_selected_region: str,
        save_selected_cohort: str,
        mask: str,
        incidence_ref: float,
        control_weight: float,
        cases_weight: float,
        sample_per_pid: int,
        top_n_value: List[int],
        thresholds_values: List[float],
        sensitivity_values: List[float],
        ui_notifcation: ui.notification,
        strata_file_name: str,
        strata_file_name_inc: str | None,
    ):
        try:
            ui_notifcation.message = "Matching Your Population"
            weights, prob_not_represented = await run.cpu_bound(
                get_weights, selected_model_data_filter, strata_data, strata_data_inc
            )
            if control_weight:
                change_indicies = selected_model_data_filter["outcome"] <= 0
                logger.info(f"Set control weight to {control_weight}")
                weights[change_indicies] = weights[change_indicies] * control_weight
            if cases_weight:
                change_indicies = selected_model_data_filter["outcome"] > 0
                logger.info(f"Set case weight to {cases_weight}")
                weights[change_indicies] = weights[change_indicies] * cases_weight
            ui_notifcation.message = "Running Bootstrap"
            res = await run.cpu_bound(
                get_bt,
                selected_model_data_filter,
                weights,
                sample_per_pid,
                top_n_value,
                thresholds_values,
                sensitivity_values,
            )
        except:
            error_msg = traceback.format_exc()
            res_table.clear()
            ui_notifcation.dismiss()
            go_button.enable()
            res_label.set_text(f"Error {error_msg}")
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            res_label.style("white-space: pre-wrap")
            res_icon.props("name=running_with_errors")
            res_icon.set_visibility(True)
            return

        # Trim numbers:
        additional_info = {}
        additional_info["Age"] = await get_age_from_info(strata_data)
        if strata_data_inc:
            additional_info["Age_inc"] = await get_age_from_info_avg(
                additional_info["Age"], strata_data_inc
            )

        await update_results_table(
            res,
            selected_model_data_filter,
            prob_not_represented,
            save_selected_model,
            save_selected_region,
            save_selected_cohort,
            mask,
            incidence_ref,
            ui_notifcation,
            strata_file_name,
            strata_file_name_inc,
            weights,
            control_weight,
            additional_info,
        )

    async def update_results_table(
        res: pd.DataFrame,
        selected_model_data_filter: pd.DataFrame,
        prob_not_represented: float,
        save_selected_model: str,
        save_selected_region: str,
        save_selected_cohort: str,
        mask: str,
        incidence_ref: float,
        ui_notifcation: ui.notification,
        strata_file_name: str,
        strata_file_name_inc: str | None,
        weights: List[float],
        control_weight: float | None,
        additional_info_data: dict[str, pd.DataFrame] | None = None,
    ):
        # Trim numbers:
        global last_run_params
        res, npos, nneg = await run.cpu_bound(process_res, res)

        general_text = (
            f"Showing results for {save_selected_model}, {save_selected_region}, {save_selected_cohort} {mask}:\n"
            + f"Note: cohort has {npos:1.0f} cases and {nneg:1.0f} controls, incidence is {100*npos/(npos+nneg):2.2f}%"
            + f" reference cohort incidence before matching was {100*incidence_ref:2.2f}%\n"
        )
        last_run_params = {
            "model": save_selected_model,
            "region": save_selected_region,
            "cohort": save_selected_cohort,
            "mask": mask,
            "file_strata_name": strata_file_name,
            "file_name_inc": strata_file_name_inc,
        }
        if prob_not_represented < 0.05:
            if prob_not_represented > 0:
                res_label.set_text(
                    general_text
                    + f"Note: The population data uploaded has a {100*prob_not_represented:2.2f}% "
                    + "unrepresented population"
                )
            else:
                res_label.set_text(general_text)
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("blue-800")
            res_label.style("white-space: pre-wrap")
        else:
            res_label.set_text(
                general_text
                + f"Warning: The population data uploaded has a {100*prob_not_represented:2.2f}% "
                + "unrepresented population. Please ensure the reference dataset is representative of the target cohort."
            )
            res_label.classes.clear()
            res_label.tailwind("font-bold").text_color("red-600")
            res_label.style("white-space: pre-wrap")
            res_icon.props("name=priority_high")
            res_icon.set_visibility(True)
        # res_table.rows.clear() #columnDefs
        # res_table.row_key = 'Measure'
        name_mapping = {
            "AUC": "Area Under ROC Curve",
            "OR@FPR": "Odds Ratio taken at top X% False Positive rate",
            "PPV@FPR": "Positive Predicted Value/Precision(Percentage of True case out of flagged) taken at top X% False Positive rate",
            "SCORE@FPR": "The score cutoff need to be used for op X% False Positive rate",
            "SENS@FPR": "Sensitivity/Recall(Percentage of true positive cases discovered out of all potential cases) at top X% False Positive rate",
        }
        all_cols = []
        all_cols.append(
            {
                "headerName": "Measure",
                "field": "Measure",
                "sortable": True,
                "filter": "agTextColumnFilter",
                "floatingFilter": True,
                "headerTooltip": "Stand over metric to see more info",
                ":tooltipValueGetter": f'(params) => ({json.dumps(name_mapping)})[params.value.split("_")[0]]',
            }
        )
        all_cols.extend(
            list(
                map(
                    lambda x: {"headerName": x, "field": x, "sortable": False},
                    filter(lambda x: x != "Measure", res.columns),
                )
            )
        )
        # res_table.columns = all_cols
        res_table.clear()
        # res_table.from_pandas(res, options = {'columnDefs': all_cols})
        res_table.options["columnDefs"] = all_cols
        res_table.options["rowData"] = res.to_dict("records")
        res_table.update()

        # res_table.rows = res.to_dict('records')

        res_table.set_visibility(True)
        download_button.set_visibility(True)
        # Plot graph:
        if PLOT_GRAPHS:
            ui_notifcation.message = "Plot graphs..."
            await plot_graph(
                selected_model_data_filter,
                weights,
                control_weight,
                additional_info_data,
            )

        ui_notifcation.dismiss()
        go_button.enable()
        ui.notify("Done running")
        logger.info("Done")

    def clear_data_csv():
        global strata_data
        logger.info("Clear strata_data")
        strata_data = None
        file_upload_ui.reset()
        upload_status.set_visibility(False)

    def clear_data_inc_csv():
        global strata_data_inc
        logger.info("Clear strata_data_inc")
        strata_data_inc = None
        file_upload_inc_ui.reset()
        upload_status_inc.set_visibility(False)

    def clear_data_spec_csv():
        global strata_data_raw
        logger.info("Clear strata_data_raw")
        strata_data_raw = None
        file_upload_input_data.reset()
        upload_status_data.set_visibility(False)

    def clear_all_pop_char():
        if ex_tabs.value == "Exact Input Data Sample":
            clear_data_csv()
            clear_data_inc_csv()
        else:
            clear_data_spec_csv()

    def file_upload_inc(e: events.UploadEventArguments):
        global strata_data_inc
        global strata_name_inc
        file_content = e.content.read().decode("utf-8")
        has_error = True
        try:
            res = parse_file_content_non_dist(file_content)
            # Test all values are between 0 to 10e5:
            if len(list(filter(lambda x: x.prob < 0 or x.prob > 1e5, res))) > 0:
                raise ErrorNotDistribution(
                    f"Error - input stratas is not incidence rate", 0
                )
            for s in res:
                s.prob = s.prob / 1e5
            strata_data_inc = res
            upload_status_inc.set_text(f"Loaded completed for {e.name}")
            has_error = False
            strata_name_inc = e.name
        except ErrorFewObs as e:
            res = None
            strata_data_inc = None
            error_msg = f"CSV File doesn't Has too few observation {e.tot_count} (<1000) - please upload file based on larger population"
        except ErrorNotDistribution as e:
            res = None
            strata_data_inc = None
            error_msg = f"CSV File doesn't seems to be a incidence rate per 100K. Values should be between 0 to 100000"
        except:
            res = None
            strata_data_inc = None
            error_msg = "Bad file format error: \n" + traceback.format_exc()
            upload_status.style("white-space: pre-wrap")

        upload_status_inc.classes.clear()
        if has_error:
            upload_status_inc.set_text(error_msg)
            upload_status_inc.tailwind("text-red-600")
        upload_status_inc.set_visibility(True)

    def file_upload_data_spec(e: events.UploadEventArguments):
        global strata_data_raw
        global strata_name_raw
        file_content = e.content.read().decode("utf-8")
        has_error = True
        try:
            clients_input = pd.read_csv(
                StringIO(file_content), sep="\t", dtype={"value": "str"}
            )
            err_file_upload_data.set_visibility(False)
            strata_data_raw = clients_input
            upload_status_data.set_text(f"Loaded completed for {e.name}")
            has_error = False
            strata_name_raw = e.name
        except:
            strata_data_raw = None
            error_msg = f"Bad File format: {traceback.format_exc()}"

        upload_status_data.classes.clear()
        if has_error:
            upload_status_data.set_text(error_msg)
            upload_status_data.tailwind("text-red-600")
        upload_status_data.set_visibility(True)

    def setup_file_ui():
        return ui.upload(
            on_upload=file_upload,
            max_files=1,
            auto_upload=True,
            label="Population characteristics  (CSV)",
        ).on("removed", clear_data_csv)

    def test_input_topn(s: str) -> bool:
        if len(s) == 0:
            return True
        tokens = s.split(",")
        integer_re = re.compile("[0-9]+")
        has_invalid = (
            len(list(filter(lambda x: integer_re.fullmatch(x) is None, tokens))) > 0
        )
        return not (has_invalid)

    def test_input_threshold(s: str) -> bool:
        if len(s) == 0:
            return True
        tokens = s.split(",")
        integer_re = re.compile(r"[0-9]+(\.[0-9]+)?")
        has_invalid = (
            len(list(filter(lambda x: integer_re.fullmatch(x) is None, tokens))) > 0
        )
        return not (has_invalid)

    def download_excel():
        global selected_model
        global selected_region
        global last_run_params
        file_strata_name = ""
        if last_run_params is None:
            selected_cohort, _ = fetch_selected_cohort()
            missing_signals_options = get_missing_signals()

            mask = ""
            for k, v in sorted(missing_signals_options.items()):
                if type(v) == bool:  # This is checkbox
                    if v:
                        continue
                    if len(mask) > 0:
                        mask += "_"
                    mask += k + "_" + str(int(v))
                else:
                    if k.endswith("Include All History"):
                        continue  # No change
                    elif k.endswith("Only Most Recent Measurement"):
                        signal_name = k.split("-")[0].strip()
                        if len(mask) > 0:
                            mask += "_"
                        mask += signal_name + "_MostRecent"
                    else:
                        signal_name = k.split("-")[0].strip()
                        num_years = int(k.split("-")[1].strip().split()[1])
                        if len(mask) > 0:
                            mask += "_"
                        mask += signal_name + "_LimitYears" + str(num_years)
            selected_mod = selected_model
            selected_reg = selected_region
        else:
            selected_cohort = last_run_params["cohort"]
            mask = last_run_params["mask"]
            selected_reg = last_run_params["region"]
            selected_mod = last_run_params["model"]
            file_strata_name = last_run_params["file_strata_name"]
        logger.info("Excel downloaded")
        df_dict = res_table.options["rowData"]
        df = pd.DataFrame(df_dict)
        if mask:
            mask = "_" + mask
        if file_strata_name:
            file_strata_name = "." + file_strata_name
        file_name = f"results_{selected_mod}_{selected_reg}_{selected_cohort}{mask}{file_strata_name}.csv"
        ui.download(
            bytes(df.to_csv(lineterminator="\n", index=False), encoding="utf-8"),
            filename=file_name,
        )

    PLOT_GRAPHS = True
    PAGE_WIDTH = 900
    CENTER_ELEMENTS = False

    ui.add_head_html(
        """
    <style type="text/tailwindcss">
        h2 {
            font-size: 150%;
        }
    </style>
    """
    )

    ui.page_title(
        "Medial EarlySign - Model Performance Evaluation for Client Configurations"
    )
    with ui.footer():
        go_button = ui.button(
            "Run Evaluation", on_click=show_res, icon="rocket_launch", color="secondary"
        ).tooltip("Run simulation")
        ui.space()
        ui.label("- FOR INTERNAL USAGE ONLY -")
        ui.space()
        with ui.button(
            "Restart app",
            on_click=lambda: os.utime(__file__),
            color="negative",
            icon="restart_alt",
        ):
            ui.tooltip("Restart app").classes("bg-red")
    with ui.row().classes("w-full"):
        if CENTER_ELEMENTS:
            ui.space()
        ui.image("resources/icons/logo-mes.svg").classes("w-16")
        ui.html("<h2>Model Performance Evaluation for Client Configurations</h2>")
        if CENTER_ELEMENTS:
            ui.space()

    with ui.row().classes("w-full"):
        # 1. Model & Setup Selection
        if CENTER_ELEMENTS:
            ui.space()
        with ui.card().style(f"width: {PAGE_WIDTH}px; background-color:lightblue"):
            with ui.card_section().style("height:30px"):
                ui.label("Model & Setup Selection").classes("text-h6")
            with ui.card_section():
                with ui.row().style("align-items: center"):
                    with ui.dropdown_button(
                        "Model Selection", auto_close=True, icon="biotech"
                    ):
                        model_name_keys = list(
                            map(
                                lambda x: x[0],
                                sorted(
                                    model_to_info.items(), key=lambda x: x[1].orderinal
                                ),
                            )
                        )
                        for model_name in model_name_keys:
                            ui.item(
                                model_name,
                                on_click=lambda model_name=model_name: select_model(
                                    model_name
                                ),
                            )
                    sel_model_label = ui.label("")
                    sel_model_info = ui.label("")
                err_model_selection = ui.label("Model selection is mandatory").classes(
                    "text-negative text-xs font-bold"
                )
                err_model_selection.set_visibility(False)

                with ui.row().style("align-items: center"):
                    region_label = ui.label("Reference Population: ")
                    region_options = ui.select(
                        [], on_change=lambda e: select_ref_region()
                    ).props("rounded standout")

                    region_label.set_visibility(False)
                    region_options.set_visibility(False)
                    cohort_label = ui.label("Cohort: ")
                    cohort_options = ui.select([]).props("rounded standout")

                    cohort_label.set_visibility(False)
                    cohort_options.set_visibility(False)

                    # Add option groups to select missing input signals:
                missing_signals_card = ui.card()
                missing_signals_card.set_visibility(False)
        if CENTER_ELEMENTS:
            ui.space()
    with ui.row().classes("w-full"):
        if CENTER_ELEMENTS:
            ui.space()
        with ui.card().style(f"width: {PAGE_WIDTH}px; background-color:lightblue"):
            # 2. Current Population Settings
            with ui.card_section().style("height:30px"):
                ui.label("Current Population Settings").classes("text-h6")
            with ui.card_section():
                with ui.tabs() as ex_tabs:
                    ex_one_format_option = ui.tab("Population Characteristics")
                    ex_two_format_option = ui.tab("Exact Input Data Sample")
                with ui.tab_panels(ex_tabs, value=ex_one_format_option).classes(
                    "w-full"
                ):
                    with ui.tab_panel(ex_one_format_option):
                        with ui.expansion(
                            "Help Instruction to upload a file with desired population properties",
                            caption="Click to show help",
                            icon="help",
                        ):
                            optional_features = ui.label("")
                            table_options = ui.table(
                                rows=[],
                                columns=[{"label": "Feature Name"}],
                                pagination=3,
                                column_defaults={
                                    "align": "left",
                                    "headerClasses": "uppercase text-primary",
                                },
                            )
                            table_options.set_visibility(False)
                            # Upload file or statistical data file to match to:
                            with ui.tabs() as tabs:
                                one_format_option = ui.tab("Simple Format")
                                two_format_option = ui.tab("Optional Format")

                            with ui.tab_panels(tabs, value=one_format_option).classes(
                                "w-full"
                            ):
                                with ui.tab_panel(one_format_option):
                                    ui.markdown(
                                        """
## Instructions
Upload a **comma-separated CSV file** where each row represents a population segment and its proportion relative to the total population.
* Proportions can be **ratios, percentages, or total counts**:
	- **Ratios** must sum to **1**.
	- **Percentages** must sum to **100**.
	- **Total counts** must be **integers**.
* The **header** should include feature names (from the optional feature list).
* **Numeric features** (e.g., age) require two columns:
	- ```<Feature>.Min``` → Minimum value
	- ```<Feature>.Max``` → Maximum value
* **Categorical features** (e.g., sex) use a single column with the feature name (e.g., Sex).
	- If a category is left empty, that criterion is ignored.
* The **last column** represents the population probability (ratio, percentage, or count).

**Example (header is case-insensitive):**
 | Age.Min | Age.Max | Sex | Probability |
| ------- | ------- | --- | ----------- |
|   50    |   54    | Male| 0.03 |
|   55    |   59    | Male| 0.028 |
|   50    |   54    | Female| 0.04 |
|   55    |   59    | Female| 0.038 |
The first row represents **males aged 50–54**, making up **3%** of the population.

The Second row represents **males aged 55–59**, making up **2.8%** of the population.

The other lines represents females in those age ranges and the corresponding proportions.

Full download [example](/download/strats.taiwan.csv)

To upload incidence rate per group the file format is identical, last columns will represent incidence rate at 100K patients.
                                                """,
                                        extras=["breaks", "cuddled-lists", "tables"],
                                    )
                                with ui.tab_panel(two_format_option):
                                    ui.markdown(
                                        """
## Instructions
Upload a **comma-separated CSV file** where each row represents a population segment and its proportion relative to the total population.
* Proportions can be **ratios, percentages, or total counts**:
	- **Ratios** must sum to **1**.
	- **Percentages** must sum to **100**.
	- **Total counts** must be **integers**.
* Each row must contain at least **one feature token**, with the **last column** being a numeric value indicating the segment’s proportion.
* A **feature token** consists of **three columns**:
	- **First column** → Feature name (from the provided list).
	- **Second & third columns** → Numeric range (**minimum** to **maximum**) defining the population filter.

**Example (no headers):**
|  |  |  |  |
| --- | -- | -- | ---- |
| Age | 50 | 54 | 0.03 |
| Age | 55 | 59 | 0.028 |
The first row represents **aged 50–54**, with a **3% proportion**.
The second row represents **aged 55–59**, with a **2.8% proportion**.
To upload incidence rate per group the file format is identical, last columns will represent incidence rate at 100K patients.
                                                """,
                                        extras=["breaks", "cuddled-lists", "tables"],
                                    )
                        with ui.row():
                            with ui.column():
                                file_upload_ui = setup_file_ui()
                                err_file_upload = ui.label(
                                    "Population CSV file upload is mandatory"
                                ).classes("text-negative text-xs font-bold")
                                err_file_upload.set_visibility(False)

                                upload_status = ui.label("Upload Status:")
                                upload_status.set_visibility(False)
                            with ui.column():
                                file_upload_inc_ui = ui.upload(
                                    on_upload=file_upload_inc,
                                    max_files=1,
                                    auto_upload=True,
                                    label="Population CSV Incidence rate per group",
                                ).on("removed", clear_data_inc_csv)
                                upload_status_inc = ui.label("Upload Status:")
                                upload_status_inc.set_visibility(False)
                    with ui.tab_panel(ex_two_format_option):
                        with ui.expansion(
                            "Help Instruction to upload Input file with sample data for AlgoMarker",
                            caption="Click to show help",
                            icon="help",
                        ):
                            ui.markdown(
                                """
## Instructions
Upload a **tab-separated CSV file** following the **file-api format**.
The file must have the following headers:
```pid```, ```code```, ```timestamp```, ```value```, ```unit```
* ```pid``` → Patient identifier.
* ```code``` → Signal name (must be in a format accepted by AlgoMarker).
* ```timestamp``` → When the signal is applicable (can be empty).
* ```value``` → The signal value (can be empty).
* ```unit``` → Unit of measurement (must match AlgoMarker’s expected unit; **no unit conversion or validation** will be performed).

**Example rows**:
| pid  | code |	timestamp | value |	unit |
|------|--------|---------------|-------|--------|
| 1    |  BDATE |         | 19880101 |   |
| 1   | Hemoglobin | 20230327 | 14.3 | g/dL |
                                                """,
                                extras=["breaks", "cuddled-lists", "tables"],
                            )
                        with ui.column():
                            file_upload_input_data = ui.upload(
                                on_upload=file_upload_data_spec,
                                max_files=1,
                                auto_upload=True,
                                label="Raw Input data sample",
                            ).on("removed", clear_data_spec_csv)
                            err_file_upload_data = ui.label(
                                "file upload is mandatory"
                            ).classes("text-negative text-xs font-bold")
                            err_file_upload_data.set_visibility(False)
                            upload_status_data = ui.label("Upload Status")

        if CENTER_ELEMENTS:
            ui.space()
    with ui.row().classes("w-full"):
        if CENTER_ELEMENTS:
            ui.space()
        with ui.card().style(f"width: {PAGE_WIDTH}px; background-color:lightblue"):
            # 3. Optional Analysis Settings
            with ui.card_section().style("height:30px"):
                ui.label("Optional Analysis Settings").classes("text-h6")
            with ui.card_section():
                # Optional TopN:
                with ui.row():
                    top_n_input = ui.input(
                        label="Optional Top N",
                        placeholder="comma separated integers for top N",
                        validation={"Input invalid format": test_input_topn},
                    )
                    with top_n_input:
                        ui.tooltip("Optional Top N patients to flag out of 1M patients")
                    threshold_input = ui.input(
                        label="Optional Thresholds",
                        placeholder="comma separated floats of thresholds",
                        validation={"Input invalid format": test_input_threshold},
                    )
                    with threshold_input:
                        ui.tooltip("Optional threshold numeric cutoff")
                    sensitivity_input = ui.input(
                        label="Optional Sensitivity",
                        placeholder="comma separated floats of senstivity thresholds",
                        validation={"Input invalid format": test_input_threshold},
                    )
                    with sensitivity_input:
                        ui.tooltip("Optional sensitivity numeric values")
        if CENTER_ELEMENTS:
            ui.space()
    with ui.row().classes("w-full"):
        if CENTER_ELEMENTS:
            ui.space()
        with ui.column():
            # 4. Results
            with ui.row():
                res_icon = ui.icon("warning", size="md")
                res_label = ui.label("Results:")
            res_icon.set_visibility(False)

            # def_cols = ['Measure', 'Mean', 'CI.Lower.95', 'CI.Upper.95', 'Std']
            res_table = ui.aggrid(
                {"autoSizeStrategy": {"type": "fitGridWidth"}},
                auto_size_columns=True,
            ).style(
                f"width:{PAGE_WIDTH}px; height:400px;"
            )  # text-align: center;
            res_table.set_visibility(False)

            download_button = ui.button(
                "Download results", on_click=download_excel, icon="download"
            )
            download_button.set_visibility(False)
            fig_age = go.Figure(
                layout=go.Layout(
                    title="Age distribution",
                    xaxis={"title": "Age"},
                    yaxis={"title": "Percentage(%)"},
                )
            )
            fig_preds = go.Figure(
                layout=go.Layout(
                    title="Score distribution",
                    xaxis={"title": "Score"},
                    yaxis={"title": "Percentage(%)"},
                )
            )
            fig_inc_age = go.Figure(
                layout=go.Layout(
                    title="Age Incidence Rate",
                    xaxis={"title": "Age"},
                    yaxis={"title": "Rate Per 100K"},
                )
            )

            sex_ratio = ui.label("Sex ratio:")
            ui_figure_age = (
                ui.plotly(fig_age).classes("h-400").style(f"width:{PAGE_WIDTH}px")
            )
            ui_figure_preds = (
                ui.plotly(fig_preds).classes("h-400").style(f"width:{PAGE_WIDTH}px")
            )
            ui_figure_age_incidence = (
                ui.plotly(fig_inc_age).classes("h-400").style(f"width:{PAGE_WIDTH}px")
            )
        if CENTER_ELEMENTS:
            ui.space()

    graphic_elements: List[ui.plotly | ui.label] = [
        ui_figure_age,
        sex_ratio,
        ui_figure_preds,
        ui_figure_age_incidence,
    ]
    for ele in graphic_elements:
        ele.set_visibility(False)

    ex_tabs.on_value_change(lambda x: clear_all_pop_char())
    SET_COHORT_SIZE = 1000000


@ui.page("/console", title="Logging")
def logging_verbose():
    def clear_all():
        logging_cache.clear_log()
        log_e.clear()

    def update_log():
        msgs = logging_cache.get_messages()
        # global_logger.clear_log() # Might miss some logs in between. not that important
        log_e.clear()
        log_e.push("\n".join(msgs))
        update_time.set_text(
            f'Last update {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )

    log_e = (
        ui.log(max_lines=logging_cache.max_messages)
        .classes("w-full")
        .style("height:800px")
    )
    update_time = ui.label("")
    ui.timer(5.0, update_log)
    ui.button("Clear log", on_click=clear_all)


def shutdown_event():
    pass


if __name__ in {"__main__", "__mp_main__"}:
    main()
    app.on_shutdown(shutdown_event)
    app.add_static_files("/download", "tests/data")
    ui.run(port=3764, favicon="resources/icons/faveicon.svg", reload=True, show=False)
