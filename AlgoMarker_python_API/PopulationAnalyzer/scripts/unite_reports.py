#!/usr/bin/env python
import os
import pandas as pd

OUTPUT_DIR = "/nas1/Work/Users/Alon/LGI/outputs/cutoff_simulations"

all_dfs = []
for model_dir in os.listdir(OUTPUT_DIR):
    full_model_path = os.path.join(OUTPUT_DIR, model_dir)
    if not (os.path.isdir(full_model_path)):
        continue
    csv_files = list(filter(lambda x: x.endswith("csv"), os.listdir(full_model_path)))
    for csv_file in csv_files:
        df = pd.read_csv(os.path.join(full_model_path, csv_file), sep="\t")
        cols = list(df.columns)
        ind = csv_file.find(".strat")
        assert ind >= 0
        full_without_strata = csv_file[:ind]
        tokens = full_without_strata.split("_")
        ind2 = tokens[2].find(".strat")
        df["model"] = model_dir
        df["file_name"] = csv_file
        df["data_source"] = tokens[1]
        df["cohort"] = tokens[2]
        df["history_limit"] = '_'.join(tokens[3:])
        df["population_adjustment"] = csv_file[ind:]
        df = df[
            ["model", "file_name", "data_source", "cohort", "population_adjustment", "history_limit"]
            + cols
        ]
        all_dfs.append(df)
df = pd.concat(all_dfs, ignore_index=True)

df.to_csv(os.path.join(OUTPUT_DIR, "all.tsv"), sep="\t", index=False)
print("Wrote")
print(df['data_source'].value_counts(dropna=False))
print(df['population_adjustment'].value_counts(dropna=False))
print(df['history_limit'].value_counts(dropna=False))
print(df['cohort'].value_counts(dropna=False))
