import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
from logic import get_bt
from logic_med import (
    compare_feature_matrices,
    generate_clients_matrix,
    get_exact_names,
    get_samples_from_recent_lab,
)

ref_lgi = "/server/Work/Users/Alon/LGI/outputs/reference_matrix/features.matrix"
clients_input_data = "/nas1/Work/Users/Alon/LGI/Belgium/belgium_input_data.tsv"
model_path = "/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.model"
repository_path = "/nas1/Work/CancerData/Repositories/THIN/thin_jun2017/thin.repository"
# scores_source =  None
scores_source = "/nas1/UsersData/alon/MR/Tools/AlgoMarker_python_API/PopulationAnalyzer/cache/preds/LGIFlag/UK-THIN/CBC_MostRecent_MPV_0_Platelets_0_RDW_0_White_Panel_0"  # TODO: better to have matrix with scores for this scenario
sample_per_pid = 1
top_n_value = []
thresholds_values = [0.13]
# use_features = None
# use_features = ["Age"]
# Age:1,Gender:1,FTR_000074.MCH.slope.win_0_1000:0.5,MCH.min.win_0_180:0.5,Platelets.Estimate.360:1,Platelets.win_delta.win_0_180_730_10000:5,MPV.min.win_0_10000:0.1,Hemoglobin.last.win_0_10000:0.2,Hemoglobin.slope.win_0_730:0.1,Hematocrit.Estimate.360:0.2,Neutrophils%.std.win_0_10000:0.2
use_features = ["Age", "Gender", "MCH.min.win_0_180", "Hemoglobin.min.win_0_180"]


clients_input = pd.read_csv(clients_input_data, sep="\t", dtype={"value": "str"})
print("Read clients input")

ref_matrix = pd.read_csv(ref_lgi).rename(columns={'outcome_time':'outcometime'})
if scores_source:
    new_scores = pd.read_csv(scores_source, sep="\t")
    ref_matrix = ref_matrix.drop(columns=["pred_0"]).merge(
        new_scores[["id", "time", "pred_0"]], on=["id", "time"], how="inner"
    )
# Locate name accurately:
use_features_final = get_exact_names(ref_matrix, use_features)

print("Read reference")
# LOGIC for samples
samples = get_samples_from_recent_lab(clients_input, "Hemoglobin")
# End logic for samples

clients_matrix = generate_clients_matrix(
    model_path, repository_path, clients_input, samples
)
# Compare clients_matrix to current_ref_matrix
ref_matrix_weighted, not_represented = compare_feature_matrices(ref_matrix, clients_matrix, use_features_final)
breakpoint()
# Get age dist:
age_original = (
    ref_matrix_weighted["Age"].value_counts().reset_index().sort_values("Age")
)
age_original["p"] = 100 * age_original["count"] / age_original["count"].sum()
age_original_client = (
    clients_matrix["Age"].value_counts().reset_index().sort_values("Age")
)
age_original_client["p"] = (
    100 * age_original_client["count"] / age_original_client["count"].sum()
)
age_ref_match_to_client = (
    ref_matrix_weighted[["Age", "weight"]]
    .groupby("Age")
    .sum()
    .reset_index()
    .sort_values("Age")
)
age_ref_match_to_client["p"] = (
    100 * age_ref_match_to_client["weight"] / age_ref_match_to_client["weight"].sum()
)
age_original_client.columns = [
    "Age",
    "count_client_original",
    "percentage_original_client",
]
age_ref_match_to_client.columns = [
    "Age",
    "count_ref_matched_to_client",
    "percentage_matched_to_original_client",
]
age_grp = age_original_client.merge(
    age_ref_match_to_client, on="Age", how="outer"
).fillna(0)
print(age_grp)

res = get_bt(
    ref_matrix_weighted.drop(columns=["weight"]),
    ref_matrix_weighted["weight"],
    sample_per_pid,
    top_n_value,
    thresholds_values,
)
print(res)
