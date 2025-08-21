#!/usr/bin/env python
import os
import pandas as pd

OUTPUT_DIR = "/nas1/Work/Users/Alon/LGI/outputs/cutoff_simulations"
MODEL = "GastroFlag"

SELECT_COHORTS = "Time-window: 365"
rename_pop = {
    ".strats.simple.all.csv": "GEN",
    ".stratas.TW_HC_NORM.csv": "YG",
    ".stratas.Japan_NORM.csv": "ELD",
}
history_limit_names = {"": "AL", "CBC_LimitYears3": "3YR", "CBC_MostRecent": "1T"}

all_dfs = []
full_model_path = os.path.join(OUTPUT_DIR, MODEL)

csv_files = list(filter(lambda x: x.endswith("csv"), os.listdir(full_model_path)))
for csv_file in csv_files:
    df = pd.read_csv(os.path.join(full_model_path, csv_file), sep="\t")
    cols = list(df.columns)
    ind = csv_file.find(".strat")
    assert ind >= 0
    full_without_strata = csv_file[:ind]
    tokens = full_without_strata.split("_")
    ind2 = tokens[2].find(".strat")
    if csv_file[ind:] == ".stratas.Medicare_NORM.csv":
        continue
    # df["model"] = MODEL
    # df["file_name"] = csv_file
    # df["data_source"] = tokens[1]
    df["_cohort"] = tokens[2]
    df = df[df["_cohort"].str.contains(SELECT_COHORTS)].reset_index(drop=True)
    df["history_limit"] = history_limit_names["_".join(tokens[3:])]
    df["population_adjustment"] = rename_pop[csv_file[ind:]]
    df["age"] = df["_cohort"].apply(lambda x: x.split(",")[0].split(":")[1].strip())
    df["Cohort"] = (
        df["population_adjustment"] + "_" + df["age"] + "_" + df["history_limit"]
    )
    df = df[["Cohort"] + cols]
    all_dfs.append(df)

df = pd.concat(all_dfs, ignore_index=True)
df["Measure"] = df["Measure"].apply(
    lambda x: x if x.find("@") < 0 or x.find(".") > 0 else x + ".000"
)
df_val = df.copy()

df_val["Measurement"] = df_val["Measure"] + "_Mean"

df_val["Value"] = df_val["Mean"]
df_val = df_val[["Cohort", "Measurement", "Value"]]
df_lower = df.copy()
df_lower["Measurement"] = df_lower["Measure"] + "_CI.Lower.95"
df_lower["Value"] = df_lower["CI_Lower_95"]
df_lower = df_lower[["Cohort", "Measurement", "Value"]]
df_upper = df.copy()
df_upper["Measurement"] = df_upper["Measure"] + "_CI.Upper.95"
df_upper["Value"] = df_upper["CI_Upper_95"]
df_upper = df_upper[["Cohort", "Measurement", "Value"]]
# _Obs, _Std
df = (
    pd.concat([df_val, df_lower, df_upper], ignore_index=True)
    .sort_values(["Cohort", "Measurement"])
    .reset_index(drop=True)
)

df.to_csv(os.path.join(OUTPUT_DIR, "gastro_flag.tsv"), sep="\t", index=False)
print("Wrote")
