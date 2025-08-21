from typing import List, Tuple
from pydantic import BaseModel
import pandas as pd
import numpy as np
import med
import subprocess
from logger import logger


class Strata(BaseModel):
    feature_name: str

    def get_bin(self, df: pd.DataFrame) -> pd.Series:
        raise Exception("Not implemented")


class StrataRange(Strata):
    min_range: float
    max_range: float

    def __str__(self):
        return f"{self.feature_name} [{self.min_range} - {self.max_range}]"

    def __repr__(self):
        return self.__str__()

    def get_bin(self, df: pd.DataFrame) -> pd.Series:
        fname = self.feature_name.lower()
        if fname not in df.columns:
            raise Exception(
                f"Error - can't use {self.feature_name} for matching. Not found in db"
            )
        cond = (df[fname] >= self.min_range) & (df[fname] <= self.max_range)
        return cond


class StrateCategory(Strata):
    categoty_value: str

    def __str__(self):
        return f"{self.feature_name}: {self.categoty_value}"

    def __repr__(self):
        return self.__str__()

    def get_bin(self, df: pd.DataFrame) -> pd.Series:
        fname = self.feature_name.lower()
        if fname not in df.columns:
            raise Exception(
                f"Error - can't use {self.feature_name} for matching. Not found in db"
            )
        cond = df[fname].astype(str) == self.categoty_value
        return cond


class StrataStats(BaseModel):
    stratas: List[Strata]
    prob: float

    def __str__(self):
        if len(self.stratas) == 0:
            return ""
        s = str(self.stratas[0])
        for strata in self.stratas[1:]:
            s += f"|{strata}"
        s += f" => {self.prob}"
        return s

    def __repr__(self):
        return self.__str__()

    def get_bin(self, df: pd.DataFrame) -> pd.Series:
        if len(self.stratas) == 0:
            return None
        cond = self.stratas[0].get_bin(df)
        for strat in self.stratas[1:]:
            cond = cond & strat.get_bin(df)
        return cond


def get_incidence(
    selected_model_data_filter: pd.DataFrame,
    sample_per_pid: int,
    control_weight: float,
    cases_weight: float | None = None,
    SET_COHORT_SIZE: int = 1e6,
) -> float:
    if sample_per_pid > 0:
        npos_ref = len(
            selected_model_data_filter[
                selected_model_data_filter["outcome"] > 0
            ].drop_duplicates(subset=["id"])
        )
        nneg_ref = len(
            selected_model_data_filter[
                selected_model_data_filter["outcome"] <= 0
            ].drop_duplicates(subset=["id"])
        )
    else:
        npos_ref = len(
            selected_model_data_filter[selected_model_data_filter["outcome"] > 0]
        )
        nneg_ref = len(
            selected_model_data_filter[selected_model_data_filter["outcome"] <= 0]
        )
    incidence_ref = 0
    if control_weight:
        nneg_ref = nneg_ref * control_weight
    total_n = nneg_ref + npos_ref
    global_factor = SET_COHORT_SIZE / total_n

    npos_ref = npos_ref * global_factor
    nneg_ref = nneg_ref * global_factor
    if control_weight:
        control_weight = control_weight * global_factor
    else:
        control_weight = global_factor
    if cases_weight:
        cases_weight = cases_weight * global_factor
    else:
        cases_weight = global_factor

    if npos_ref > 0:
        incidence_ref = npos_ref / (npos_ref + nneg_ref)
    return incidence_ref


def get_weights(
    matrix_df: pd.DataFrame,
    stratas: List[StrataStats],
    stratas_inc: List[StrataStats] | None,
) -> Tuple[List[float], float]:
    # Match gender,sex names:
    data_col_name = "sex" if "sex" in matrix_df.columns else "gender"
    stat_name = None
    for strata_s in stratas:
        for strata in strata_s.stratas:
            fname = strata.feature_name.lower()
            if fname not in ["sex", "gender"]:
                continue
            stat_name = fname
            break
    if stat_name:
        if stat_name != data_col_name:
            matrix_df = matrix_df.rename(columns={data_col_name: stat_name})
            logger.info(f"Rename {data_col_name} to {stat_name}")

    tot_size = len(matrix_df)
    weights = np.zeros(tot_size)
    matrix_df.columns = list(map(lambda x: x.lower(), list(matrix_df.columns)))
    # Test sum of all stratas:
    tot_prob = sum(map(lambda x: x.prob, stratas))
    if abs(tot_prob - 100) < 1e-4:
        # divide by 100:
        for strata_s in stratas:
            strata_s.prob = strata_s.prob / 100
        tot_prob = tot_prob / 100
    if abs(tot_prob - 1) > 1e-4:
        raise Exception(
            f"Error - input stratas is not distribution, reached {tot_prob}"
        )

    # Assume stratas_inc names are the same as stratas - sex/gender
    idx_cahce = []
    if stratas_inc:
        for starta_inc_s in stratas_inc:
            idx_cahce.append(starta_inc_s.get_bin(matrix_df))
    prob_not_represented = 0
    for strata_s in stratas:
        for strata in strata_s.stratas:
            fname = strata.feature_name.lower()
            if fname not in matrix_df.columns:
                raise Exception(
                    f"Error - can't use {strata.feature_name} for matching. Not found in db, source: strata"
                )
        all_idx = strata_s.get_bin(matrix_df)
        current_bin_size_orig = len(matrix_df[all_idx])
        prob_original = current_bin_size_orig / tot_size
        if prob_original == 0:
            prob_not_represented += strata_s.prob
            continue
        # Check in stratas_inc
        if stratas_inc:
            for indx_cache, starta_inc_s in enumerate(stratas_inc):
                for strata_inc_ in starta_inc_s.stratas:
                    fname = strata_inc_.feature_name.lower()
                    if fname not in matrix_df.columns:
                        raise Exception(
                            f"Error - can't use {strata_inc_.feature_name} for matching. Not found in db, source: strata_inc"
                        )
                all_idx_inc = idx_cahce[indx_cache]
                # Combine with all_idx:
                current_idx = all_idx & all_idx_inc
                bin_size_part = len(matrix_df[current_idx])
                if bin_size_part == 0:
                    continue
                expected_inc = starta_inc_s.prob

                # Not zero now slice based on label:

                cases_mask = current_idx & (matrix_df["outcome"] > 0)
                controls_mask = current_idx & (matrix_df["outcome"] < 1)
                cases_cnt = sum(cases_mask)
                controls_cnt = sum(controls_mask)
                inc_in_group = cases_cnt / (cases_cnt + controls_cnt)
                if inc_in_group == 0 and expected_inc > 0:
                    prob_not_represented += strata_s.prob * (
                        bin_size_part / current_bin_size_orig
                    )
                    continue
                # Reweight cases, controls to match the expected_inc
                factor_size = strata_s.prob * (bin_size_part / current_bin_size_orig)
                pos_final_weight = factor_size / (((1 / expected_inc) * cases_cnt))
                neg_final_weight = (
                    ((1 - expected_inc) / expected_inc)
                    * (cases_cnt / controls_cnt)
                    * pos_final_weight
                )  # cause incidence to be expected_inc
                # neg_final_weight * controls_cnt + pos_final_weight * cases_cnt = factor_size

                weights[cases_mask] = pos_final_weight
                weights[controls_mask] = neg_final_weight
                logger.info(
                    f"Bin,{starta_inc_s},prob_original,{prob_original},expected_prob,{strata_s.prob},factor_size,{factor_size},neg,{neg_final_weight},pos,{pos_final_weight},bin_size_part,{bin_size_part},current_bin_size_orig,{current_bin_size_orig},cases_cnt,{cases_cnt},controls_cnt,{controls_cnt}"
                )
        else:
            weight = strata_s.prob / prob_original
            weights[all_idx] = weight

    # Normalize total weight:
    tot_w_sum = sum(weights)
    if tot_w_sum < 1e-4:
        return weights, prob_not_represented
    tot_size_len = sum(weights > 0)
    weights = weights / tot_w_sum * tot_size_len
    return weights, prob_not_represented


def get_bt(
    matrix_df: pd.DataFrame,
    weights: List[float],
    sample_per_pid: int = 1,
    top_n_value: List[int] = [],
    thresholds_values: List[float] = [],
    sensitivity_values: List[float] = [],
) -> pd.DataFrame:
    bt = med.Bootstrap()
    bt.ROC_working_point_PR = [0.5] + list(range(1, 100))
    bt.ROC_working_point_FPR = [0.5] + list(range(1, 100))
    bt.ROC_working_point_SENS = [60, 65, 70, 75, 80, 85, 90]
    bt.ROC_working_point_TOPN = top_n_value
    bt.ROC_working_point_Score = thresholds_values
    bt.ROC_working_point_SENS = sensitivity_values
    bt.sample_per_pid = sample_per_pid
    bt.ROC_max_diff_working_point = 0.2
    samples = med.Samples()
    matrix_df["split"] = -1
    matrix_df["attr_weight"] = weights
    # logger.info(matrix_df['attr_weight'].value_counts())
    cols = ["id", "time", "outcome", "outcometime", "split", "pred_0", "attr_weight"]
    samples_df = matrix_df[cols].copy()
    samples.from_df(samples_df)
    res = bt.bootstrap_cohort(samples, "", "", "").to_df()
    res = res[["Measurement", "Value"]]
    res = res[res["Measurement"] != "Checksum"].reset_index(drop=True)
    res["Measure"] = res["Measurement"].apply(
        lambda x: x[: x.rfind("_")] if x.find("_") > 0 else x
    )
    res["Description"] = res["Measurement"].apply(
        lambda x: x[x.rfind("_") + 1 :] if x.find("_") > 0 else ""
    )
    res = (
        res[["Measure", "Description", "Value"]]
        .pivot(index="Measure", columns="Description", values="Value")
        .reset_index()
    )
    return res


def full_run(
    matrix_df: pd.DataFrame,
    stratas: List[StrataStats],
    strata_inc: List[StrataStats] | None,
    control_weight: float | None,
    caes_weight: float | None,
    sample_per_pid: int = 1,
    top_n_value: List[int] = [],
    thresholds_values: List[float] = [],
):
    weights, prob_not_represented = get_weights(matrix_df, stratas, strata_inc)
    if control_weight:
        change_indicies = matrix_df["outcome"] <= 0
        logger.info(f"Set control weight to {control_weight}")
        weights[change_indicies] = weights[change_indicies] * control_weight
    if caes_weight:
        change_indicies = matrix_df["outcome"] > 0
        logger.info(f"Set case weight to {caes_weight}")
        weights[change_indicies] = weights[change_indicies] * caes_weight
    res = get_bt(matrix_df, weights, sample_per_pid, top_n_value, thresholds_values)
    return res, prob_not_represented


def fit_model_to_rep(model_path: str, repo_path: str, output_path: str):
    cmd = f'Flow --fit_model_to_rep --cleaner_verbose -1 --remove_explainability 1 --f_model "{model_path}" --rep {repo_path} --f_output "{output_path}"'
    subprocess.run(cmd, shell=True, check=True)
