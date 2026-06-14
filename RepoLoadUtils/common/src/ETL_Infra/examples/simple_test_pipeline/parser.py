from typing import Callable, Generator
import pandas as pd
from ETL_Infra.data_fetcher.files_fetcher import (
    files_fetcher,
    list_directory_files,
    big_files_fetcher,
)

BASE_PATH = ""  # Define the base path where files are located


def list_files(file_prefix: str) -> list[str]:
    return list_directory_files(BASE_PATH, file_prefix)


def read_single_file(file_path: str) -> pd.DataFrame:
    """
    Reads a single file into a DataFrame.

    :param file_path: Path to the file to be read.
    :return: DataFrame containing the data from the file.
    """
    # Adjust the parameters as needed based on your file format
    return pd.read_csv(file_path, sep="\t", encoding="unicode_escape")


# This function is used in prepare_final_signals
def generic_file_fetcher(
    file_pattern: str,
) -> Callable[[int, int], Generator[pd.DataFrame, None, None]]:
    """
    Creates a file fetcher function that reads files matching the given pattern.

    :param file_pattern: Pattern to match files.
    :return: A function that fetches files in batches based on requested batch size, starting index.
    """
    file_fetcher_function = lambda batch_size, start_batch: files_fetcher(
        list_files(file_pattern),
        batch_size,
        read_single_file,
        start_batch,
    )
    return file_fetcher_function


###### If there are big files, we can use this function to fetch rows from files in batches:
def big_file_parser_lazy(
    filepath: str, batch_size: int, start_from_row: int
) -> Generator[pd.DataFrame, None, None]:
    """
    Parses a file in chunks, yielding DataFrames of specified batch size.

    :param filepath: Path to the file to be parsed.
    :param batch_size: Number of rows per batch.
    :param start_from_row: Row index to start reading from.
    :return: Generator yielding DataFrames.
    """
    # manipulate the file reading parameters as needed (keep chunksize and skiprows):
    has_header = True  # Set to False if the file has no header
    header = None
    if has_header and start_from_row > 0:
        header = pd.read_csv(filepath, sep="\t", nrows=0).columns.tolist()
        start_from_row += 1

    df_iterator = pd.read_csv(
        filepath,
        names=header,
        sep="\t",
        skiprows=start_from_row,
        chunksize=batch_size,
    )
    for df in df_iterator:
        # Do manipulations on df if needed
        yield df


def big_data_fetcher(
    file_pattern: str,
) -> Callable[[int, int], Generator[pd.DataFrame, None, None]]:
    """
    Creates a data fetcher function for large files, reading them in batches.
    Iterates over files matching the given pattern and processes them in chunks by reading rows.

    :param file_pattern: Pattern to match files.
    :return: A function that fetches files in batches based on requested batch size, starting index.
    batch_size controls the number of rows read from each file. When file ends, it will read the next file.
    """
    # Use the labs_file_parser_lazy to read files in chunks
    files = list_files(file_pattern)
    data_fetcher_function = lambda batch_size, start_batch: big_files_fetcher(
        files,
        batch_size,
        big_file_parser_lazy,
        has_header=True,
        start_batch=start_batch,
    )
    return data_fetcher_function


## Debugging and testing functions for the fetchers
if __name__ == "__main__":
    data = pd.DataFrame(
        {"pid": [1, 2, 3, 4, 5], "value": [1988, 1999, 2000, 2001, 2002]}
    )
    data["signal"] = "BYEAR"
    BASE_PATH = "/tmp"
    data.to_csv(f"{BASE_PATH}/res.tsv", sep="\t", index=False)
    func_fetcher = generic_file_fetcher("res.tsv")
    func_big_fetcher = big_data_fetcher("res.tsv")

    file_fetcher = func_fetcher(1, 0)
    file_fetcher_big = func_big_fetcher(2, 0) # Read 2 rows at a time
    # Example usage of the file fetchers
    print("generic_file_fetcher output:")
    for i, df in enumerate(file_fetcher):
        print(f"Batch {i}:\n{df}")
    print("-----------------------------------------------")
    print("Big file fetcher output:")
    for i, df in enumerate(file_fetcher_big):
        print(f"Batch {i}:\n{df}")
