#!/usr/bin/env python
from typing import Any
import med
import os
import pandas as pd
import argparse
import json


def __get_signal_units(rep_config: str):
    with open(rep_config, "r") as fr:
        lines = fr.readlines()
    sig_line = list(filter(lambda x: x.startswith("SIGNAL"), lines))
    assert len(sig_line) == 1
    sig_line = sig_line[0]
    base_dir = os.path.dirname(rep_config)
    sig_path = sig_line.split("\t")[1].strip()
    if not (sig_path.startswith("/")):
        sig_path = os.path.join(base_dir, sig_path)
    with open(sig_path, "r") as fr:
        lines = fr.readlines()
    sig_to_unit = {}
    for line in lines:
        if not (line.startswith("SIGNAL")):
            continue
        tokens = line.split("\t")
        sig_name = tokens[1]
        sig_unit = ""
        if len(tokens) >= 7:
            sig_unit = tokens[6]
        sig_to_unit[sig_name] = sig_unit
    return sig_to_unit


def __generate_data(
    data: pd.DataFrame, sig_units: dict[str, str], pid: int
) -> dict[str, Any] | None:
    df_pid = data[data["pid"] == pid].reset_index(drop=True)
    if len(df_pid) == 0:
        print(f"Pid {pid} has no data - skip")
        return None
    req_time = df_pid["time"].iloc[0]
    pid_req = {"patient_id": int(pid), "time": int(req_time)}
    pid_req["data"] = {"signals": []}
    # code, unit, data{value[], timestamp[]}
    for key, sig_df in df_pid.groupby("signal"):
        sig_data = {"code": key, "data": [], "unit": ""}
        if key in sig_units:
            sig_data["unit"] = sig_units[key]  # type: ignore
        # time_vals = list(filter(lambda x: x.startswith("time_"), sig_df.columns))
        # val_vals = list(filter(lambda x: x.startswith("value_"), sig_df.columns))
        all_js_vals = sig_df.apply(
            lambda row: {"timestamp": [row["time_0"]], "value": [row["value_0"]]},
            axis=1,
        )
        sig_data["data"] = list(all_js_vals.values)
        pid_req["data"]["signals"].append(sig_data)
    return pid_req


def generate_data_from_rep(
    rep_path: str, signal_list: list[str], pid_time_df: pd.DataFrame
) -> list[dict[str, Any]]:
    assert "pid" in pid_time_df.columns, "pid column is missing"
    assert pd.api.types.is_integer_dtype(pid_time_df["pid"]), "pid column isn't integer"
    assert "time" in pid_time_df.columns, "time column is missing"
    assert pd.api.types.is_integer_dtype(
        pid_time_df["time"]
    ), "time column isn't integer"
    assert len(pid_time_df.drop_duplicates(subset=["pid"])) == len(
        pid_time_df
    ), "pid_time_df, patient is not unique"
    rep = med.PidRepository()
    pid_list = list(pid_time_df["pid"].unique())
    if rep.read_all(rep_path, pid_list, signal_list) < 0:
        raise Exception(f"Error in reading repository {rep_path}")
    # Generate data for all patients
    data = []
    for sig in signal_list:
        sig_df: pd.DataFrame = rep.get_sig(sig)  # type: ignore
        sig_df = sig_df.rename(
            columns={"time0": "time_0", "val0": "value_0"}, errors="ignore"
        )
        if "time_0" in sig_df.columns: #Otherwise static signal
            sig_df = sig_df.merge(pid_time_df, on="pid", how="inner")
            sig_df = (
                sig_df[sig_df["time"] >= sig_df["time_0"]]
                .reset_index(drop=True)
                .drop(columns=["time"])
            )  # Filter data for each patient till that time
        sig_df["signal"] = sig
        data.append(sig_df)
    data = pd.concat(data, ignore_index=True)
    data = data.merge(pid_time_df, on="pid", how="inner")
    # Convert to json data and request:
    sig_units = __get_signal_units(rep_path)
    all_data = []
    for pid in pid_list:
        js_pid = __generate_data(data, sig_units, pid)
        if js_pid is not None:
            all_data.append(js_pid)
    return all_data


def get_model_signals(model_path: str) -> list[str]:
    model = med.Model()
    model.read_from_file(model_path)
    all_signals = model.get_required_signal_names()
    return all_signals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate json_request file")
    parser.add_argument("--rep_path", help="the repository path", required=True)
    parser.add_argument("--model_path", help="path to model", required=True)
    parser.add_argument(
        "--pid_time_file",
        help="A TSV file with pid,time columns. for each patient requested prediction time",
        required=True,
    )
    parser.add_argument("--output", help="path to output", required=True)

    args = parser.parse_args()
    signals_list = get_model_signals(args.model_path)
    pid_time_df = pd.read_csv(args.pid_time_file, sep="\t").rename(columns={"id":"pid"}, errors="ignore")[["pid", "time"]]
    js_requests_data = generate_data_from_rep(args.rep_path, signals_list, pid_time_df)

    full_request = {
        "type": "request",
        "request_id": "TEST_REQUEST_ID",
        "exports": {"prediction": "pred_0"},
        "load": 1,
        "requests": js_requests_data,
    }
    # Store this in output
    with open(args.output, "w") as fw:
        fw.write(json.dumps(full_request, indent=True))
