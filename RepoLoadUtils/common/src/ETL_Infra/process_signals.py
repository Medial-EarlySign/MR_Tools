import os
import pandas as pd
import numpy as np


def process_default_after(df, signal_name, sig_types, workdir):
    # convert pid to id2nr
    ID2NR_path = os.path.join(workdir, "FinalSignals", "ID2NR")
    START_ID = 1
    MAX_INT = 2**31

    x = pd.to_numeric(df["pid"].sample(min(10000, len(df))), errors="coerce")
    non_numeric_cnt = x.isnull().sum()
    if non_numeric_cnt == 0 and x.max() < MAX_INT and x.min() > 0:
        return df
    if non_numeric_cnt == 0:
        print(
            "ID's are numeric but bigger then MAX_INT or not positive, will use ID2NR"
        )
    write_mode = "w"
    pid_map = None
    if os.path.exists(ID2NR_path):
        pid_map = pd.read_csv(
            ID2NR_path,
            sep="\t",
            names=["source_pid", "target_pid"],
            dtype={"source_pid": "str"},
        )  # 2 cols - from, to
        write_mode = "a"

    # Don't filter missing ids - will be filtered/tested later
    df["pid"] = df["pid"].astype(
        str
    )  # Ensure that this is string and not big integer or something
    allowed_sigs = set(["BYEAR", "BDATE", "GENDER", "demographic"])
    if signal_name in allowed_sigs:
        print(
            "Found that patient id is string and needs to be converted into numbers",
            flush=True,
        )
        if write_mode == "a" and pid_map is not None:
            print("Will append to existing ID2NR", flush=True)
            pid_map_ = pd.DataFrame({"source_pid": df["pid"].unique()})
            pid_map_ = pid_map_[
                ~pid_map_["source_pid"].isin(pid_map["source_pid"])
            ].reset_index(
                drop=True
            )  # keep only new pids
            START_ID = pid_map["target_pid"].max() + 1
            pid_map_["target_pid"] = START_ID + np.array(range(len(pid_map_)))
            pid_map = (
                pd.concat([pid_map, pid_map_], ignore_index=True)
                .sort_values("target_pid")
                .reset_index(drop=True)
            )
            # Rewrite all
        else:
            pid_map = pd.DataFrame({"source_pid": df["pid"].unique()})
            pid_map["target_pid"] = START_ID + np.array(range(len(pid_map)))

        pid_map = pid_map[["source_pid", "target_pid"]]
        pid_map["target_pid"] = pid_map["target_pid"].astype(int)
        pid_map.to_csv(ID2NR_path, sep="\t", index=False, header=False)
        print("Stored mapping of patient identifiers map %s" % (ID2NR_path), flush=True)
    else:
        if not (os.path.exists(ID2NR_path)):
            raise Exception(
                "Error - please process BDATE,BYEAR,Gender,demographic first to generate ID2NR file.\nPatient id is not numeric, requested to process %s"
                % (signal_name)
            )
        print(
            f"Patient id is not numeric - using {ID2NR_path} to convert into numbers",
            flush=True,
        )

    df = (
        df.set_index("pid")
        .join(
            pid_map.rename(columns={"source_pid": "pid"}).set_index("pid"), how="left" # type: ignore
        )
        .reset_index(drop=True)
        .rename(columns={"target_pid": "pid"})
    )
    # Keep in mind that rows without mapping, might have None in pid now!

    return df


def process_default_before(df, signal_name, sig_types, workdir):
    return df
