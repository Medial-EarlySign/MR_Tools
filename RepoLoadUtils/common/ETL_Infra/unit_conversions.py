#!/usr/bin/env python
# coding: utf-8
import os
import sys
import argparse
import datetime as dt
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from .env import *
from .define_signals import SignalInfo, load_signals_map


def read_signals_defs() -> Dict[str, SignalInfo]:
    """
    :meta private:
    """
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return load_signals_map(FULL_SIGNALS_TYPES, codedir)


def get_stats(fullDFi, inFile=None, signals_def=None, samples_per_signal=5):
    """
    :meta private:
    """
    fullDF = fullDFi[fullDFi["unit"].notnull()].reset_index()
    if len(fullDF) == 0:
        return None
    freqSignal = fullDF["signal"].value_counts().reset_index()
    freqUnit = fullDF.value_counts(subset=["signal", "unit"], dropna=False)

    if "index" in freqSignal.columns:
        freqSignal = freqSignal.rename(columns={"signal": "count", "index": "signal"})
    inData = freqSignal.merge(
        freqUnit.to_frame()
        .reset_index()
        .rename(columns={0: "unitCount", "count": "unitCount"}),
        on="signal",
        how="left",
    ).sort_values(by=["count", "signal", "unitCount"], ascending=False)
    inData.loc[inData["unit"].isnull(), "unit"] = ""
    inData["unit"] = inData["unit"].astype(
        str
    )  # in case they are all nulls  and read as floats
    if inFile is None or not (os.path.exists(inFile)):
        inTable = pd.DataFrame(
            columns=[
                "signal",
                "unit",
                "to_signal",
                "to_unit",
                "multiple_by",
                "additive_b0",
                "value",
            ]
        )
    else:
        inTable = pd.read_csv(
            inFile, sep="\t", converters={"signal": str, "unit": str}
        ).rename(columns={"value_0": "value"})
        inTable = inTable[inTable["signal"] != ""].reset_index(
            drop=True
        )  # Remvoe empty lines
        if inTable.empty:
            inTable = pd.DataFrame(
                columns=[
                    "signal",
                    "unit",
                    "to_signal",
                    "to_unit",
                    "multiple_by",
                    "additive_b0",
                    "value",
                ]
            )

    inTable = inTable[inTable["signal"].notnull()].reset_index(drop=True)
    inTable["unit"] = inTable["unit"].astype(str)
    outTable = inData[["signal", "count", "unit", "unitCount"]].merge(
        inTable[
            [
                "signal",
                "unit",
                "to_signal",
                "to_unit",
                "multiple_by",
                "additive_b0",
                "value",
            ]
        ],
        how="outer",
        on=["signal", "unit"],
    )
    outTable = outTable.rename(columns={0: "unitCount"})
    if signals_def is not None:  # Fetch Target unit from known signal
        sig_names = list(map(lambda x: x[1].name, signals_def.items()))
        unit_vec = list(
            map(
                lambda x: x[1].units[0] if (len(x[1].units) > 0) else "",
                signals_def.items(),
            )
        )
        df_unit = pd.DataFrame({"to_signal_f": sig_names, "unit_official": unit_vec})
        df_unit["to_signal_f"] = df_unit["to_signal_f"].astype(str)
        outTable["to_signal_f"] = outTable["to_signal"]
        filter_cond = (outTable["to_signal_f"].isnull()) | (
            outTable["to_signal_f"] == ""
        )
        outTable.loc[filter_cond, "to_signal_f"] = outTable.loc[filter_cond, "signal"]
        outTable.loc[outTable["to_signal_f"].isnull(), "to_signal_f"] = ""
        outTable["to_signal_f"] = outTable["to_signal_f"].astype(str)
        outTable = outTable.merge(df_unit, how="left", on=["to_signal_f"])
        filter_cond = (outTable["unit_official"].notnull()) & (
            outTable["unit_official"] != ""
        )
        outTable.loc[filter_cond, "to_unit"] = outTable.loc[
            filter_cond, "unit_official"
        ]
        outTable = outTable.drop(columns=["unit_official", "to_signal_f"])

    samples = (
        fullDF[["signal", "unit", "value_0"]]
        .groupby(["signal", "unit"])
        .sample(n=samples_per_signal, replace=True)
    )
    outTableSample = (
        outTable.merge(samples, on=["signal", "unit"], how="left")
        .groupby(["signal", "unit"], dropna=False)
        .aggregate(lambda tdf: tdf.tolist())
    )
    # Remove Empty "value 0"
    if "value" in outTableSample.columns:  # Try fix nan
        outTableSample.loc[
            outTableSample["value_0"].apply(lambda x: np.isnan(x).all()), "value_0"
        ] = outTableSample.loc[
            outTableSample["value_0"].apply(lambda x: np.isnan(x).all()), "value"
        ].apply(
            lambda x: eval(x[0])
        )
        outTableSample = outTableSample.drop(columns=["value"])
        outTable = outTable.drop(columns=["value"])
    outTableSample1 = outTable.merge(
        outTableSample["value_0"], on=["signal", "unit"], how="left"
    )

    return outTableSample1


def process_unit_conversion(
    fullDF: pd.DataFrame, outFile: str, signals_def=None, samples_per_signal: int = 5
) -> None:
    """
    :meta private:
    """
    print("Start analyzing signal+units...", flush=True)
    outTable = get_stats(fullDF, outFile, signals_def, samples_per_signal)
    if outTable is not None:
        outTable.to_csv(outFile, index=False, sep="\t")
        print(f">>>>> outTable written to {outFile} <<<<<<", flush=True)


def fix_units(fullDF: pd.DataFrame, inFile: str) -> pd.DataFrame:
    """
    :meta private:
    """
    if not (os.path.exists(inFile)):
        raise NameError(
            "Please call process_unit_conversion, or generate config file\n%s"
            % (inFile)
        )
    print("Start fixing signal+units...", flush=True)
    inTable = pd.read_csv(inFile, sep="\t", converters={"signal": str, "unit": str})
    # Use signal if tp_signal is empty (keep same name) - if you want you can filter yourself later
    empty_map_cond = (inTable["to_signal"].isnull()) | (inTable["to_signal"] == "")
    inTable["mapped"] = 1
    inTable.loc[empty_map_cond, "to_signal"] = inTable.loc[empty_map_cond, "signal"]
    inTable.loc[empty_map_cond, "mapped"] = 0
    df = fullDF
    inTable["unit"] = inTable["unit"].astype(str)
    numConvert = df.merge(
        inTable[
            ["signal", "unit", "to_signal", "multiple_by", "additive_b0", "mapped"]
        ],
        how="left",
        on=["signal", "unit"],
    )

    no_map = numConvert[numConvert["to_signal"].isnull()].reset_index(drop=True)
    if len(no_map) > 0:
        print(f"WARN :: There are {len(no_map)} records without mapping")
        print(no_map.head(10))
        print(
            "Those are the common signal+unit unmapped:\n",
            no_map[["signal", "unit"]].value_counts().reset_index(),
        )
        raise NameError("No mapping found for some of the input signals")

    # Convert
    numConvert.multiple_by = pd.to_numeric(numConvert.multiple_by, errors="coerce")
    numConvert.additive_b0 = pd.to_numeric(numConvert.additive_b0, errors="coerce")
    numConvert.loc[numConvert.multiple_by.isna(), "multiple_by"] = 1  # Default 1
    numConvert.loc[numConvert.additive_b0.isna(), "additive_b0"] = 0  # Default 0
    numConvert["value_00"] = (
        numConvert["value_0"] * numConvert.multiple_by + numConvert.additive_b0
    )
    numConvert = numConvert.rename(
        columns={
            "value_0": "value_0.original",
            "value_00": "value_0",
            "signal": "signal.original",
            "to_signal": "signal",
        }
    ).drop(columns=["multiple_by", "additive_b0", "value_0.original"])
    return numConvert


class SuggestionResult:
    """
    A class that holds unit suggestion linear transformation
    """

    bias: float
    factor: float
    distance: float
    opposite_transformation: bool
    description: str
    target_unit: str
    group_size: int
    current_median: float
    expected_median: float

    def __init__(
        self,
        direction: bool,
        _bias: float,
        _factor: float,
        _distance: float,
        _desc: str,
        _target: str,
        _grp_size: int,
        _current_median: float,
        _expected_median: float,
    ):
        self.bias = _bias
        self.factor = _factor
        self.distance = _distance
        self.opposite_transformation = direction
        self.description = _desc
        self.target_unit = _target
        self.group_size = _grp_size
        self.current_median = _current_median
        self.expected_median = _expected_median

    def __repr__(self):
        ss = (
            f"Size: {self.group_size}, bias: {self.bias}, factor:{self.factor}, distance_from_target_median: {self.distance}, target_unit:{self.target_unit}, guested_unit: {self.description}"
            f", current_fixed: {self.current_median}, expected: {self.expected_median}"
        )
        if self.opposite_transformation:
            return ss + f", reversed_transform!"
        else:
            return ss


def find_best_unit_suggestion(
    df: pd.DataFrame,
    allow_op: bool = False,
    diff_threshold_percentage: float = 0.5,
    diff_threshold_ratio: float = 3,
    min_grp_size: int = 500,
) -> Dict[Tuple[str, str] | str, List[SuggestionResult]]:
    """
    Function that recieves dataframe with multiple signals, units and breaks down results by each group of signal,unit to rank of most suitable
    units linear transformation [bias + factor] for this group. IT will also return the distance from expected median value of target unit

    :param df: DataFrame input with signal, value_0 column
    :param allow_op: If true will allow to test also the opposite transformation of the linear suggestion.
    :param diff_threshold_percentage: How much in percentage [0-1] difference from best match continue to suggest other options
    :param min_grp_size: Group size that below this value we will ignore
    """
    all_sigs_config = read_signals_defs()
    current_dir = os.path.dirname(__file__)
    signal_value_stats_df = pd.read_csv(
        os.path.join(current_dir, "rep_signals", "signals_prctile.cfg"), sep="\t"
    )
    unit_suggestion_cfg = pd.read_csv(
        os.path.join(current_dir, "rep_signals", "unit_suggestions.cfg"),
        sep="\t",
        names=["signal", "bias", "factor", "description"],
    )

    subset = ["signal"]
    if "unit" in df.columns:
        subset.append("unit")
    res_full = dict()
    skip_cols = set(["pid", "signal"])
    additional_cols = list(
        filter(
            lambda x: x not in skip_cols
            and not (x.startswith("time_"))
            and not (x.startswith("value_")),
            df.columns,
        )
    )
    first_tm = True
    grp_name = "GROUP_COLS"
    for col in additional_cols:
        if first_tm:
            df[grp_name] = f"{col}:" + df[col].astype(str)
        else:
            df[grp_name] = df[grp_name] + f"|{col}:" + df[col].astype(str)
        first_tm = False
    if len(additional_cols) > 0:
        subset = ["signal", grp_name]
    for group_key, group_df in df.groupby(by=subset):
        grp_size = len(group_df)
        if grp_size < min_grp_size:
            print(f"Skip {group_key} too small {grp_size}")
            continue
        res_full[group_key] = find_best_unit_suggestion_to_group(
            group_df,
            None,
            allow_op,
            diff_threshold_percentage,
            diff_threshold_ratio,
            signal_value_stats_df,
            unit_suggestion_cfg,
            all_sigs_config,
            group_key,
        )
    return res_full


def try_get_quantile(
    signal_value_stats_df: pd.DataFrame, prc: float, signal_name: str
) -> float | None:
    signal_value_stats_df_ = signal_value_stats_df[
        signal_value_stats_df["q"] == prc
    ].reset_index(drop=True)
    if len(signal_value_stats_df_) == 0:
        print(
            f"Warning, no reference for signal {signal_name} to suggest unit transformation",
            flush=True,
        )
        return None
    target_median = signal_value_stats_df_["reference"].iloc[0]
    return target_median


def find_best_unit_suggestion_to_group(
    df: pd.DataFrame,
    optional_factors: List[Tuple[float, float, str]] | None = None,
    allow_op: bool = False,
    diff_threshold_percentage: float = 0.5,
    diff_threshold_ratio: float = 3,
    signal_value_stats_df: pd.DataFrame | None = None,
    unit_suggestion_cfg: pd.DataFrame | None = None,
    signal_info: Dict[str, SignalInfo] | None = None,
    group_name: tuple[str, str] | None = None,
) -> List[SuggestionResult] | None:
    """
    Function that recieve dataframe with raw value and optional tranformation Tuple [bias, factor] and chooses best

    :param df: DataFrame input with signal, value_0 column
    :param optional_factors: List of options for linear tranformations - Each tuple is based on [bias, factor]
    :param allow_op: If true will allow to test also the opposite transformation of the linear suggestion.
    :param diff_threshold_percentage: How much in percentage [0-1] difference from best match continue to suggest other options
    :param signal_value_stats_df: A dataframe with signal and percentile stats - median value. If not given will read again from resources directroy.
    :param unit_suggestion_cfg: A dataframe with signal unit suggestion transormations for each signal,unit. If not given will read again from resources directroy.
    :param signal_info: An object that holds signals information, what is the target unit. If None, will read from resource directory

    """
    current_dir = os.path.dirname(__file__)
    if signal_value_stats_df is None:
        signal_value_stats_df = pd.read_csv(
            os.path.join(current_dir, "rep_signals", "signals_prctile.cfg"), sep="\t"
        )
    signal_name = df["signal"].iloc[0]
    if optional_factors is None or len(optional_factors) == 0:
        # print(f'Reading suggestion from config file',flush=True)
        if unit_suggestion_cfg is None:
            unit_suggestion_cfg = pd.read_csv(
                os.path.join(current_dir, "rep_signals", "unit_suggestions.cfg"),
                sep="\t",
                names=["signal", "bias", "factor", "description"],
            )
        unit_suggestion_cfg = unit_suggestion_cfg[
            unit_suggestion_cfg["signal"] == signal_name
        ].reset_index(drop=True)
        if len(unit_suggestion_cfg) == 0: # type: ignore
            print(
                f"Warning, no options, optional_factors is empty for {signal_name}",
                flush=True,
            )
            return None
        optional_factors = list(
            unit_suggestion_cfg[["bias", "factor", "description"]].values # type: ignore
        )

    grp_size = len(df)
    prc = 0.5
    signal_value_stats_df = (
        signal_value_stats_df[signal_value_stats_df["signal"] == signal_name]
        .reset_index(drop=True)[["q", "value_0"]]
        .rename(columns={"value_0": "reference"})
    )
    target_median = try_get_quantile(signal_value_stats_df, prc, signal_name) # type: ignore
    if target_median is None or target_median == 0:
        prc = 0.9
        target_median = try_get_quantile(signal_value_stats_df, prc, signal_name) # type: ignore

    if target_median is None or target_median == 0:
        print(f"WARN: signal {signal_name} has quantile {target_median} - skipping")
        return None
    if prc != 0.5:
        print(f"INFO ::Comparing quantile {prc} for signal {signal_name}")
    current_median = df["value_0"].quantile(q=prc)
    if current_median == 0:
        print(
            f"Current quantile {prc} for {signal_name} is 0 - skipping unit suggestion"
        )
        return None

    # Iterate over all options and find best "match", closest. Compare if there are more then one good option:
    opt_rank = (
        []
    )  # tuple of index+1 in optional_factors, distance or -(index+1) for opposite
    for idx, tp in enumerate(optional_factors):
        idx += 1
        bias, factor, desription = tp
        if bias == 0 and factor == 1:
            continue  # I already have this option
        fixed_median = factor * current_median + bias
        opt_distance = abs(target_median - fixed_median)
        opt_rank.append([idx, opt_distance, fixed_median])
        if allow_op:
            # Let's check opposite transformation:
            fixed_median = (current_median - bias) / factor
            opt_distance = abs(target_median - fixed_median)
            opt_rank.append([-idx, opt_distance, fixed_median])
    # Last Option - treat it as [0,1] - means no bias, no factor so keep as is.
    opt_distance = abs(current_median - target_median)
    opt_rank.append([None, opt_distance, current_median])
    # Sort by distance
    opt_rank = sorted(opt_rank, key=lambda x: x[1])
    # Let's choose best option and see if the next one is far enough behind
    # Filter diff_threshold_ratio from opt_rank:
    if target_median > 0:
        opt_rank = list(
            filter(
                lambda x: (
                    max(x[2] / target_median, target_median / x[2])
                    <= diff_threshold_ratio
                    if x[2] > 0
                    else False
                ),
                opt_rank,
            )
        )

    if len(opt_rank) == 0:
        raise Exception(
            f"No suitable unit found for signal {signal_name} - {group_name} - all options does not fit. expected median {target_median}, current median: {current_median}"
        )

    _, best_option_distance, _ = opt_rank[0]
    till_idx = 0
    while best_option_distance == 0 and till_idx + 1 < len(opt_rank):
        till_idx += 1
        _, best_option_distance, _ = opt_rank[till_idx]
        best_option_distance = min(
            best_option_distance, 5
        )  # Since previous was 0, don't allow more than 5

    for idx, opt_tp in enumerate(opt_rank[till_idx:]):
        _, opt_dist, _ = opt_tp
        if best_option_distance == 0:
            break
        if opt_dist / best_option_distance - 1 > diff_threshold_percentage:
            break
        till_idx += 1
    opt_rank = opt_rank[:till_idx]
    # Now return opt_rank in this format: [direction:bool, bias, factor, distance]
    res = []
    target_unit = ""
    if signal_info is not None and signal_name in signal_info:
        si = signal_info[signal_name]
        target_unit = ",".join(si.units)
    for idx, distance, fixed_median in opt_rank:
        bias = 0
        factor = 1
        description = ""
        if idx is not None:
            access_idx = abs(idx) - 1
            bias = optional_factors[access_idx][0]
            factor = optional_factors[access_idx][1]
            description = optional_factors[access_idx][2]
            if idx < 0:
                description += " Reversed"
        opt_res = SuggestionResult(
            idx is not None and idx < 0,
            bias,
            factor,
            distance,
            description,
            target_unit,
            grp_size,
            fixed_median,
            target_median,
        )
        res.append(opt_res)

    return res


if __name__ == "__main__":
    # get parameters
    parser = argparse.ArgumentParser(
        description="Prepare signals for load. Convert units"
    )
    parser.add_argument(
        "--raw_pkl", required=True, help="raw pkl file 'id signal date value unit'"
    )
    parser.add_argument("--out_table", required=True, help="updated conversion table")
    parser.add_argument(
        "--samples_per_signal",
        help="number of samples presented from each signal unit combination",
        default=5,
    )
    args = parser.parse_args()

    fullDF = pd.read_pickle(args.raw_pkl)
    fullDF = fullDF[fullDF.value.notna()]
    process_unit_conversion(
        fullDF, args.out_table, samples_per_signal=args.samples_per_signal
    )
