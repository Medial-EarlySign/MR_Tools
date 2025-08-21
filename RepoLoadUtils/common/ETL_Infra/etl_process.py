"""
ETL Infra
"""

import sys, re, subprocess, os, traceback
import pandas as pd
import numpy as np
from IPython import embed
from traitlets.config import get_config
from typing import Optional, Generator, List, Callable, Literal

from .logger import Tee, Logger
from .define_signals import load_signals_map
from .map_signals import handle_mapping
from .test_signals import test_df, minimal_test_df
from .etl_loading_status import *
from .process_signals import process_default_before, process_default_after
from .dict_utils import *
from .build_config_file import create_convert_config_file
from .unit_conversions import process_unit_conversion, fix_units

from .env import *


def read_signals_defs():
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return load_signals_map(FULL_SIGNALS_TYPES, codedir)


global_logger = Tee()


def generate_labs_mapping_and_units_config(
    df: pd.DataFrame, samples_per_signal: int = 5
) -> None:
    """
    Creates a config table for signal+unit under CODE_DIR/config/map_units_stats.cfg

    :param df: the dataframe to process. have columns : signal, unit
    :param samples_per_signal: how many example values to fecth for each signal+unit combination
    """
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    cfg_dir = os.path.join(codedir, "configs")
    os.makedirs(cfg_dir, exist_ok=True)
    map_unit_cfg = os.path.join(cfg_dir, "map_units_stats.cfg")
    needed = ["signal", "unit", "value_0"]
    for col in needed:
        if col not in df.columns:
            raise NameError(f'Please provide dataframe with "{col}" column')
    sig_def = read_signals_defs()

    process_unit_conversion(df, map_unit_cfg, sig_def, samples_per_signal)


# Assume df have columns : signal, unit
def map_and_fix_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Uses the configuration file of the units to convert the units

    :param df:  the dataframe to process. have columns : signal, unit
    """
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    map_unit_cfg = os.path.join(codedir, "configs", "map_units_stats.cfg")
    if not (os.path.exists(map_unit_cfg)):
        raise NameError(
            "Please call generate_labs_mapping_and_units_config, or generate config file\n%s"
            % (map_unit_cfg)
        )
    needed = ["signal", "unit", "value_0"]
    for col in needed:
        if col not in df.columns:
            raise NameError(f'Please provide dataframe with "{col}" column')
    df = fix_units(df, map_unit_cfg)
    return df


def clean_color(st):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", st)


def merge_lines(lines):
    multi_line = re.compile("^   ...: ")
    t_command = re.compile(r"(?:In|Out) \[[0-9]+\]:")
    curr_line = None
    prev_line_idx = None
    for i in range(len(lines)):
        line = lines[i]
        if len(multi_line.findall(line)) > 0 and i > 1:
            lines[prev_line_idx] = lines[prev_line_idx].strip("\n") + multi_line.sub(
                " ", line
            )
            lines[i] = None
            continue
        if len(t_command.findall(line)) > 0:
            curr_f = t_command.findall(line)[0]
            if curr_line is None:
                curr_line = curr_f
            else:
                if curr_line == curr_f:  # same shit, merge lines:
                    lines[prev_line_idx] = lines[prev_line_idx].strip("\n") + lines[i]
                    lines[i] = None
                    continue
                else:  # new section
                    curr_line = curr_f
        prev_line_idx = i
    lines = list(filter(lambda x: x is not None, lines))

    # now remove duplicate lines that starts with same prefix:
    prev_line_prefix = None
    for i in range(len(lines)):
        line = lines[i]
        if len(t_command.findall(line)) > 0:
            curr_f = t_command.findall(line)[0]
            if (
                curr_f == prev_line_prefix and i > 0 and prev_line_prefix is not None
            ):  # Keep only this line and remove previous
                lines[i - 1] = None
            else:
                prev_line_prefix = curr_f
        else:
            prev_line_prefix = None

    lines = list(filter(lambda x: x is not None, lines))

    return lines


def clean_prefix(st):
    # Take initial
    st = st.strip("\n")
    input_cmd = re.compile(r"In \[[0-9]+\]:")
    full_matches = list(input_cmd.finditer(st))
    if len(full_matches) > 0:
        first_token = full_matches[0].group()
        # Duplication - take second part:
        idx = st.rindex(first_token)
        st = st[idx:]

        idx = st.find("]")
        if idx > 0:
            st = st[idx + 3 :]
    return st.strip()


def clean_to_output(s):
    t_command = re.compile(r"(?:In|Out) \[[0-9]+\]: ")
    res = list(t_command.finditer(s))
    if len(res) > 0:
        idx = res[-1].start()
        s = s[idx:]

    return s.strip()


def fetch_code(full_log_path, store_clean_path, editor):
    # Does not support multi line right now

    # Filter In []
    input_command = re.compile(r"In \[[0-9]+\]:")
    fr = open(full_log_path, "r")
    lines = fr.readlines()
    fr.close()

    lines = list(map(clean_color, lines))  # need to remove color
    lines = merge_lines(lines)
    lines = list(filter(lambda x: len(input_command.findall(x)) > 0, lines))
    lines = list(map(clean_prefix, lines))  # need to remove number

    # TODO: Add header of instruction + df.head
    if lines[-1].strip() == "exit":
        lines = lines[:-1]
    code_block = "\n".join(lines)

    # fw=open(store_clean_path, 'a')
    # fw.write(code_block)
    # fw.close()
    # Edit with vim for now
    if editor is not None:
        proc = subprocess.Popen(
            [editor, store_clean_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()


def exec_code_block(
    store_clean_path, _locals, process_logger_file, batch_num, print_code=True
):
    fr = open(store_clean_path, "r")
    code_block = fr.read()
    fr.close()

    if print_code:
        print("Will excute this code:\n", flush=True)
        print("####### CODE FROM %s ##########" % (store_clean_path), flush=True)
        print(code_block, flush=True)
        print("##########################END CODE##########", flush=True)

    done_succ = False
    if batch_num is not None:
        sys.stdout = Logger(process_logger_file, f"batch_{batch_num}")
    else:
        sys.stdout = Logger(process_logger_file)
    try:
        exec(code_block, globals(), _locals)
        done_succ = True
    except:
        print(
            f"Error in excution of code from {store_clean_path}, please fix", flush=True
        )
        print(_locals["df"], flush=True)
        print(traceback.format_exc(), flush=True)
    sys.stdout = sys.__stdout__

    return code_block, done_succ


def print_old_code(store_clean_path):
    MAX_PRINT = 10000
    fr = open(store_clean_path, "r")
    code_block = fr.read()
    fr.close()
    print("####### CODE FROM %s ##########" % (store_clean_path), flush=True)
    print(code_block[:MAX_PRINT], flush=True)
    if len(code_block) > MAX_PRINT:
        print("##### Truncated in the middle", flush=True)
    print("##########################END CODE##########", flush=True)


def print_and_fw(fw, str_msg):
    fw.write(str_msg)
    print(str_msg.replace("\n#", "\n").lstrip("#"), end=" ", flush=True)


def process_and_open_shell_when_needed(
    df,
    signal_name,
    sig_types,
    workdir,
    full_log_path="/tmp/code_block.log",
    store_clean_path="/tmp/clean_code.py",
    batch_num=None,
    editor: str | None = None,
    interactive=True,
):
    if not (interactive):
        editor = None
    code_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    _locals = locals()
    process_log_file = os.path.join(
        workdir, "signal_processings_log", f"process_{signal_name}.log"
    )

    # clean log file on first batch:
    if batch_num is None or batch_num == 0:
        fw = open(process_log_file, "w")
        fw.close()
    code_block_name = get_code_name(signal_name, workdir, sig_types)
    _store_clean_path = store_clean_path

    if code_block_name != store_clean_path:
        _store_clean_path = os.path.join(
            code_dir, "signal_processings", code_block_name + ".py"
        )

    if os.path.exists(_store_clean_path):  # Has code file, was done in the past
        if batch_num is None or batch_num == 0:  # Print code only in first time
            if interactive:
                print_old_code(_store_clean_path)
            print(
                "Already defined code to execute from %s"
                % (os.path.basename(_store_clean_path)),
                flush=True,
            )
        code, done_succ = exec_code_block(
            _store_clean_path, _locals, process_log_file, batch_num, False
        )  # Excute
        if done_succ:
            df = _locals["df"]
            if signal_name == "labs":
                codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
                map_unit_cfg = os.path.join(codedir, "configs", "map_units_stats.cfg")
                if os.path.exists(map_unit_cfg) and "unit" in df.columns:
                    print("In labs fixing units...")
                    if "signal.original" not in df.columns:
                        df = map_and_fix_units(df)
                    else:
                        print("Already fixed units, skipping...")
                else:
                    print(
                        f"Warning! Labs has no unit configuration, please configure in {map_unit_cfg} and add unit column"
                    )
            return df, done_succ

    if not (os.path.exists(_store_clean_path)):
        print(
            'Code block for signal "%s" is missing (code block name "%s") - creating it'
            % (signal_name, code_block_name),
            flush=True,
        )
    else:
        if interactive:
            print("Adding code to existing block...", flush=True)

    if signal_name in sig_types:
        si = sig_types[signal_name]
        print(
            "You can also create/edit files with preceding names that are tried before: [%s]"
            % (",".join(map(lambda x: x + ".py", si.classes))),
            flush=True,
        )

    # Add instructions in the begining of code template
    if not (os.path.exists(_store_clean_path)):
        fw = open(_store_clean_path, "w")
        if signal_name in sig_types:
            str_msg = f'#You have dataframe called "df". Please process it to generare signal "{signal_name}"\n'
        else:
            str_msg = f'#You have dataframe called "df". Please process it to generare signal/s of class "{signal_name}"\n'
        print_and_fw(fw, str_msg)

        candidate_name = signal_name
        if signal_name not in sig_types:
            # breakpoint()
            potential = list(
                filter(lambda x: signal_name in x.classes, sig_types.values())
            )  # try find an example from this class
            if len(potential) > 0:
                candidate_name = potential[0].name

        if candidate_name in sig_types:
            si = sig_types[candidate_name]
            if candidate_name != signal_name:
                print_and_fw(
                    fw, f"\n#Example signal from this class might be {candidate_name}\n"
                )

            print_and_fw(fw, f"\n#The target dataframe should have those columns:\n")
            print_and_fw(fw, f"#    pid\n#    signal\n")
            for i_ch in range(len(si.t_ch)):
                print_and_fw(fw, f"#    time_{i_ch} - type {si.t_ch[i_ch]}\n")
            for i_ch in range(len(si.v_ch)):
                if int(si.v_categ[i_ch]) > 0:
                    print_and_fw(
                        fw,
                        f"#    value_{i_ch} - string categorical (rep channel type {si.v_ch[i_ch]})\n",
                    )
                else:
                    print_and_fw(
                        fw,
                        f"#    value_{i_ch} - numeric (rep channel type {si.v_ch[i_ch]})\n",
                    )
        else:
            print_and_fw(
                fw,
                f'\n#Signal or class of signal "{signal_name}" is not recognized. please define it in rep.signals first\n',
            )
            print_and_fw(fw, f"#or change signal column to known one\n")

        print_and_fw(fw, "\n#Source Dataframe - df.head() output:")
        df_head_str = "%s" % (df.head())
        df_head_str = df_head_str.replace("\n", "\n#")
        print_and_fw(fw, f"\n#{df_head_str}\n")

        if signal_name == "labs":
            map_unit_cfg = os.path.join(code_dir, "configs", "map_units_stats.cfg")
            print_and_fw(
                fw, "#Adding mapping\\units code blocks for you as starting point\n"
            )
            print_and_fw(fw, "generate_labs_mapping_and_units_config(df, 5)\n")
            print_and_fw(
                fw,
                f'#Please edit the file "{map_unit_cfg}" and then comment out previous line for speedup in next run\n',
            )
            print_and_fw(
                fw, "# df=map_and_fix_units(df) # Will be called automatically\n"
            )
        fw.close()

    if not (interactive):
        return df, False

    print("Opening debug shell...", flush=True)
    global_logger.change_log_file(full_log_path, "w")
    sys.stdout = global_logger
    c = get_config()
    # c.InteractiveShellEmbed.cdfolors = "Linux"
    # c.InteractiveShellEmbed.cdfolors = ''
    # c.InteractiveShellEmbed.colors = ''
    c.InteractiveShell.logappend = _store_clean_path
    c.InteractiveShell.logstart = True
    df_before = df.copy()
    embed(config=c)
    del df
    df = df_before
    global_logger.close_log()  # To close file
    sys.stdout = sys.__stdout__
    # Generate clean log:
    fname = os.path.basename(full_log_path)
    if fname.find("."):
        fname = fname[: fname.rindex(".")]
    full_clean_log = os.path.join(os.path.dirname(full_log_path), fname + ".clean.log")
    fr = open(full_log_path, "r")
    lines = fr.readlines()
    fr.close()
    lines = list(map(clean_color, lines))
    lines = merge_lines(lines)
    lines = list(map(clean_to_output, lines))
    fw_log = open(full_clean_log, "w")
    fw_log.writelines(map(lambda x: x + "\n", lines))
    fw_log.close()
    print(
        "Done, please edit and clean your code to store for future and compact usage in your editor",
        flush=True,
    )
    print("The code file is located in %s" % (store_clean_path), flush=True)

    # Process df using this cleaned code:
    fetch_code(full_log_path, store_clean_path, editor)

    _locals = locals()
    if batch_num is None or batch_num == 0:
        print("Before processing:\n", df.head(), flush=True)
    code, done_succ = exec_code_block(
        store_clean_path, _locals, process_log_file, batch_num
    )  # Excute
    if signal_name == "labs":
        codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
        map_unit_cfg = os.path.join(codedir, "configs", "map_units_stats.cfg")
        if os.path.exists(map_unit_cfg) and "unit" in df.columns:
            print("In labs fixing units...")
            if "signal.original" not in df.columns:
                df = map_and_fix_units(df)
            else:
                print("Already fixed units, skipping...")
        else:
            print(
                f"Warning! Labs has no unit configuration, please configure in {map_unit_cfg} and add unit column"
            )

    if done_succ:
        df = _locals["df"]
        print("After processing:\n", df.head(), flush=True)
    # Test df
    return df, done_succ


def get_code_name(signal_name, workdir, sig_types):
    code_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    base_dir = os.path.join(code_dir, "signal_processings")
    store_clean_path = os.path.join(base_dir, signal_name + ".py")
    if signal_name not in sig_types:
        return signal_name

    classes = sig_types[signal_name].classes
    # from most speiocifc to least:
    if os.path.exists(store_clean_path):
        return signal_name
    # Iteratate from last to first:
    for cl_code in classes[::-1]:
        store_clean_path = os.path.join(base_dir, cl_code + ".py")
        if os.path.exists(store_clean_path):
            return cl_code

    # Not found, return most specific
    return signal_name


def filter_cols(col_name, good_cols):
    if not (
        col_name.startswith("time_")
        or col_name.startswith("date_")
        or col_name.startswith("value_")
        or col_name.startswith("val_")
    ):
        return True
    # need to filter - this column start with prefix of col
    return col_name in good_cols


def test_if_has_code_to_execute(signal_name, workdir, sig_types):
    code_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    code_block_name = get_code_name(signal_name, workdir, sig_types)
    store_clean_path = os.path.join(code_dir, "signal_processings", signal_name + ".py")
    _store_clean_path = store_clean_path
    if code_block_name != store_clean_path:
        _store_clean_path = os.path.join(
            code_dir, "signal_processings", code_block_name + ".py"
        )
    return os.path.exists(_store_clean_path)


def fetch_signal(
    df,
    signal_name,
    workdir,
    sig_types,
    batch_num=None,
    skip_batch_tests=False,
    editor=None,
    override="n",
    interactive=True,
):
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(os.path.join(workdir, "signal_processings_log"), exist_ok=True)
    os.makedirs(os.path.join(workdir, "FinalSignals"), exist_ok=True)
    full_log_path = os.path.join(
        workdir, "signal_processings_log", signal_name + ".log"
    )
    code_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.makedirs(os.path.join(code_dir, "signal_processings"), exist_ok=True)
    store_clean_path = os.path.join(code_dir, "signal_processings", signal_name + ".py")

    # clean log when needed - when in first batch:
    test_log_path = os.path.join(workdir, "outputs", f"tests.{signal_name}.log")
    if os.path.exists(test_log_path) and ((batch_num is None) or (batch_num == 0)):
        fw = open(test_log_path, "w")
        fw.close()  # Clean log
    code_block_name = get_code_name(signal_name, workdir, sig_types)
    _store_clean_path = store_clean_path
    if code_block_name != store_clean_path:
        _store_clean_path = os.path.join(
            code_dir, "signal_processings", code_block_name + ".py"
        )
    has_code_block = os.path.exists(_store_clean_path)

    df = process_default_before(df, signal_name, sig_types, workdir)
    # check if has processing unit, if has, skip this test!
    has_code_to_exec = test_if_has_code_to_execute(signal_name, workdir, sig_types)
    no_batches = batch_num is None or batch_num == 0
    if not (has_code_to_exec):
        succ = True
        if not (skip_batch_tests) or no_batches:
            df, succ = test_df(
                df,
                signal_name,
                sig_types,
                batch_num,
                workdir,
                code_dir,
                not (has_code_block),
            )
        else:
            df, succ = minimal_test_df(
                df,
                signal_name,
                sig_types,
                batch_num,
                workdir,
                code_dir,
                not (has_code_block),
            )
    else:
        succ = False
    df = process_default_after(df, signal_name, sig_types, workdir)
    df_before = df.copy()
    if succ:
        print(
            'Signal "%s" is ok. no need for special processing. Please see tests in outputs, if you want'
            % (signal_name),
            flush=True,
        )
        # Rerun again to get all logs
        if has_code_block:
            if not (skip_batch_tests) or no_batches:
                df, succ = test_df(
                    df, signal_name, sig_types, batch_num, workdir, code_dir
                )
            else:
                df, succ = minimal_test_df(
                    df, signal_name, sig_types, batch_num, workdir, code_dir
                )
    else:
        print('Signal "%s", needs processings' % (signal_name), flush=True)
        df, done_succ = process_and_open_shell_when_needed(
            df,
            signal_name,
            sig_types,
            workdir,
            full_log_path,
            store_clean_path,
            batch_num,
            editor,
            interactive,
        )
        # test again
        if done_succ:
            succ = True
            if not (skip_batch_tests) or no_batches:
                df, succ = test_df(
                    df, signal_name, sig_types, batch_num, workdir, code_dir
                )
            else:
                df, succ = minimal_test_df(
                    df, signal_name, sig_types, batch_num, workdir, code_dir
                )
        else:
            succ = False
    if succ:
        print(
            'OK, there are no more issues for signal "%s"...' % (signal_name),
            flush=True,
        )
    else:
        print(
            'There are stil issues!!, rerun again for signal "%s"' % (signal_name),
            flush=True,
        )
        df = df_before  # rollback
        return df, False

    # Final sorting, and store in right place for loading:

    # sort and last arrangment to file
    sort_by = ["pid"]
    full_ds_cols = ["pid", "signal"]
    if "time_0" in df.columns:
        sort_by.append("time_0")
    elif "date_0" in df.columns:
        sort_by.append("date_0")
    else:
        pass

    for col_name in df.columns:
        if col_name.startswith("time_") or col_name.startswith("date_"):
            full_ds_cols.append(col_name)
    for col_name in df.columns:
        if col_name.startswith("value_") or col_name.startswith("val_"):
            full_ds_cols.append(col_name)

    df["pid"] = df["pid"].astype(int)
    df = (
        df.drop_duplicates(subset=full_ds_cols)
        .sort_values(sort_by)
        .reset_index(drop=True)
    )
    # add other columns:
    set_added = set(full_ds_cols)
    for col_name in df.columns:
        if col_name not in set_added:
            full_ds_cols.append(col_name)
    # order columns:
    df = df[full_ds_cols]

    # save file
    # Write by each Signal name:
    all_sigs_in_df = sorted(list(set(df["signal"].values)))
    os.makedirs(os.path.join(workdir, "outputs"), exist_ok=True)
    categorical_stats = os.path.join(workdir, "outputs", "signal_categorical_stats")
    os.makedirs(categorical_stats, exist_ok=True)
    if len(all_sigs_in_df) > 1:
        print("Start saving files...", flush=True)
    for sig_s in all_sigs_in_df:
        final_file = os.path.join(workdir, "FinalSignals", sig_s)
        if batch_num is not None:
            final_file = os.path.join(
                workdir, "FinalSignals", sig_s + "." + str(batch_num)
            )
        if sig_s in sig_types:
            si = sig_types[sig_s]
            # Filter columns time_*, value_* that are out of bounds:
            good_cols = set(list(map(lambda x: "time_" + str(x), range(len(si.t_ch)))))
            good_cols = good_cols.union(
                set(list(map(lambda x: "date_" + str(x), range(len(si.t_ch)))))
            )
            good_cols = good_cols.union(
                set(list(map(lambda x: "value_" + str(x), range(len(si.v_ch)))))
            )
            good_cols = good_cols.union(
                set(list(map(lambda x: "val_" + str(x), range(len(si.v_ch)))))
            )
            full_ds_cols = list(
                filter(lambda x: filter_cols(x, good_cols), full_ds_cols)
            )
            df = df[full_ds_cols]
        else:
            raise Exception(f"Signal {sig_s} is not defined in rep.signals")
        if batch_num is None or batch_num == 0 or len(all_sigs_in_df) == 1:
            print("Storing file in [%s]..." % (final_file), flush=True)

        # Let's convert integer columns:
        for ch_i, type_i in enumerate(si.t_ch):
            col_name = f"time_{ch_i}"
            if type_i.endswith("s") or type_i.endswith("i"):
                df[col_name] = df[col_name].astype(int)
        for ch_i, type_i in enumerate(si.v_ch):
            col_name = f"value_{ch_i}"
            is_categ = si.v_categ[ch_i]
            if not (is_categ) and (type_i.endswith("s") or type_i.endswith("i")):
                df[col_name] = df[col_name].astype(int)

        sort_by = ["pid"]
        if "time_0" in full_ds_cols:
            sort_by.append("time_0")
        elif "date_0" in full_ds_cols:
            sort_by.append("date_0")
        else:
            pass

        df[df["signal"] == sig_s].sort_values(sort_by).reset_index(drop=True).to_csv(
            final_file, sep="\t", index=False, header=False
        )

        # Let's store stats for categorical:
        for ch_i, categ_i in enumerate(si.v_categ):
            if categ_i == "0":
                continue
            full_file_pt = os.path.join(categorical_stats, f"{sig_s}.value_{ch_i}")
            if batch_num is not None:
                full_file_pt = full_file_pt + "." + str(batch_num)
            stats_categ = (
                df[df["signal"] == sig_s]
                .reset_index(drop=True)
                .rename(columns={f"val_{ch_i}": f"value_{ch_i}"})[
                    ["pid", f"value_{ch_i}"]
                ]
                .groupby(f"value_{ch_i}")
                .agg(["count", "nunique"])
                .reset_index()
            )
            stats_categ.columns = [f"value_{ch_i}", "total_count", "count_pid"]
            stats_categ.sort_values("total_count", ascending=False).reset_index(
                drop=True
            ).to_csv(full_file_pt, sep="\t", index=False)
    if len(all_sigs_in_df) > 1:
        print("Finished saving all files", flush=True)

    return df, True


def get_input_yn(message):
    while True:
        res = input(f"{message} Y/N? ").upper()
        if res == "N" or res == "Y":
            return res
        else:
            print('Unknown option "%s", try again' % (res), flush=True)


def map_fetch_and_process(
    data_fetcher,
    workdir,
    signal,
    batch_size,
    write_batch=None,
    skip_batch_tests=False,
    editor: str | None = None,
    map_editor: str | None = None,
    override="n",
    interactive=True,
):
    # data_fetcher - is function which accepts:
    # workdir - workdir folder
    # signal - name of signal/s with comma netween - each signal is processing unit to process/test and load for the same data source
    # batch_size - batch size to handle for tis data source
    # write_batch - parameter to batch start write- by default 0 - when single batch, ignores this.
    override = override.lower()
    sig_types = read_signals_defs()
    exists_sig = set(sig_types.keys())
    os.makedirs(workdir, exist_ok=True)
    sig_load_status = get_load_status(workdir)
    sig_load_batches = get_load_batch_status(workdir)
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    # sigs=list(set(df['signal'].values))
    # Test all intersection  with classes
    flat_cls = set()
    good_classed = list(map(lambda x: set(x.classes), sig_types.values()))
    for cls in good_classed:
        flat_cls = flat_cls.union(cls)
    flat_cls = flat_cls.union(set(exists_sig))
    # breakpoint()
    succ_all_batches = True
    start_batch = 0  # Holds from where to start reading input
    start_batch_output = 0

    signals_ls = []
    start_batch_ls = []  # Holds from where to start writing output
    skip_list = set()
    if signal is not None:
        signals_ls_ = signal.split(",")
        for sig in signals_ls_:
            start_batch = None
            if sig not in flat_cls and sig != "all":
                print(
                    f'Warning signal_type "{sig}" is not defined in rep.signals by name or tag',
                    flush=True,
                )

            if sig in sig_load_status and sig_load_status[sig][1] == "Completed":
                if override == "n":
                    print(f'Signal "{sig}" was loaded successfully, skip', flush=True)
                    skip_list.add(sig)
                    continue
                else:
                    print(
                        f"Signal {sig} was loaded successfully, but you are overwriteing it",
                        flush=True,
                    )
            signals_ls.append(sig)
            start_batch_ = 0
            if write_batch is not None:
                start_batch_ = write_batch
                print(f"Start write for {sig} at batch {write_batch}", flush=True)
            if sig in sig_load_batches:
                print(
                    "Signal %s was stopped at batch %d"
                    % (sig, sig_load_batches[sig][1]),
                    flush=True,
                )
                if override == "n":
                    start_batch_ = sig_load_batches[sig][1] + 1
            if start_batch is None or start_batch_ < start_batch:  # find minimum
                start_batch = start_batch_
            start_batch_ls.append(start_batch_)
            print(f"Fetching data for {sig} from batch {start_batch}...", flush=True)
    else:
        start_batch_ = 0
        if write_batch is not None:
            start_batch_ = write_batch
            print(f"Start write for unknown signal at batch {write_batch}", flush=True)
        else:
            print("Fetching unkown signal...", flush=True)
        signals_ls = [None]
        start_batch_ls = [start_batch_]

    if len(signals_ls) == 0:  # proccess all - no need to do something
        return True

    if write_batch is not None:
        start_batch_output = write_batch
    interact = interactive
    all_sigs = set()
    print(f"Final Data start batch: {start_batch}")
    for i, df in enumerate(data_fetcher(batch_size, start_batch)):
        if "signal" not in df.columns:
            df["signal"] = None

        succ = False
        df_sig = handle_mapping(
            df, sig_types, codedir, interactive=(interact and i == 0), editor=map_editor
        )
        sig_list_df = set(df_sig[df_sig["signal"].notnull()]["signal"].values)
        missing_sig_rows = len(df_sig[df_sig["signal"].isnull()])
        if missing_sig_rows > 0:
            sig_list_df.add(None)
        demo_sigs = ["BYEAR", "BDATE", "GENDER", "demographic"]
        sig_list_df = sorted(
            list(sig_list_df),
            key=lambda x: (
                x
                if x not in demo_sigs and x is not None
                else "" if x is not None else "~"
            ),
        )
        if (
            i == 0
            and override == "y"
            and (
                len(set(sig_list_df).intersection(set(demo_sigs))) > 0
                or len(set(signals_ls).intersection(set(demo_sigs))) > 0
            )
        ):
            ID2NR_path = os.path.join(workdir, "FinalSignals", "ID2NR")
            print(
                "WARNNING!!! Override - removing existing ID2NR in first iteration. If you have multiple prepare_final_signal to create demographic"
            )
            print("WARNNING!!! with overrirde=yes this can cause problems.")
            if os.path.exists(ID2NR_path):
                os.remove(ID2NR_path)

        # process by signals_ls, start_batch_ls
        batch_i = start_batch + i  # current input batch
        if batch_size == 0:
            batch_i = None  # Mark that there are no batches!
        while not (succ):
            # Handle each mapped "signal" separately - and the rest in the end:
            batch_succ = True
            res_all_sigs = []
            # split to signals inside if signal column is exists with value:
            for curr_sig in sig_list_df:
                if curr_sig is None:
                    full_proc = []
                    for index_i, sig_n in enumerate(signals_ls):
                        start_b = start_batch_ls[index_i]
                        batch_ii = start_b + i  # target output batch to write
                        if batch_size == 0 and (write_batch is None):
                            batch_ii = None
                        if batch_ii is not None and batch_ii < start_batch_output:
                            print(
                                f"Skiping input batch {batch_i} for empty_signal. output batch was {batch_ii}",
                                flush=True,
                            )
                            continue
                        df_sig_c = (
                            df_sig[df_sig["signal"].isnull()]
                            .reset_index(drop=True)
                            .copy()
                        )
                        df_sig_c, suc_i = fetch_signal(
                            df_sig_c,
                            sig_n,
                            workdir,
                            sig_types,
                            batch_ii,
                            skip_batch_tests,
                            editor,
                            override if i == 0 else "n",
                            interactive,
                        )
                        if not (suc_i):
                            succ = False
                            break
                        else:
                            succ = True
                        full_proc.append(df_sig_c)
                    if len(full_proc) > 0:
                        df_sig_c = pd.concat(full_proc, ignore_index=True)
                else:
                    df_sig_c = (
                        df_sig[df_sig["signal"] == curr_sig]
                        .reset_index(drop=True)
                        .copy()
                    )
                    batch_iii = 0
                    if batch_i is not None:
                        batch_iii = batch_i
                    df_sig_c, succ = fetch_signal(
                        df_sig_c,
                        curr_sig,
                        workdir,
                        sig_types,
                        start_batch_output + batch_iii,
                        skip_batch_tests,
                        editor,
                        override if i == 0 else "n",
                        interactive,
                    )

                if succ:
                    print(
                        "In map_fetch_and_process, after processing %s in batch %d succesfully"
                        % (signal, batch_i if batch_i is not None else 0),
                        flush=True,
                    )
                else:
                    print(
                        "In map_fetch_and_process, after processing %s in batch %d failed!"
                        % (signal, batch_i if batch_i is not None else 0),
                        flush=True,
                    )
                    batch_succ = False
                    break
                print(df_sig_c.head(), flush=True)
                res_all_sigs.append(df_sig_c)
            if batch_succ:
                df_sig = pd.concat(res_all_sigs, ignore_index=True)

            if batch_succ:
                if batch_i is not None:
                    signals_list_update = signal.split(",")
                    for sig in signals_list_update:
                        if sig not in skip_list:
                            update_batch_load_status(
                                workdir, sig, batch_i, override == "y"
                            )
                break
            res = "N"
            if interact:
                res = get_input_yn(f'Problem found, rerun again on signal "{signal}"?')
            if res == "N":
                succ_all_batches = False
                break
            else:  # Y
                sig_types = read_signals_defs()  # reread again

        if not (succ_all_batches):
            break
        all_sigs = all_sigs.union(set(df_sig["signal"].values))
    # Done all batches!
    signals_list_update = signal.split(",")
    for sig in signals_list_update:
        if sig not in skip_list:
            if succ_all_batches:
                update_load_status(workdir, sig, "Completed")
            else:
                update_load_status(workdir, sig, "Failed")
    if succ_all_batches and batch_size != 0:
        print("Let's test final signals!!", flush=True)
        for sig_name in all_sigs:
            df_final = load_final_sig(workdir, sig_types, sig_name)
            if df_final is not None:
                test_df(df_final, sig_name, sig_types, None, workdir, codedir)
    return succ_all_batches


# Main function - data is either Dataframe or data_fetcher(generator that can iterate and generate dataframes)
def prepare_final_signals(
    data: Callable[[int, int], Generator[pd.DataFrame, None, None]] | pd.DataFrame,
    workdir: str,
    sigs: str,
    batch_size: int = 0,
    start_write_batch: Optional[int] = None,
    skip_batch_tests: bool = False,
    editor: str | None = None,
    map_editor: str | None = None,
    override: Literal["y", "n"] = "n",
    interactive: bool = False,
) -> bool:
    """
    The main function to generate FinalSignals using batches of DataFrames.\n
    The code will do the following for each batch:\n
    1. When pid is not numeric a conversion is needed. If the signal is part of "demographic" \n
    it will creating a mappsing file from the string to numeric number. If the signal is not demographic,\n
    it will use the mapping to convert it to numeric. The mapping will be stored inside workdir/FinalSignals/ID2NR \n
    2. If we have "signals" column and the signal is "unknown" it will try to use "config/map.tsv" \n
    to map the signal to existing signal. \n
    3. Running The suitable processing unit from CODE_DIR/signal_processings/$SIGNAL_NAME_OR_PROCESSING_UNIT_NAME_OR_TAG.py \n
    The most specific code will be called. There is a logic like class inheritance. \n
    If my signal is Hemoglobin, it is also tagged and "cbc" and "labs".\n
    It will first look for "Hemoglobin.py", then "cbc.py" and then "labs.py". \n
    If the code file is missing/directory doesn't exist - the code will create the directory and a file with instructions \n
    The signal will be determined by "signal" column if not Null, otherwise it will use the "sigs" parameter. \n
    4. Testing the result dataframe - first signal format testing, time channel is integer and in valid dates, value is numeric \n
    Categorical values doens't contains invalid characters, etc. Then deeper tests that can be expended based on the signal labels \n
    Will be executes, like testing the value range. \n
    5. Sorting, and storing the file in the right place under - WORK_DIR/FinalSignals \n

    :param data: A lazy iterator of DataFrame, the only constraint is to have "pid" column. To use this iterator, we need to specify 2
     integers - batch size and starting batch position.
    :param workdir: The working directory where we stored all the ETL outputs
    :param sigs: comma separeted names of logic units to execute on each DataFrame on records without "signal" value
    :param batch_size: A parameter to control batch size of the lazy iterator to pass to it
    :param start_write_batch: If multiple data sources wants to generate the same "signal" we wants to avoid override in
     FinalSignals. This is our way tp handle this. To give each call od prepare_final_signals a different "batch" number
     for writing the output
    :param skip_batch_tests: This controls if to skip tests in between batches
    :param override: If "y" will redo again and will not take into account current status. The default is "n" - no.
     To use current state, and to skip completed batches or skip all this processing if all batches are completed.

    :return: True is finished succesfully.
    """
    data_fetcher = data
    if isinstance(data, pd.DataFrame):

        def fetch_signal_single(
            batch_size: int, start_batch: int
        ) -> Generator[pd.DataFrame, None, None]:
            """
            A generator to yield the data in single batches - wrapper for the DataFrame input.
            """
            yield data

        data_fetcher = fetch_signal_single

    succ = map_fetch_and_process(
        data_fetcher,
        workdir,
        sigs,
        batch_size,
        start_write_batch,
        skip_batch_tests,
        editor,
        map_editor,
        override,
        interactive,
    )
    if not (succ):
        raise NameError(f"Failed in prepare_final_signal for {sigs}")
    return succ


def prepare_dicts(
    workdir: str,
    signal: str,
    def_dict: Optional[pd.DataFrame] = None,
    set_dict: Optional[pd.DataFrame] = None,
    add_missing_codes: bool = True,
) -> None:
    """
    Main for preparing dicts - workdir, signal, 2 additional argument to add cusom client dicts for this signal

    :param workdir: The working directory where we stored all the ETL outputs
    :param signal: The name of the signal or several signals with comma seperated
    :param def_dict: Optional DataFrame with 2 columns, the first column is the internal code and the value we used in the
     loading files. The second column is the description of this code that we will be able to see it next to the internla code
     or query the code by the description
    :param set_dict: Optional if we have sets inside the client dictionary.
    :param add_missing_codes: If true will try to "trim" long codes to shorter ones and search for matching

    :todo: change signal to List
    """
    sig_types = read_signals_defs()
    signal_ls = signal.split(",")
    all_df = []
    for sig_n in signal_ls:
        df = load_categ_sig(workdir, sig_types, sig_n)
        all_df.append(df)
    df = pd.concat(all_df, ignore_index=True)
    if def_dict is not None:
        generate_dict_from_codes(def_dict, workdir, sig_types, signal, df, set_dict)
    if set_dict is not None:
        add_hirarchy(set_dict, workdir, signal)

    process_dicts(df, sig_types, signal, workdir, set_dict, add_missing_codes)


def finish_prepare_load(
    workdir: str,
    dest_folder: str,
    dest_rep: str,
    to_remove: List[str] = [],
    load_only: List[str] = [],
    override: bool = False,
) -> None:
    """
    Finalize and prepare Flow load command to execute to complete the load

    :param workdir: The working directory where we stored all the ETL outputs
    :param dest_folder: The path to create the final repository. A Directory
    :param dest_rep: The name of the repository, to contorl the name of NAME.repository file
    :param to_remove: optional list of signals to skip from loading
    :param load_only: optional list of signals to load only if exist
    :param override: If true will override all process
    """

    os.makedirs(os.path.join(workdir, "rep_configs"), exist_ok=True)
    codedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    signal_types = read_signals_defs()
    finish_prepare_dicts(workdir, signal_types, override=override)
    generate_signals_file(codedir, workdir, dest_rep)
    create_convert_config_file(workdir, dest_folder, dest_rep, to_remove, load_only)
    # Generate Flow command
    generate_flow_script(workdir, dest_folder, dest_rep)


def create_train_signal(work_dir: str, old_train_path:pd.DataFrame|None=None):
    """_summary_

    Args:
        work_dir (str): Working directory where the FinalSignals are stored.
        old_train_path (pd.DataFrame | None, optional): if given a dataframe with "pid" and "val" of old train value. Defaults to None.
    """
    sig = "TRAIN"
    signals_dir = os.path.join(work_dir, "FinalSignals")
    bdate_files = list(
        filter(
            lambda x: x.startswith("BDATE.") or x == "BDATE", os.listdir(signals_dir)
        )
    )
    all_pd = []
    for f in bdate_files:
        all_pd.append(
            pd.read_csv(
                os.path.join(signals_dir, f),
                sep="\t",
                names=["pid", "signal", "value_0"],
                usecols=[0, 1, 2],
            )
        )
    if len(all_pd) == 1:
        all_pd = all_pd[0]
    else:
        all_pd = pd.concat(all_pd, ignore_index=True)

    tr_df = pd.DataFrame({"pid": [], "val": []})
    if old_train_path is not None:
        for old_train_p in old_train_path:
            tr_df_tmp = pd.read_csv(
                old_train_p,
                sep="\t",
                usecols=[0, 2],
                names=["pid", "val"],
                dtype={"pid": int, "val": int},
            )
            tr_df = tr_df_tmp
    old_ids = tr_df["pid"].unique()

    cur_ids = all_pd["pid"].unique()

    not_in_cur = list(
        set(old_ids) - set(cur_ids)
    )  # not need to load - not used anymore
    only_in_new = list(set(cur_ids) - set(old_ids))
    in_both = list(set(cur_ids) & set(old_ids))

    per70 = int(len(only_in_new) * 0.7)
    per20 = int(len(only_in_new) * 0.2)

    list1 = np.random.choice(only_in_new, per70, replace=False)
    df1 = pd.DataFrame(list1)
    df1["val"] = 1

    remain = list(set(only_in_new) - set(list1))
    list2 = np.random.choice(remain, per20, replace=False)
    df2 = pd.DataFrame(list2)
    df2["val"] = 2

    remain2 = list(set(remain) - set(list2))
    df3 = pd.DataFrame(remain2)
    df3["val"] = 3

    new_df = pd.concat([df1, df2, df3], ignore_index=True)
    new_df.rename({0: "pid"}, inplace=True, axis=1)

    tr_df = tr_df[tr_df["pid"].isin(in_both)]
    tr_df = pd.concat([tr_df, new_df], ignore_index=True)

    tr_df["signal"] = sig
    tr_df["pid"] = tr_df["pid"].astype(int)
    tr_df["val"] = tr_df["val"].astype(int)
    if os.path.exists(os.path.join(signals_dir, sig)):
        print("Override exisinting Train")
        os.remove(os.path.join(signals_dir, sig))
    tr_df = tr_df[["pid", "signal", "val"]].sort_values(by="pid").reset_index(drop=True)
    tr_df.to_csv(
        os.path.join(signals_dir, sig),
        sep="\t",
        index=False,
        header=False,
    )
    print("Created Train signal with %d records" % (len(tr_df)), flush=True)


# TODO:
# 1. parallel code
# 2. numeric test - resolution
# 8. Allow skip signals, summary report

# Example usage
if __name__ == "__main__":
    # Configure workdir
    WORK_DIR = "/nas1/Work/Users/Alon/ETL/demo"
    # Read data
    df = pd.DataFrame(
        {
            "pid": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "signal": ["Hemoglobin"] * 11,
            "time_0": [2012] * 11,
            "valu_0": [12] * 11,
        }
    )
    df2 = pd.DataFrame(
        {
            "pid": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "signal": ["MCV"] * 11,
            "time_0": [2012] * 11,
            "valu_0": [12] * 11,
        }
    )
    df = pd.concat([df, df2], ignore_index=True)

    # Process, iterate over all signals in dataframe, or call one-by-one
    prepare_final_signals(
        df, WORK_DIR, "labs", editor="/home/apps/thonny/bin/thonny", override="n"
    )
