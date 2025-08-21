import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel
from xgboost import XGBClassifier
from config import unfix_name
from logic import fit_model_to_rep
import med
from models import InputSignals
from nicegui import ui, run
from logger import logger


class ReferenceInfo_minimal(BaseModel):
    repository_path: str | None
    model_cv_path: str | None
    model_cv_format: str | None


def __get_model_pids(CV_MODELS: str, CV_MODELS_FORMAT: str, model_num: int) -> Set[str]:
    train_samples = os.path.join(
        CV_MODELS, CV_MODELS_FORMAT % (model_num) + ".train_samples"
    )
    df = pd.read_csv(train_samples, sep="\t", usecols=["id"])
    df = df.drop_duplicates().reset_index(drop=True)
    ids_in_training = set(df["id"])
    return ids_in_training


def _get_preds_with_splits(
    CV_MODELS: str, CV_MODELS_FORMAT: str, df: pd.DataFrame
) -> pd.DataFrame:
    # Set split column:
    prefix = CV_MODELS_FORMAT[: CV_MODELS_FORMAT.find("%d")]
    suffix = CV_MODELS_FORMAT[CV_MODELS_FORMAT.find("%d") + 2 :]
    all_files = list(
        filter(
            lambda x: x.startswith(prefix) and x.endswith(suffix), os.listdir(CV_MODELS)
        )
    )
    all_ids = list(map(lambda x: int(x[len(prefix) : -len(suffix)]), all_files))
    cv_size = len(all_ids)
    assert min(all_ids) == 0
    assert max(all_ids) == cv_size - 1
    # logger.info(df)
    df["split"] = -1
    for i in range(cv_size):
        pids = __get_model_pids(CV_MODELS, CV_MODELS_FORMAT, i)
        df.loc[~df["id"].isin(pids), "split"] = i
    assert df["split"].min() >= 0
    return df


def _apply_cv_from_df(
    df: pd.DataFrame,
    CV_MODELS: str,
    CV_MODELS_FORMAT: str,
    REPO_PATH: str,
    pre_json: str,
) -> pd.DataFrame:
    min_split = df["split"].min()
    max_split = df["split"].max()
    all_res = []
    for split in range(min_split, max_split):
        dff = df[df["split"] == split].reset_index(drop=True).copy()
        model_path = os.path.join(CV_MODELS, CV_MODELS_FORMAT % (split))
        # dff_scores = calc_scores(model_path, REPO_PATH, dff)
        dff_scores = recalc_scores(model_path, REPO_PATH, dff, pre_json, None)
        dff = dff.drop(columns=["pred_0"]).merge(
            dff_scores[["id", "time", "pred_0"]], on=["id", "time"]
        )
        all_res.append(dff)
    df = pd.concat(all_res, ignore_index=True)
    return df


def _apply_post(model_path: str, samples_df: pd.DataFrame) -> pd.DataFrame:
    model = med.Model()
    model.read_from_file(model_path)
    samples = med.Samples()
    # populate from samples_df
    samples.from_df(
        samples_df.rename(columns={"outcometime": "outcomeTime"})[
            ["id", "time", "outcome", "outcomeTime", "split", "pred_0"]
        ]
    )

    rep = med.PidRepository()
    model.features.append_samples(samples)
    model.apply(rep, samples, 9, 99)
    return samples.to_df()


def apply_cv(
    CV_MODELS: str,
    CV_MODELS_FORMAT: str,
    REPO_PATH: str,
    pre_json: str,
    samples_df: pd.DataFrame,
    calibrator_model: str | None,
    output_path: str,
) -> pd.DataFrame:
    df = _get_preds_with_splits(CV_MODELS, CV_MODELS_FORMAT, samples_df)
    df = _apply_cv_from_df(df, CV_MODELS, CV_MODELS_FORMAT, REPO_PATH, pre_json)
    # TODO: apply calibrator:
    if calibrator_model:
        df = _apply_post(calibrator_model, df)
    df.to_csv(output_path, sep="\t", index=False)
    return df


def get_missing_panels_info(
    missing_signals_options: Dict[str, str | bool], signals_info: List[InputSignals]
) -> tuple[List[str], str, bool]:
    mask = ""
    need_recalc = False
    rep_processors_js = []
    for k, v in sorted(missing_signals_options.items()):
        if type(v) == bool:  # This is checkbox
            if v:
                continue
            need_recalc = True
            logger.info(f"Will Turn off {k}")
            if len(mask) > 0:
                mask += "_"
            mask += k + "_" + str(int(v))
            rel_info = list(filter(lambda x: x.signal_name == k, signals_info))
            if len(rel_info) != 1:
                raise Exception(f"Error - found {len(rel_info)} for {k}")
            rel_info = rel_info[0]
            full_sigs = ",".join(
                map(lambda x: '"' + x + '"', rel_info.list_raw_signals)
            )
            rep_proccesor_json = (
                """
                            {
                                "rp_type":"history_limit",
                                "take_last_events":"0",
                                "delete_sig":"1",
                                "signal":[ """
                + full_sigs
                + """ ]
                            }
                """
            )
            rep_processors_js.append(rep_proccesor_json)

        else:  # radio, k == v
            if k.endswith("Include All History"):
                continue  # No change
            elif k.endswith("Only Most Recent Measurement"):
                need_recalc = True
                signal_name = k.split("-")[0].strip()
                # Find this in models:
                rel_info = list(
                    filter(lambda x: x.signal_name == signal_name, signals_info)
                )
                if len(rel_info) != 1:
                    raise Exception(f"Error - found {len(rel_info)} for {signal_name}")
                rel_info = rel_info[0]
                full_sigs = ",".join(
                    map(lambda x: '"' + x + '"', rel_info.list_raw_signals)
                )
                logger.info(f"{signal_name} will be taken as only most recent")
                rep_proccesor_json = (
                    """
                            {
                                "rp_type":"history_limit",
                                "take_last_events":"1",
                                "delete_sig":"0",
                                "signal":[ """
                    + full_sigs
                    + """ ]
                            }
                """
                )
                rep_processors_js.append(rep_proccesor_json)
                if len(mask) > 0:
                    mask += "_"
                mask += signal_name + "_MostRecent"
            else:
                need_recalc = True
                signal_name = k.split("-")[0].strip()
                num_years = int(k.split("-")[1].strip().split()[1])
                if len(mask) > 0:
                    mask += "_"
                mask += signal_name + "_LimitYears" + str(num_years)
                rel_info = list(
                    filter(lambda x: x.signal_name == signal_name, signals_info)
                )
                if len(rel_info) != 1:
                    raise Exception(f"Error - found {len(rel_info)} for {signal_name}")
                rel_info = rel_info[0]
                full_sigs = ",".join(
                    map(lambda x: '"' + x + '"', rel_info.list_raw_signals)
                )
                logger.info(f"{signal_name} will be taken for {num_years} years")
                num_days = num_years * 365
                rep_proccesor_json = (
                    '''
                            {
                                "rp_type":"history_limit",
                                "take_last_events":"0",
                                "delete_sig":"0",
                                "win_from": "0",
                                "win_to": "'''
                    + str(num_days)
                    + """",
                                "signal":[ """
                    + full_sigs
                    + """ ]
                            }
                """
                )
                rep_processors_js.append(rep_proccesor_json)
                # Include {opt_num} Years
    return rep_processors_js, mask, need_recalc


def calc_scores(model_path: str, repo_path: str, samples_df: pd.DataFrame):
    model = med.Model()
    model.read_from_file(model_path)

    rep = med.PidRepository()
    rep.init(repo_path)

    model.fit_for_repository(rep)
    signalNamesSet = model.get_required_signal_names()

    ids = samples_df["id"].unique().astype("int32")
    rep.read_all(repo_path, ids, signalNamesSet)

    samples = med.Samples()
    # populate from samples_df
    samples.from_df(
        samples_df.rename(columns={"outcometime": "outcomeTime"})[
            ["id", "time", "outcome", "outcomeTime", "split"]
        ]
    )

    # Apply model:
    model.apply(rep, samples)
    return samples.to_df()


def recalc_scores(
    model_path: str,
    repo_path: str,
    samples_df: pd.DataFrame,
    pre_rep_json: str,
    output_path: str | None,
    return_matrix: bool = False,
) -> pd.DataFrame:
    model = med.Model()
    model.read_from_file(model_path)

    logger.info(pre_rep_json)
    model.add_pre_processors_json_string_to_model(pre_rep_json, "")

    rep = med.PidRepository()
    rep.init(repo_path)

    model.fit_for_repository(rep)
    signalNamesSet = model.get_required_signal_names()

    ids = samples_df["id"].unique().astype("int32")
    rep.read_all(repo_path, ids, signalNamesSet)

    samples = med.Samples()
    # populate from samples_df
    samples.from_df(
        samples_df.rename(columns={"outcometime": "outcomeTime"})[
            ["id", "time", "outcome", "outcomeTime", "split"]
        ]
    )

    # Apply model:
    model.apply(rep, samples)
    # Save
    if output_path:
        samples.write_to_file(output_path)
    if return_matrix:
        return model.features.to_df()
    return samples.to_df()


def get_merged_res(final_pred_path: str, selected_model_data_filter: pd.DataFrame):
    new_preds_res = pd.read_csv(final_pred_path, sep="\t")
    new_preds_res = new_preds_res[["id", "time", "pred_0"]].set_index(["id", "time"])
    selected_model_data_filter.drop(columns=["pred_0"], inplace=True)
    selected_model_data_filter = (
        selected_model_data_filter.set_index(["id", "time"])
        .join(new_preds_res, how="inner")
        .reset_index()
    )
    return selected_model_data_filter


async def ensure_adjust_model(
    cache_dir: str,
    reference_info: ReferenceInfo_minimal,
    model_name: str,
    model_path: str,
    ui_notifcation: ui.notification = None,
) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    if reference_info.repository_path:
        rep_name = ".".join(
            os.path.basename(reference_info.repository_path).split(".")[:-1]
        )
        full_model_output = os.path.join(cache_dir, f"{model_name}.{rep_name}.medmdl")
        if not (os.path.exists(full_model_output)):
            if ui_notifcation:
                ui_notifcation.message = "Adjusting model to rep"
                await run.cpu_bound(
                    fit_model_to_rep,
                    model_path,
                    reference_info.repository_path,
                    full_model_output,
                )

            else:
                logger.info("Adjusting model to rep")
                fit_model_to_rep(
                    model_path,
                    reference_info.repository_path,
                    full_model_output,
                )
    return full_model_output


async def get_final_scores(
    selected_model_data: pd.DataFrame,
    selected_model_data_filter: pd.DataFrame,
    cache_dir: str,
    model_name: str,
    model_path: str,
    region: str,
    cohort: str,
    reference_info: ReferenceInfo_minimal,
    missing_signals_options: Dict[str, str | bool],
    signals_info: List[InputSignals],
    ui_notifcation: ui.notification = None,
) -> tuple[pd.DataFrame, str]:
    # Prepare model if not in cache:
    model_name_f = unfix_name(model_name)
    full_model_output = await ensure_adjust_model(
        cache_dir, reference_info, model_name_f, model_path, ui_notifcation
    )
    # Get right scores:
    new_pred_dir = os.path.join(cache_dir, "preds")
    os.makedirs(new_pred_dir, exist_ok=True)
    _am_preds_dir = os.path.join(new_pred_dir, model_name_f)
    os.makedirs(_am_preds_dir, exist_ok=True)
    am_preds_dir = os.path.join(_am_preds_dir, region)
    os.makedirs(am_preds_dir, exist_ok=True)
    # Get mask of each option:

    rep_processors_js, mask, need_recalc = get_missing_panels_info(
        missing_signals_options, signals_info
    )

    if need_recalc:
        logger.info(f"Calculating for {model_name}, {region}, {cohort}, {mask}...")
        rep_processors_json_final = (
            """
{
    "pre_processors": [{
        "action_type":"rp_set",
        "members":[
"""
            + "\n,".join(rep_processors_js)
            + """
           ]
    }]
}
"""
        )
        final_pred_path = os.path.join(am_preds_dir, mask)
        if not (os.path.exists(final_pred_path)):
            logger.info(f"Will generate {final_pred_path}")
            if not (reference_info.repository_path):
                raise Exception(
                    f'Error please define "repository_path" for {model_name} in {region}'
                )
            # run on full data "selected_model_data"

            if ui_notifcation:
                ui_notifcation.message = "Calculating new scores for this scenario"
            else:
                logger.info("Calculating new scores for this scenario")
            if reference_info.model_cv_path:
                if ui_notifcation is None:
                    apply_cv(
                        reference_info.model_cv_path,
                        reference_info.model_cv_format,
                        reference_info.repository_path,
                        rep_processors_json_final,
                        selected_model_data,
                        full_model_output,
                        final_pred_path,
                    )
                else:
                    await run.cpu_bound(
                        apply_cv,
                        reference_info.model_cv_path,
                        reference_info.model_cv_format,
                        reference_info.repository_path,
                        rep_processors_json_final,
                        selected_model_data,
                        full_model_output,
                        final_pred_path,
                    )

                # apply_cv(reference_info_obj.model_cv_path, reference_info_obj.model_cv_format,
                #                    reference_info_obj.repository_path, rep_processors_json_final, selected_model_data, full_model_output, final_pred_path)
            else:
                if ui_notifcation is None:
                    recalc_scores(
                        full_model_output,
                        reference_info.repository_path,
                        selected_model_data,
                        rep_processors_json_final,
                        final_pred_path,
                    )
                else:
                    await run.cpu_bound(
                        recalc_scores,
                        full_model_output,
                        reference_info.repository_path,
                        selected_model_data,
                        rep_processors_json_final,
                        final_pred_path,
                    )

        if ui_notifcation:
            ui_notifcation.message = "Merging with new scores"
            # Read and merge with file:
            selected_model_data_filter = await run.cpu_bound(
                get_merged_res, final_pred_path, selected_model_data_filter
            )

        else:
            logger.info("Merging with new scores")
            # Read and merge with file:
            selected_model_data_filter = get_merged_res(
                final_pred_path, selected_model_data_filter
            )

    return selected_model_data_filter, mask


async def get_final_matrix(
    selected_model_data_filter: pd.DataFrame,
    cache_dir: str,
    model_name: str,
    model_path: str,
    region: str,
    cohort: str,
    reference_info: ReferenceInfo_minimal,
    missing_signals_options: Dict[str, str | bool],
    signals_info: List[InputSignals],
    ui_notifcation: ui.notification = None,
) -> tuple[pd.DataFrame, str, str]:
    model_name_f = unfix_name(model_name)
    full_model_output = await ensure_adjust_model(
        cache_dir, reference_info, model_name_f, model_path, ui_notifcation
    )
    rep_processors_js, mask, need_recalc = get_missing_panels_info(
        missing_signals_options, signals_info
    )

    logger.info(f"Calculating for {model_name}, {region}, {cohort}, {mask}...")
    rep_processors_json_final = (
        """
{
"pre_processors": [{
    "action_type":"rp_set",
    "members":[
"""
        + "\n,".join(rep_processors_js)
        + """
        ]
}]
}
"""
    )

    if not (reference_info.repository_path):
        raise Exception(
            f'Error please define "repository_path" for {model_name} in {region}'
        )
        # run on full data "selected_model_data"

    if ui_notifcation:
        ui_notifcation.message = "Calculating new matrix for this scenario"
    else:
        logger.info("Calculating new matrix for this scenario")
    if reference_info.model_cv_path:
        raise Exception(
            "Not supported in this case - need CV. please try other reference region"
        )
    if ui_notifcation is None:
        calculated_matrix = recalc_scores(
            full_model_output,
            reference_info.repository_path,
            selected_model_data_filter,
            rep_processors_json_final,
            None,
            True,
        )
    else:
        calculated_matrix = await run.cpu_bound(
            recalc_scores,
            full_model_output,
            reference_info.repository_path,
            selected_model_data_filter,
            rep_processors_json_final,
            None,
            True,
        )
    calculated_matrix = calculated_matrix.rename(columns={"outcomeTime": "outcometime"})
    return calculated_matrix, mask, full_model_output


def filter_data_bt(selected_model_data_filter, bt_filter):
    return selected_model_data_filter[bt_filter(selected_model_data_filter)]


def norm_names_lower(df: pd.DataFrame) -> pd.DataFrame:
    cols = sorted(list(set(df.columns) - set(["Time-Window"])))
    names = {"outcome_time": "outcometime"}
    for col in cols:
        if col != col.lower():
            names[col] = col.lower()
    if len(names) > 0:
        df = df.rename(columns=names)
    # Check columns: ['id', 'time' ,'outcome', 'outcometime', 'split', 'pred_0']
    checkup_cols = set(["id", "time", "outcome", "outcometime", "split", "pred_0"])
    final_cols = set(list(df.columns))
    miss_cols = sorted(list(checkup_cols - final_cols))
    if len(miss_cols) > 0:
        raise Exception(f"Error, missing columns in reference: [{miss_cols}]")
    if "Time-Window" not in final_cols:
        df["Time-Window"] = 0
        df.loc[df["outcometime"] % 100 == 0, "outcometime"] = (
            df.loc[df["outcometime"] % 100 == 0, "outcometime"] + 1
        )  # fix days
        df.loc[df["outcometime"] // 100 % 100 == 0, "outcometime"] = (
            df.loc[df["outcometime"] // 100 % 100 == 0, "outcometime"] + 100
        )  # fix month
        df.loc[df["time"] % 100 == 0, "time"] = (
            df.loc[df["time"] % 100 == 0, "time"] + 1
        )  # fix days
        df.loc[df["time"] // 100 % 100 == 0, "time"] = (
            df.loc[df["time"] // 100 % 100 == 0, "time"] + 100
        )  # fix month
        df.loc[df["outcome"] > 0, "Time-Window"] = (
            pd.to_datetime(df.loc[df["outcome"] > 0, "outcometime"], format="%Y%m%d")
            - pd.to_datetime(df.loc[df["outcome"] > 0, "time"], format="%Y%m%d")
        ).dt.days
    return df


def auto_format(measure: str) -> str:
    format_3_set = set(
        [
            "AUC",
            "PART_AUC",
            "Harrell-C-Statistic",
            "Kendall-Tau",
            "R2",
            "RMSE",
            "LOGLOSS",
        ]
    )
    format_1_set = set(["NPOS", "NNEG", "Checksum"])
    if measure in format_3_set or measure.find("PART_AUC") >= 0:
        return "%2.3f"
    elif measure in format_1_set:
        return "%d"
    elif measure.startswith("SCORE@"):
        return "%2.5f"
    else:
        return "%2.1f"


def trim_numbers(df: pd.DataFrame):
    for col in df.columns:
        if col == "Measure":
            continue
        df[col] = df[["Measure", col]].apply(
            lambda row: auto_format(row["Measure"]) % (row[col]), axis=1
        )
    return df


def process_res(res: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    res = trim_numbers(res)
    regex_mes = re.compile(
        "AUC|(SENS|OR|SCORE|SPEC|FPR|PPV|PR)@(FPR|TOPN|SCORE|SENS|PR)"
    )
    # regex_mes = re.compile("AUC|(SENS|OR|SCORE|SPEC|FPR|PPV)@(FPR|TOPN|SCORE|SENS)")
    npos = float(res[res["Measure"] == "NPOS"]["Obs"].iloc[0])
    nneg = float(res[res["Measure"] == "NNEG"]["Obs"].iloc[0])
    res = res[["Measure", "Mean", "CI.Lower.95", "CI.Upper.95"]]
    res = res.rename(
        columns={"CI.Lower.95": "CI_Lower_95", "CI.Upper.95": "CI_Upper_95"}
    )
    res["Measure"] = res["Measure"].apply(
        lambda x: x if not (x.endswith(".000")) else x[:-4]
    )
    # res = res[
    #     (~res["Measure"].str.contains("FPR@PR_"))
    #     & (~res["Measure"].str.contains("PR@FPR_"))
    #     & (~res["Measure"].str.contains("SPEC@PR_"))
    # ].reset_index(drop=True)
    res = res[res["Measure"].apply(lambda x: len(regex_mes.findall(x)) > 0)]
    # Filter None values:
    logger.info(f"Has {len(res)} records in result")
    res = res[abs(res["Mean"].astype(float) + 65336) >= 0.01].reset_index(drop=True)
    logger.info(f"Has {len(res)} records in result after filtering Nones")
    return res, npos, nneg


# Generate matching from our population to reference data:
def proc_record(full_df, rec):
    pid = rec.pop("pid")
    code = rec.pop("code")
    if str(rec["timestamp"]) == "nan":
        rec.pop("timestamp")
        rec["timestamp"] = []
    else:
        rec["timestamp"] = [int(rec["timestamp"])]
    if str(rec["unit"]) == "nan":
        rec.pop("unit")
    if str(rec["value"]) == "nan":
        rec.pop("value")
        rec["value"] = []
    else:
        val = rec["value"]
        rec["value"] = [val]

    if pid not in full_df:
        full_df[pid] = {}
    if code not in full_df[pid]:
        full_df[pid][code] = {"code": code, "data": []}
    full_df[pid][code]["data"].append(rec)
    return full_df


def final_transform(js: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_data = []
    for pid, data in js.items():
        final_js = {}
        final_js["patient_id"] = pid
        final_js["signals"] = []
        for signal_name, sig_data in data.items():
            final_js["signals"].append({"code": signal_name, "data": sig_data["data"]})
        all_data.append(final_js)
    return all_data


def get_exact_names(df: pd.DataFrame, feat_names: List[str]) -> List[str]:
    use_features_final = []
    all_feat_names = list(df.columns)
    for fname in feat_names:
        if fname in all_feat_names:
            use_features_final.append(fname)
        else:
            res_find = list(filter(lambda x: x.find(fname) >= 0, all_feat_names))
            if len(res_find) != 1:
                for ii in res_find:
                    print(f"Optional Name: {ii}")
                raise Exception(f"Cant locate feature {fname} - {len(res_find)}")
            res_find = res_find[0]
            use_features_final.append(res_find)
    return use_features_final


def generate_clients_matrix(
    model_path: str,
    repository_path: str,
    clients_inputs_data: pd.DataFrame,
    samples: med.Samples | pd.DataFrame,
    samples_is_df: bool = False,
) -> pd.DataFrame:
    all_js = clients_inputs_data.to_dict(orient="records")
    full_data = {}
    for i in range(len(all_js)):
        full_df = proc_record(full_data, all_js[i])
    final_res = final_transform(full_df)
    js_data = {"multiple": final_res}
    data_req_str = json.dumps(js_data)
    rep = med.PidRepository()
    rep.switch_to_in_mem()
    rep.init(repository_path)
    rep.load_from_json_str(data_req_str)
    model = med.Model()
    model.read_from_file(model_path)

    if samples_is_df:
        smp = med.Samples()
        smp.from_df(samples)
        model.apply(rep, smp)
    else:
        model.apply(rep, samples)
    full_matrix = model.features.to_df()
    return full_matrix


def compare_feature_matrices(
    current_ref_matrix: pd.DataFrame,
    clients_matrix: pd.DataFrame,
    use_features: List[str] | None = None,
) -> Tuple[pd.DataFrame, int]:
    # Train propensity model! - maybe select only important features?

    ref_data = current_ref_matrix[
        ["id", "time", "outcome", "outcometime", "pred_0"]
    ].copy()
    if use_features:
        ref_matrix = current_ref_matrix[use_features]
        c_matrix = clients_matrix[use_features]
    else:
        c_matrix = clients_matrix
        ref_matrix = current_ref_matrix

    ref_matrix = ref_matrix.drop(
        columns=["id", "outcome", "split", "pred_0"],
        errors="ignore",
    )
    ref_matrix["id"] = ref_matrix.index + 1
    ref_matrix["outcome"] = 0
    ref_matrix["split"] = -1

    c_matrix = c_matrix.drop(
        columns=["id", "outcome", "split", "pred_0"],
        errors="ignore",
    )
    start_pid = ref_matrix["id"].max()
    c_matrix["id"] = start_pid + c_matrix.index + 1
    c_matrix["outcome"] = 1
    c_matrix["split"] = -1
    train_matrix = pd.concat([ref_matrix, c_matrix], ignore_index=True)
    all_columns = set(train_matrix.columns)
    all_columns.remove("outcome")
    all_columns.remove("id")
    all_columns.remove("split")
    # Train XGboost on c_matrix, ref_matrix
    # dtrain = DMatrix(data=train_matrix[list(all_columns)], label=train_matrix['outcome'])
    propensity = XGBClassifier(
        colsample_bylevel=1,
        colsample_bytree=1,
        gamma=0,
        learning_rate=0.05,
        max_delta_step=0,
        max_depth=6,
        min_child_weight=1,
        n_estimators=150,
        nthread=-1,
        objective="binary:logistic",
        reg_alpha=0,
        reg_lambda=1,
        scale_pos_weight=1,
        seed=0,
        subsample=1,
    )
    propensity = propensity.fit(
        train_matrix[list(all_columns)], train_matrix["outcome"]
    )
    # Recalibrate? xgboost already calibrated, skip
    # Use IPW score to match ref to c and retrieve weights:
    ref_scores = propensity.predict_proba(
        train_matrix[list(all_columns)].iloc[:start_pid].values
    )
    ref_scores = ref_scores[:, 1]
    ref_matrix["prob_client"] = ref_scores
    # Equation is [P - model score, W final weight]: W := P / (1-P). Need to handle P==1
    eps = 1e-4
    exclude_idx = ref_scores >= 1 - eps
    ref_matrix["weight"] = np.nan
    ref_matrix.loc[~exclude_idx, "weight"] = ref_matrix.loc[
        ~exclude_idx, "prob_client"
    ] / (1 - ref_matrix.loc[~exclude_idx, "prob_client"])
    ref_matrix = pd.concat(
        [ref_matrix.drop(columns=["id", "outcome"]), ref_data], axis=1
    )
    sum_w = ref_matrix["weight"].sum()
    cl_size = len(clients_matrix)
    print(f"Santiy test: client size {cl_size} vs weighted size {sum_w:.0f}")
    # Test Un represented patients:
    ref_scores_client = propensity.predict_proba(
        train_matrix[list(all_columns)].iloc[start_pid:].values
    )
    ref_scores_client = ref_scores_client[:, 1]
    # Check how many receives "1" or close to it and they can be coinsidered as excluded:
    not_represented_cnt = sum(ref_scores_client >= 1 - eps)

    return ref_matrix, not_represented_cnt


def get_samples_from_recent_lab(
    final_res: pd.DataFrame, lab_name: str = "Hemoglobin"
) -> med.Samples:
    samples = med.Samples()

    df = (
        final_res[final_res["code"] == lab_name]
        .sort_values(["pid", "timestamp"], ascending=[True, False])
        .drop_duplicates(subset=["pid"])[["pid", "timestamp"]]
    )
    df.columns = ["id", "time"]
    df["outcome"] = 0
    df["outcomeTime"] = 20300101
    df["split"] = -1
    df = df[["id", "time", "outcome", "outcomeTime", "split"]]
    samples.from_df(df)
    return samples


def full_matching_propensity(
    current_ref_matrix: pd.DataFrame,
    clients_inputs_data: pd.DataFrame,
    model_path: str,
    repository_path: str,
    samples: med.Samples,
):
    clients_matrix = generate_clients_matrix(
        model_path, repository_path, clients_inputs_data, samples
    )
    # Compare clients_matrix to current_ref_matrix
    ref_matrix_weighted, not_represented = compare_feature_matrices(current_ref_matrix, clients_matrix)
    # res = get_bt(ref_matrix_weighted.drop(columns=['weight']), ref_matrix_weighted['weight'], sample_per_pid, top_n_value, thresholds_values)
