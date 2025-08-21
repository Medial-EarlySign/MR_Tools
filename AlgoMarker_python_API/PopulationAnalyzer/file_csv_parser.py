from io import StringIO
from typing import List
from pydantic import BaseModel
from logic import StrataStats, Strata, StrataRange, StrateCategory
import pandas as pd
import math
import traceback
from logger import logger


class ErrorFewObs(Exception):
    tot_count: int

    def __init__(self, msg: str, tot_count: int):
        self.msg = msg
        self.tot_count = int(tot_count)


class ErrorNotDistribution(Exception):
    tot_prob: float

    def __init__(self, msg: str, tot_prob: int):
        self.msg = msg
        self.tot_prob = tot_prob


def parse_file_complex(file_content: str) -> List[StrataStats]:
    """File Format: Header: (feature name1,min_range_1, max_range_1), feature_name2, etc.. last column is the probability .
    so 3 columns for each Strata: name, min, max.
    Parse df into StrataStats
    """
    lines = file_content.split("\n")  # dos2unis?
    lines = list(filter(lambda x: len(x.strip()) > 0, lines))

    full_strata_stats = []
    for line in lines:
        tokens = line.split(",")
        _prob = float(tokens[-1])
        tokens = tokens[:-1]
        all_stratas = []
        for i in range(0, len(tokens), 3):
            feat_name, _min_range, _max_range = tokens[i : i + 3]
            _min_range = float(_min_range)
            _max_range = float(_max_range)
            strata = StrataRange(
                feature_name=feat_name, min_range=_min_range, max_range=_max_range
            )
            all_stratas.append(strata)
        strata_stat = StrataStats(stratas=all_stratas, prob=_prob)
        full_strata_stats.append(strata_stat)
    return full_strata_stats


def parse_file_simpler(file_content: str) -> List[StrataStats]:
    """File Format: Header: (feature_name1.Min, feature_name1.Max),.... ,last column is the probability
    If feature is binary no ".Min" or ".Max" suffix.
    Each row after this header will have data.
    """
    data = pd.read_csv(StringIO(file_content))
    if len(data) == 0:
        raise Exception("complex format? - 1 line")
    col_names = list(data.columns)
    col_names[-1] = "Probability"
    data.columns = col_names
    # Check col names:
    feat_info = {}

    for col_idx, col in enumerate(col_names[:-1]):
        if col.lower().endswith(".min") or col.lower().endswith(".max"):
            tokens = col.split(".")
            range_act = tokens[-1].lower()
            range_idx = 0
            if range_act == "max":
                range_idx = 1
            feat_name = ".".join(tokens[:-1])
            if feat_name not in feat_info:
                feat_info[feat_name] = [None, None]
            feat_info[feat_name][range_idx] = col_idx
        else:  # No range, 1 value
            feat_name = col
            if feat_name in feat_info:
                raise Exception(f"Error found {feat_name} more then once")
            feat_info[feat_name] = col_idx
    # Check
    for feat_name, feat_vals in feat_info.items():
        if type(feat_vals) == int:
            continue
        else:
            if feat_vals[0] is None:
                raise Exception(
                    f"Error, feature {feat_name} lacks min range columns, .min suffix"
                )
            if feat_vals[1] is None:
                raise Exception(
                    f"Error, feature {feat_name} lacks max range columns, .max suffix"
                )
    # Now we have map for each feature to it's columns.
    full_res = []
    for row_num in range(len(data)):
        row = data.iloc[row_num]
        startas = []
        for feat_name, feat_vals in feat_info.items():
            if type(feat_vals) == int:
                set_value = row[col_names[feat_vals]]
                if not (set_value) or (
                    type(set_value) != str and math.isnan(set_value)
                ):
                    continue
                if feat_name.lower() == "gender" or feat_name.lower() == "sex":
                    if set_value.lower() == "male" or set_value.lower() == "m":
                        set_value = "1"
                    elif set_value.lower() == "female" or set_value.lower() == "f":
                        set_value = "2"
                    else:
                        raise Exception(f"Unsupport value {set_value} for {feat_name}")
                strata = StrateCategory(
                    feature_name=feat_name, categoty_value=set_value
                )
                startas.append(strata)
            else:
                min_col_ids, max_col_idx = feat_vals
                min_col_name = col_names[min_col_ids]
                max_col_name = col_names[max_col_idx]
                strata = StrataRange(
                    feature_name=feat_name,
                    min_range=row[min_col_name],
                    max_range=row[max_col_name],
                )
                startas.append(strata)
        current_strata_data = StrataStats(stratas=startas, prob=row["Probability"])
        full_res.append(current_strata_data)
    return full_res


def parse_file_content_non_dist(file_content: str) -> List[StrataStats]:
    try:
        full_res = parse_file_simpler(file_content)
    except:
        logger.error(traceback.format_exc())
        logger.info("Using Complex format")
        full_res = parse_file_complex(file_content)
    return full_res


def parse_file_content(file_content: str, min_obs: int = 1000) -> List[StrataStats]:
    EPSILON_ERR = 1e-4
    full_res = parse_file_content_non_dist(file_content)
    logger.info(full_res)
    # Check sum to 1 or all integers > 1, sum over min_obs
    all_integers = len(
        list(filter(lambda x: abs(int(x.prob) - x.prob) < EPSILON_ERR, full_res))
    )
    tot_prob = sum(map(lambda x: x.prob, full_res))
    all_integers_condition = all_integers == len(full_res)
    is_dist = abs(tot_prob - 100) <= EPSILON_ERR or abs(tot_prob - 1) <= EPSILON_ERR
    if all_integers_condition and not (is_dist):
        if tot_prob < min_obs:
            raise ErrorFewObs(
                f"Error - input stratas has too few observations, less than {min_obs}, got {tot_prob}",
                tot_prob,
            )
        else:
            logger.info("Normalizing to dist...")
            # All ok - just normalize:
            for i in range(len(full_res)):
                full_res[i].prob = 100 * (full_res[i].prob / tot_prob)
            tot_prob = sum(map(lambda x: x.prob, full_res))

    if abs(tot_prob - 100) > EPSILON_ERR and abs(tot_prob - 1) > EPSILON_ERR:
        raise ErrorNotDistribution(
            f"Error - input stratas is not distribution, reached {tot_prob}", tot_prob
        )

    return full_res
