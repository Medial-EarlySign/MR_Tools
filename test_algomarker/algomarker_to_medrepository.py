#!/usr/bin/env python
"""
This is the opposite script of create_json_req_from_repository.py
This generates MedRepository Data Files from AlgoMarker json for Data Science deep analysis

Please run this script in folder that you want to configure the loading if needed
"""

import json
import os
from typing import Generator, Callable
import pandas as pd
from tqdm import tqdm
from ETL_Infra.etl_process import prepare_final_signals, finish_prepare_load
import argparse
import subprocess

def algomarker_parser(
    json_content: str,
) -> Callable[[int, int], Generator[pd.DataFrame, None, None]]:
    """
    Returns Callable for `prepare_final_signals` that returns enumerator/generator for each signal that you can iterate and fetch it's data
    """
    static_renames = {"SEX": "GENDER"} # Renames from AlgoMarker official names to MES infra names
    js = json.loads(json_content)
    assert "requests" in js, "AlgoMarker request always contains requests element"
    requests_data = js["requests"]
    data_per_signal: dict[str, list[dict[str, float | str]]] = dict()
    for req in tqdm(requests_data):
        assert (
            "patient_id" in req
        ), "AlgoMarker request element always contains patient_id element"
        patient_id = req["patient_id"]
        assert "data" in req, "AlgoMarker request element always contains data element"
        req_data = req["data"]
        assert (
            "signals" in req_data
        ), "AlgoMarker request data element always contains signals element"
        signals = req_data["signals"]
        for sig in signals:
            assert (
                "code" in sig
            ), "AlgoMarker signal element always contains code element"
            sig_name: str = sig["code"]
            if sig_name in static_renames:
                sig_name = static_renames[sig_name]
            assert (
                "data" in sig
            ), "AlgoMarker signal element always contains data element"
            sig_data = sig["data"]
            for dd in sig_data:
                assert (
                    "timestamp" in dd
                ), "AlgoMarker data element always contains timestamp element"
                timestamp = dd["timestamp"]
                assert (
                    "value" in dd
                ), "AlgoMarker data element always contains value element"
                value = dd["value"]
                if sig_name not in data_per_signal:
                    data_per_signal[sig_name] = []
                df_raw_data = {"pid": patient_id, "signal": sig_name}
                for i, t in enumerate(timestamp):
                    df_raw_data[f"time_{i}"] = t
                for i, v in enumerate(value):
                    df_raw_data[f"value_{i}"] = v
                data_per_signal[sig_name].append(df_raw_data)
    df_per_signal: dict[str, pd.DataFrame] = dict()
    for sig_name, data in data_per_signal.items():
        df_per_signal[sig_name] = pd.DataFrame(data)

    def wrapper_generator(batch_size: int, start_from: int):
        for sig_name, df in df_per_signal.items():
            yield df

    return wrapper_generator


def main_load(work_dir: str, final_repo_dir: str, request_json_content: str):
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(final_repo_dir, exist_ok=True)
    succ = prepare_final_signals(
        algomarker_parser(request_json_content),
        work_dir,
        "all",
        batch_size=1,
        override="n",
    )
    if not (succ):
        raise Exception("Failed!")
    finish_prepare_load(work_dir, final_repo_dir, "test")


# --- USAGE ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate loading files to load repository from algomarker json"
    )
    parser.add_argument(
        "--algomarker_json_path", help="the algomarker json request path", required=True
    )
    parser.add_argument(
        "--work_dir", help="path to process the loading files", required=True
    )
    parser.add_argument(
        "--final_repo_dir", help="path to final repository directory", required=True
    )

    args = parser.parse_args()
    with open(args.algomarker_json_path, "r") as fr:
        request_json_content = fr.read()
    main_load(args.work_dir, args.final_repo_dir, request_json_content)
    # Now we will run the load script:
    full_script = os.path.join(args.work_dir, "rep_configs", "load_with_medpython.py")
    subprocess.run(full_script, shell=True)
    print(f"Done! - use this repository: {os.path.join(args.final_repo_dir, 'test.repository')}")