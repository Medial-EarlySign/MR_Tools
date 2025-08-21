import pandas as pd
import os, re
from typing import List, Generator, Callable

# Please use to return function that accepts 2 arguments: [batch_size, start_batch] in order to use in "prepare_final_signals"


# basic data fetcher - the batch will be by batches
# files - list of full paths
# batch_size - batch size in rows/files/your decision. 0 - means read all
# file_parser - function that recieve (file_path) and returns parsed dataframe
def files_fetcher(
    files: List[str],
    batch_size: int,
    file_parser: Callable[[str], pd.DataFrame],
    start_batch: int = 0,
) -> Generator[pd.DataFrame, None, None]:
    """
    A helper function to create data generator from list of files. \n
    The batching is done in the level of each file.\n
    So "1" means process each file in separate batch, 0 - no batches

    :param files: list of file paths to process
    :param batch_size: the batch size in number of files to process
    :param file_parser: a function to "read" each file path into dataframe with at least "pid" column
    :param start_batch: Staring position of the batch

    :return: a lazy data generator to fetch the Dataframes
    """
    all_data = None
    curr_data = []
    for full_f in files[start_batch * batch_size :]:
        print("Process file %s" % (full_f), flush=True)
        data = file_parser(full_f)
        curr_data.append(data)
        print("Done reading")
        if (batch_size > 0) and (len(curr_data) >= batch_size):
            data = pd.concat(curr_data, ignore_index=True)
            curr_data = []
            yield data
    if len(curr_data) > 0:
        data = pd.concat(curr_data, ignore_index=True)
        yield data


def big_files_fetcher(
    files: List[str],
    batch_size: int,
    file_parser: Callable[[str, int, int], Generator[pd.DataFrame, None, None]],
    has_header: bool = True,
    start_batch: int = 0,
) -> Generator[pd.DataFrame, None, None]:
    """
    A helper function to create data generator from list of big files. \n
    The batching is done in the level of #rows. So "1" means process 1 row, 0 - no batches, read all \n
    It will read several files till it reaches "batch_size" or part of 1 \n
    file if the file is bigger than "batch_size"

    :param files: list of file paths to process
    :param batch_size: the batch size in number of rows to process
    :param file_parser: a function to "read" each file path into dataframe with at least "pid" column
     The function recieves file path, number of lines to read from (batch_size) the file and how many lines to skip from file (start_from) 
     usefull when we want to continue run from the middle in big file. Example reading with pandas:
     df_i=pd.read_csv($FILE_PATH, skiprows=start_from_row, chunksize=batch_size)
    :param has_header: A flag to indicate if file contains header
    :param start_batch: Staring position of the batch

    :return: a lazy data generator to fetch the Dataframes
    """
    all_data = None
    curr_data = []
    curr_size = 0
    start_from_row = start_batch * batch_size
    for full_f in files:
        print("Process file %s" % (full_f), flush=True)
        try:
            data_it = file_parser(full_f, batch_size, start_from_row)
        except pd.errors.EmptyDataError:
            with open(full_f, "rbU") as f:
                num_lines = sum(1 for _ in f)
            if has_header:
                num_lines = num_lines - 1  # remove header from count
            start_from_row = start_from_row - num_lines
            if start_from_row < 0:  # not suppose to happen
                start_from_row = 0
            # Update start_from_row by rows size and continue
            continue
        for ii, data in enumerate(data_it):
            curr_data.append(data)
            curr_size += len(data)
            print(
                f"Done reading batch {ii} in file {full_f}, current buffer size {curr_size}"
            )
            if (batch_size > 0) and (curr_size >= batch_size):
                data = pd.concat(curr_data, ignore_index=True)
                curr_data = []
                curr_size = 0
                yield data
        print(f"Done processing file {full_f}")
    if len(curr_data) > 0:
        data = pd.concat(curr_data, ignore_index=True)
        yield data


def list_directory_files(base_path: str, file_search: str) -> List[str]:
    """
    A helper function to list all files in directory that matches a certain regex

    :param base_path: the directory path
    :param file_search: the regex to search in the directory
    :return: list of files matches the regex
    """
    reg_se = re.compile(file_search)
    files = list(filter(lambda x: len(reg_se.findall(x)) > 0, os.listdir(base_path)))
    files = sorted(files)
    files = list(map(lambda x: os.path.join(base_path, x), files))
    return files


# TODO: when single file is big - split to batches not needed currently
