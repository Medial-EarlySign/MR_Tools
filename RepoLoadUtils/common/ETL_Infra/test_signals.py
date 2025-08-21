import pandas as pd
import os, re, sys, importlib.util, traceback, contextlib
from .plot_graph import plot_graph, get_plotly_js
import numpy as np
from datetime import datetime
from .logger import Logger


def test_date_column(df, col_name, signal_name, batch_num, workdir, print_error):
    batch_info = ""
    batch_info_f = ""
    if batch_num is not None:
        batch_info = f"(batch {batch_num})"
        batch_info_f = f".batch_{batch_num}"
    # Test format and convert to YYYYMMDD. TODO in the future add support for ICU where time is in minutes
    df = fix_date_col(df, col_name, signal_name, batch_num, print_error)
    if type(df) != pd.DataFrame:
        return df
    df_test = df[[col_name]].copy()
    df_test["_MES__YEAR__"] = df_test[col_name] // 10000
    dist_by_years = df_test["_MES__YEAR__"].value_counts().reset_index()
    if "index" in dist_by_years.columns:
        dist_by_years = dist_by_years.rename(
            columns={"index": "Year", "_MES__YEAR__": "Count"}
        )
    else:
        dist_by_years = dist_by_years.rename(columns={"_MES__YEAR__": "Year"})
    dist_by_years = dist_by_years.sort_values("Year").reset_index(drop=True)
    sz = len(df_test)
    sl = sorted(df_test["_MES__YEAR__"].values)
    # Take 1,99 percentiles:
    if sl[int(0.01 * sz)] <= 1900 or sl[int(0.01 * sz)] >= 2100:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 1%% year prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.01 * sz)]),
                flush=True,
            )
        return False
    if sl[int(0.99 * sz)] <= 1900 or sl[int(0.99 * sz)] >= 2100:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 99%% year prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.99 * sz)]),
                flush=True,
            )
        return False

    # Test month:
    df_test["_MES__MONTH__"] = (df_test[col_name] // 100) % 100
    dist_by_months = df_test["_MES__MONTH__"].value_counts().reset_index()
    if "index" in dist_by_months.columns:
        dist_by_months = dist_by_months.rename(
            columns={"index": "Month", "_MES__MONTH__": "Count"}
        )
    else:
        dist_by_months = dist_by_months.rename(columns={"_MES__MONTH__": "Month"})
    dist_by_months = dist_by_months.sort_values("Month").reset_index(drop=True)
    sl = sorted(df_test["_MES__MONTH__"].values)

    if sl[int(0.01 * sz)] < 1 or sl[int(0.01 * sz)] > 12:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 1%% month prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.01 * sz)]),
                flush=True,
            )
        return False
    if sl[int(0.99 * sz)] < 1 or sl[int(0.99 * sz)] > 12:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 99%% month prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.99 * sz)]),
                flush=True,
            )
        return False

    # Test day:
    df_test["_MES__DAY__"] = df_test[col_name] % 100
    dist_by_days = df_test["_MES__DAY__"].value_counts().reset_index()
    if "index" in dist_by_days.columns:
        dist_by_days = dist_by_days.rename(
            columns={"index": "Day", "_MES__DAY__": "Count"}
        )
    else:
        dist_by_days = dist_by_days.rename(columns={"_MES__DAY__": "Day"})
    dist_by_days = dist_by_days.sort_values("Day").reset_index(drop=True)
    sl = sorted(df_test["_MES__DAY__"].values)

    if sl[int(0.01 * sz)] < 1 or sl[int(0.01 * sz)] > 31:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 1%% day prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.01 * sz)]),
                flush=True,
            )
        return False
    if sl[int(0.99 * sz)] < 1 or sl[int(0.99 * sz)] > 31:
        if print_error:
            print(
                "ERROR :: Bad date column %s in signal %s%s. The date range is weird, 99%% day prctile is %d"
                % (col_name, signal_name, batch_info, sl[int(0.99 * sz)]),
                flush=True,
            )
        return False

    # Store this graph in outputs: dist_by_years, dist_by_months, dist_by_days
    outputs_dir = os.path.join(workdir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    sig_dir = os.path.join(outputs_dir, signal_name)
    os.makedirs(sig_dir, exist_ok=True)
    sig_dir_f = sig_dir
    js_path = os.path.join(
        "..", "js", "plotly.js"
    )  # Create relative path that we can copy
    if batch_num is not None:
        sig_dir_f = os.path.join(sig_dir, "batches")
        os.makedirs(sig_dir_f, exist_ok=True)
        js_path = os.path.join(
            "..", "..", "js", "plotly.js"
        )  # Create relative path that we can copy

    plot_graph(
        dist_by_years,
        os.path.join(sig_dir_f, "%s%s_Year.html" % (col_name, batch_info_f)),
        "%s %s by years" % (signal_name, col_name),
        javascript_path=js_path,
    )
    plot_graph(
        dist_by_months,
        os.path.join(sig_dir_f, "%s%s_Month.html" % (col_name, batch_info_f)),
        "%s %s by months" % (signal_name, col_name),
        javascript_path=js_path,
    )
    plot_graph(
        dist_by_days,
        os.path.join(sig_dir_f, "%s%s_Day.html" % (col_name, batch_info_f)),
        "%s %s by days" % (signal_name, col_name),
        javascript_path=js_path,
    )

    # Test date format:
    new_col = pd.to_datetime(df_test[col_name], format="%Y%m%d", errors="coerce")
    bad_dates = df_test[new_col.isnull()].reset_index(drop=True)
    if len(bad_dates) > 0:
        print(f"Has bad dates in dataframe column {col_name} for signal {signal_name}")
        print(f"Histogram: {bad_dates[col_name].value_counts()}")

    # Test years, months, days

    return True


def test_categorical_column(df, col_name, signal_name, batch_num, workdir, print_error):
    batch_info = ""
    batch_info_f = ""
    if batch_num is not None:
        batch_info = f"(batch {batch_num})"
        batch_info_f = f".batch_{batch_num}"

    # strip whitespaces
    non_values_cnt = len(df[df[col_name].isna()])
    if non_values_cnt > 0:
        print(
            f"ERROR - There are {non_values_cnt} None/NA values in {col_name} under {signal_name}.\nPlease fix your code that process this signal"
        )
        return False
    df[col_name] = df[col_name].astype(str).map(lambda x: x.strip())

    df_test = df[[col_name]].copy()
    df_test[col_name] = df_test[col_name].astype(str)
    df_test.loc[df_test[col_name].notnull(), col_name] = df_test.loc[
        df_test[col_name].notnull(), col_name
    ].map(lambda x: x.strip())
    null_vals_cnt = len(
        df_test[(df_test[col_name].isnull()) | (df_test[col_name] == "")]
    )
    if null_vals_cnt > 0:
        if print_error:
            print(
                "ERROR :: signal %s%s has empty, null values in col %s - %d(%2.1f%%)"
                % (
                    signal_name,
                    batch_info,
                    col_name,
                    null_vals_cnt,
                    100 * null_vals_cnt / len(df_test),
                ),
                flush=True,
            )
        else:
            print(
                "WARN :: signal %s%s has empty, null values in col %s - %d(%2.1f%%). Will try to recover by further processing"
                % (
                    signal_name,
                    batch_info,
                    col_name,
                    null_vals_cnt,
                    100 * null_vals_cnt / len(df_test),
                ),
                flush=True,
            )
        return False
    # find ilegal characters:
    ilegal_reg = re.compile(r'[, "\'\t;]')
    df_test["MES__ILEGAL_CNT"] = df_test[col_name].map(
        lambda x: len(ilegal_reg.findall(x)) != 0
    )
    ilegal_count = df_test["MES__ILEGAL_CNT"].sum()
    if ilegal_count > 0:
        if print_error:
            print(
                "ERROR :: signal %s%s has %d ilegal chars in col %s"
                % (signal_name, batch_info, ilegal_count, col_name),
                flush=True,
            )
            print(
                df[df_test["MES__ILEGAL_CNT"] > 0][col_name]
                .value_counts(dropna=False)
                .reset_index(),
                flush=True,
            )
        else:
            print(
                "WARN :: signal %s%s has %d ilegal chars in col %s. Will try to recover by further processing"
                % (signal_name, batch_info, ilegal_count, col_name),
                flush=True,
            )
            print(
                df[df_test["MES__ILEGAL_CNT"] > 0][col_name]
                .value_counts(dropna=False)
                .reset_index(),
                flush=True,
            )
        return False

    # Plot distribution:
    cnt_dist = df_test[col_name].value_counts().reset_index()
    if "index" in cnt_dist.columns:
        cnt_dist = cnt_dist.rename(
            columns={col_name: "count", "index": col_name, "count": col_name}
        )
    cnt_dist = cnt_dist.sort_values("count", ascending=False).reset_index(drop=True)

    # store in outputs
    outputs_dir = os.path.join(workdir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    sig_dir = os.path.join(outputs_dir, signal_name)
    os.makedirs(sig_dir, exist_ok=True)
    sig_dir_f = sig_dir
    js_path = os.path.join(
        "..", "js", "plotly.js"
    )  # Create relative path that we can copy
    if batch_num is not None:
        sig_dir_f = os.path.join(sig_dir, "batches")
        os.makedirs(sig_dir_f, exist_ok=True)
        js_path = os.path.join("..", "..", "js", "plotly.js")
    plot_graph(
        cnt_dist,
        os.path.join(sig_dir_f, "%s%s_histogram.html" % (col_name, batch_info_f)),
        "%s %s histogram" % (signal_name, col_name),
        javascript_path=js_path,
    )

    return True


def test_numeric_column(df, col_name, signal_name, batch_num, workdir, print_error):
    batch_info = ""
    batch_info_f = ""
    if batch_num is not None:
        batch_info = f"(batch {batch_num})"
        batch_info_f = f".batch_{batch_num}"
    # Test column is numeric, not null:
    df_test = df[[col_name]].copy()
    df_test[col_name] = pd.to_numeric(df_test[col_name], errors="coerce")
    null_vals_cnt = len(df_test[df_test[col_name].isnull()])
    if null_vals_cnt > 0:
        if print_error:
            print(
                "ERROR :: signal %s%s has empty, null values in col %s - %d (%2.1f%%)"
                % (
                    signal_name,
                    batch_info,
                    col_name,
                    null_vals_cnt,
                    100 * null_vals_cnt / len(df_test),
                ),
                flush=True,
            )
        else:
            print(
                "WARN :: signal %s%s has empty, null values in col %s - %d (%2.1f%%). will try to recover by further processings"
                % (
                    signal_name,
                    batch_info,
                    col_name,
                    null_vals_cnt,
                    100 * null_vals_cnt / len(df_test),
                ),
                flush=True,
            )
        return False
    else:
        df[col_name] = (
            pd.to_numeric(df_test[col_name], errors="coerce") * 1
        )  # To handle "booleans"

    # Plot distribution, compare to known dist:
    cnt_dist = df_test[col_name].value_counts().reset_index()
    if "index" in cnt_dist.columns:
        cnt_dist = cnt_dist.rename(
            columns={col_name: "Count", "index": col_name, "count": col_name}
        )
    cnt_dist = cnt_dist.sort_values(col_name).reset_index(drop=True)
    # store in outputs
    outputs_dir = os.path.join(workdir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    sig_dir = os.path.join(outputs_dir, signal_name)
    os.makedirs(sig_dir, exist_ok=True)
    sig_dir_f = sig_dir
    js_path = os.path.join(
        "..", "js", "plotly.js"
    )  # Create relative path that we can copy
    if batch_num is not None:
        sig_dir_f = os.path.join(sig_dir, "batches")
        os.makedirs(sig_dir_f, exist_ok=True)
        js_path = os.path.join(
            "..", "..", "js", "plotly.js"
        )  # Create relative path that we can copy
    plot_graph(
        cnt_dist,
        os.path.join(sig_dir_f, "%s%s_histogram.html" % (col_name, batch_info_f)),
        "%s %s histogram" % (signal_name, col_name),
        javascript_path=js_path,
    )

    return True


def _setup_plotly_js(workdir):
    js_path = os.path.join(workdir, "outputs", "js")
    os.makedirs(js_path, exist_ok=True)
    file_path = os.path.join(js_path, "plotly.js")
    if os.path.exists(file_path):
        return
    # Create file
    js = get_plotly_js()
    fw = open(file_path, "w")
    fw.write(js)
    fw.close()


def fix_date_col(df, col_name, signal_name, batch_num, print_error=False):
    batch_info = ""
    if batch_num is not None:
        batch_info = f"(batch {batch_num})"
    if df[col_name].dtype > np.int64:
        # try fix:
        try:
            if print_error:
                print(
                    "WARN :: Bad date column %s in signal %s%s. not integer, got %s. try to convert"
                    % (col_name, signal_name, batch_info, df[col_name].dtype),
                    flush=True,
                )
            df[col_name] = pd.to_numeric(
                df[col_name].astype(str).map(lambda x: x.replace("-", ""))
            ).astype(int)
        except:
            bad_dates = df[
                pd.to_numeric(
                    df[col_name].astype(str).map(lambda x: x.replace("-", "")),
                    errors="coerce",
                ).isna()
            ]
            if print_error:
                print(
                    "ERROR :: Bad date column %s in signal %s%s. not integer, got %s"
                    % (col_name, signal_name, batch_info, df[col_name].dtype),
                    flush=True,
                )
                print(bad_dates[col_name].value_counts(dropna=False), flush=True)
            else:
                print(
                    "WARN :: Bad date column %s in signal %s%s. not integer, got %s - will try to recover by processing data"
                    % (col_name, signal_name, batch_info, df[col_name].dtype),
                    flush=True,
                )
                print(bad_dates[col_name].value_counts(dropna=False), flush=True)
            return False
    return df


def minimal_test_df(
    df: pd.DataFrame,
    signal_type,
    sig_types,
    batch_num,
    workdir,
    codedir,
    print_error=True,
):
    outputs_dir = os.path.join(workdir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    test_logger_file = os.path.join(outputs_dir, f"tests.{signal_type}.log")
    sys.stdout = Logger(test_logger_file)
    # Test df has "signal" column and pid column"
    if "pid" not in df.columns:
        print(
            'ERROR :: Failed %s - dataframe has no "pid" column' % (signal_type),
            flush=True,
        )
        sys.stdout = sys.__stdout__
        return df, False
    if "signal" not in df.columns:
        print(
            'ERROR :: Failed %s - dataframe has no "signal" column' % (signal_type),
            flush=True,
        )
        sys.stdout = sys.__stdout__
        return df, False
    na_pids = sum(df["pid"].isna())
    if na_pids > 0:
        raise NameError(
            f'There are {na_pids} None values in "pid" column for "{signal_type}"'
        )
    all_sigs = set(df["signal"].values)
    all_signals_ok = True
    res_additional = True
    for sig_name in all_sigs:
        if sig_name not in sig_types:
            if sig_name is not None:
                print(
                    "ERROR :: signal %s is not defined in signals [%s], please define it, for more tests"
                    % (sig_name, signal_type),
                    flush=True,
                )
            sys.stdout = sys.__stdout__
            return df, False
        if len(all_sigs) > 0:
            df_i = df[df["signal"] == sig_name].reset_index(drop=True).copy()
        else:
            df_i = df  # no need to copy

        si = sig_types[sig_name]
        t_ch = si.t_ch
        v_ch = si.v_ch
        categ_numeric_cols = si.v_categ
        units_m = si.units
        # print('signal %s, has %d, %d channels %s'%(signal_type, len(t_ch), len(v_ch), categ_numeric_cols))
        # Lets's check time channels:
        first_time_col = None
        for i in range(len(t_ch)):
            col_name = "time_%d" % (i)
            if not (col_name in df.columns):
                col_name = "date_%d" % (i)
                if not (col_name in df.columns):
                    if print_error:
                        print(
                            'ERROR :: Can\'t find time channel column %d in signal %s, column should be called "time_%d"'
                            % (i, sig_name, i),
                            flush=True,
                        )
                    sys.stdout = sys.__stdout__
                    return df, False
            if first_time_col is None:
                first_time_col = col_name
            df_i = fix_date_col(df_i, col_name, sig_name, batch_num, print_error)
            if type(df_i) != pd.DataFrame:
                if print_error:
                    print(
                        'ERROR :: Can\'t convert date column %d in signal %s, column should be called "time_%d"'
                        % (i, sig_name, i),
                        flush=True,
                    )
                sys.stdout = sys.__stdout__
                return df, False

        # Test numeric:
        for i in range(len(v_ch)):
            col_name = "value_%d" % (i)
            if not (col_name in df.columns):
                col_name = "val_%d" % (i)
                if not (col_name in df.columns):
                    if print_error:
                        print(
                            'ERROR :: Can\'t find value channel column %d in signal %s, column should be called "value_%d"'
                            % (i, sig_name, i),
                            flush=True,
                        )
                    sys.stdout = sys.__stdout__
                    return df, False
            is_categorical = int(categ_numeric_cols[i]) > 0
            if is_categorical:
                df_i[col_name] = df_i[col_name].astype(str).map(lambda x: x.strip())
            else:
                # Check if "should check Date":
                if i < len(units_m) and units_m[i].lower() == "date":
                    df_i = fix_date_col(
                        df_i, col_name, sig_name, batch_num, print_error
                    )
                    if type(df_i) != pd.DataFrame:
                        if print_error:
                            print(
                                'ERROR :: Can\'t convert date column %d in signal %s, column should be called "time_%d"'
                                % (i, sig_name, i),
                                flush=True,
                            )
                        sys.stdout = sys.__stdout__
                        return df, False
        if len(all_sigs) > 0:  # Store manipulations in df from df_i:
            df = pd.concat(
                [df[df["signal"] != sig_name].reset_index(drop=True), df_i],
                ignore_index=True,
            )

        # sys.stdout=sys.__stdout__
        # return df, False
    # All Tests passed
    sys.stdout = sys.__stdout__
    return df, True


def test_df(df, signal_type, sig_types, batch_num, workdir, codedir, print_error=True):
    outputs_dir = os.path.join(workdir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    _setup_plotly_js(workdir)
    test_logger_file = os.path.join(outputs_dir, f"tests.{signal_type}.log")
    sys.stdout = Logger(test_logger_file)
    # test dataframe structure, values and decide if valid or not.

    # Test df has "signal" column and pid column"
    if "pid" not in df.columns:
        print(
            'ERROR :: Failed %s - dataframe has no "pid" column' % (signal_type),
            flush=True,
        )
        sys.stdout = sys.__stdout__
        return df, False
    if "signal" not in df.columns:
        print(
            'ERROR :: Failed %s - dataframe has no "signal" column' % (signal_type),
            flush=True,
        )
        sys.stdout = sys.__stdout__
        return df, False

    batch_info = ""
    if batch_num is not None:
        batch_info = f"(batch {batch_num})"
    print("Running tests for %s%s" % (signal_type, batch_info), flush=True)
    # Do for each "signal" in df - df might have multiple "values":
    # Test pid is not None
    na_pids = sum(df["pid"].isna())
    if na_pids > 0:
        raise NameError(
            f'There are {na_pids} None values in "pid" column for "{signal_type}"'
        )
    all_sigs = set(df["signal"].values)
    all_signals_ok = True
    res_additional = True
    for sig_name in all_sigs:
        if sig_name not in sig_types:
            if sig_name is not None:
                print(
                    "ERROR :: signal %s is not defined in signals [%s], please define it, for more tests"
                    % (sig_name, signal_type),
                    flush=True,
                )
            sys.stdout = sys.__stdout__
            return df, False
        if len(all_sigs) > 0:
            df_i = df[df["signal"] == sig_name].reset_index(drop=True).copy()
        else:
            df_i = df  # no need to copy

        # Test that pid is integer - if not, go to FinalSignals, search for ID2NR and convert

        # Now fetch signal type table and test dates columns, test validity of each date column. Than move to value columns.
        si = sig_types[sig_name]
        t_ch = si.t_ch
        v_ch = si.v_ch
        categ_numeric_cols = si.v_categ
        units_m = si.units
        # print('signal %s, has %d, %d channels %s'%(signal_type, len(t_ch), len(v_ch), categ_numeric_cols))
        # Lets's check time channels:
        first_time_col = None
        for i in range(len(t_ch)):
            col_name = "time_%d" % (i)
            if not (col_name in df.columns):
                col_name = "date_%d" % (i)
                if not (col_name in df.columns):
                    if print_error:
                        print(
                            'ERROR :: Can\'t find time channel column %d in signal %s, column should be called "time_%d"'
                            % (i, sig_name, i),
                            flush=True,
                        )
                    sys.stdout = sys.__stdout__
                    return df, False
            if first_time_col is None:
                first_time_col = col_name
            if not (
                test_date_column(
                    df_i, col_name, sig_name, batch_num, workdir, print_error
                )
            ):
                sys.stdout = sys.__stdout__
                return df, False

        # Test numeric:
        for i in range(len(v_ch)):
            col_name = "value_%d" % (i)
            if not (col_name in df.columns):
                col_name = "val_%d" % (i)
                if not (col_name in df.columns):
                    if print_error:
                        print(
                            'ERROR :: Can\'t find value channel column %d in signal %s, column should be called "value_%d"'
                            % (i, sig_name, i),
                            flush=True,
                        )
                    sys.stdout = sys.__stdout__
                    return df, False
            is_categorical = int(categ_numeric_cols[i]) > 0
            if is_categorical:
                if not (
                    test_categorical_column(
                        df_i, col_name, sig_name, batch_num, workdir, print_error
                    )
                ):
                    sys.stdout = sys.__stdout__
                    return df, False
            else:
                # Check if "should check Date":
                if i < len(units_m) and units_m[i].lower() == "date":
                    if not (
                        test_date_column(
                            df_i, col_name, sig_name, batch_num, workdir, print_error
                        )
                    ):
                        sys.stdout = sys.__stdout__
                        return df, False
                else:
                    if not (
                        test_numeric_column(
                            df_i, col_name, sig_name, batch_num, workdir, print_error
                        )
                    ):
                        sys.stdout = sys.__stdout__
                        return df, False
        # Run additional_tests!
        # print(f'Before tests {sig_name} was {len(df_i)}')
        res_additional = additional_tests(
            df_i, sig_name, sig_types, workdir, codedir, print_error
        )
        # print(f'After tests {sig_name} is {len(df_i)}')

        if len(all_sigs) > 0:  # Store manipulations in df from df_i:
            df = pd.concat(
                [df[df["signal"] != sig_name].reset_index(drop=True), df_i],
                ignore_index=True,
            )
        if not (res_additional):
            all_signals_ok = False  # run all tests till end
            # sys.stdout=sys.__stdout__
            # return df, False

    # All Tests passed
    sys.stdout = sys.__stdout__
    return df, all_signals_ok


# Will load all tests from dir called tests, by directory name + local dir in $WORKDIR/configs/tests
def load_all_tests(codedir):
    global_tests = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tests")
    all_tags = os.listdir(global_tests)
    all_tests = dict()
    for sig_tag in all_tags:
        full_pt = os.path.join(global_tests, sig_tag)
        for test_file in os.listdir(full_pt):
            if not (test_file.endswith(".py")):
                continue
            full_name = os.path.join(full_pt, test_file)
            if sig_tag not in all_tests:
                all_tests[sig_tag] = []
            all_tests[sig_tag].append(full_name)
    # Now read from codedir:
    local_test = os.path.join(codedir, "tests")
    all_tags = []
    if os.path.exists(local_test):
        all_tags = os.listdir(local_test)
    for sig_tag in all_tags:
        full_pt = os.path.join(local_test, sig_tag)
        for test_file in os.listdir(full_pt):
            if not (test_file.endswith(".py")):
                continue
            full_name = os.path.join(full_pt, test_file)
            if sig_tag not in all_tests:
                all_tests[sig_tag] = []
            # remove global test, if has same name in local:
            existing_names = set(map(lambda x: os.path.basename(x), all_tests[sig_tag]))
            if test_file in existing_names:
                # remove global test from all_tests[sig_tag]:
                all_tests[sig_tag] = list(
                    filter(
                        lambda x: os.path.basename(x) != test_file, all_tests[sig_tag]
                    )
                )
            all_tests[sig_tag].append(full_name)
    return all_tests


def additional_tests(df, signal_type, sig_types, workdir, codedir, print_error=True):
    # load additional tests for signal!
    tests = load_all_tests(codedir)
    si = sig_types[signal_type]
    sig_classes = set(si.classes)
    sig_classes.add(signal_type)
    # filter relevant tests for signal:
    all_tests_status = True
    cwd = os.getcwd()
    for tag, test_full_path_list in tests.items():
        if tag not in sig_classes:  # skip irelevant test
            continue
        # load test:
        for test_full_path in test_full_path_list:
            os.chdir(
                os.path.dirname(__file__)
            )  # Change working directory to test directory
            test_name = os.path.basename(test_full_path)[:-3]
            spec = importlib.util.spec_from_file_location(test_name, test_full_path)
            if spec is None:
                raise ImportError(
                    f"Could not load test {test_name} from {test_full_path}"
                )
            test_logic = importlib.util.module_from_spec(spec)
            sys.modules[test_name] = test_logic
            if spec.loader is None:
                raise ImportError(
                    f"Could not load test {test_name} from {test_full_path}"
                )
            spec.loader.exec_module(test_logic)

            res = None
            try:
                if print_error:
                    res = test_logic.Test(df, si, codedir, workdir)
                else:
                    with contextlib.redirect_stdout(None):
                        res = test_logic.Test(df, si, codedir, workdir)
            except:
                if print_error:
                    print(
                        "Error in test %s, test failed. full path %s"
                        % (test_name, test_full_path),
                        flush=True,
                    )
                    traceback.print_exc()
                res = False
            if not (res):
                all_tests_status = False
    # run all tests till end - don't stop at first failed test
    os.chdir(cwd)
    return all_tests_status
