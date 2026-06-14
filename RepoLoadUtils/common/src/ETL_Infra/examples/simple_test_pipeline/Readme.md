## Readme

This ETL pipeline is designed to process output files from external suppliers, integrating them into our ETL system for testing and final formatting.

## Assumptions

- Input files are plain text.
- All output files are located in a single directory (this can be changed if needed).
- Files are tab-delimited, include headers, and must contain both "pid" and "signal" columns. Missing columns will result in an error.

## Test Workflow (for each signal):

1. Ensure the signal is recognized and listed in our signals list. If not, update the signal name or add a new type (instruction will be given in the error).
2. Check the file structure: verify the number of time channels, expected value channels, and that time channel dates are valid.
3. Validate lab values: confirm values are within expected ranges and compare data across ETL sources for consistency.
4. Format the final output: sort by patient ID and time, generate data dictionaries for categorical signals, and retrieve relevant ontologies when possible. For example, if values use the "ICD10_CODE:" prefix, the complete ICD10 ontology hierarchy will be retrieved. If "ICD9_CODE:" is used, both the ICD9 ontology and a mapping to ICD10 will be included.
5. Create the final configuration file for loading into the `Flow` ETL.

## Getting Started

**In `parser.py`:**

1. Set `BASE_PATH` to the directory containing your output files.
2. Modify `read_single_file` to parse files into DataFrames if the format is more complex than `pd.read_csv`. For files too large to fit in memory, update `big_file_parser_lazy` for file parsing that will be used by `big_data_fetcher` (no need to edit `big_data_fetcher`).

**In `load.py`:**

1. Set `WORK_DIR` as the working directory for processing and test outputs.
2. Set `FINAL_REP_PATH` as the destination for the final repository.
3. Update `prepare_final_signals` as needed, duplicating lines for different file formats. Use the appropriate regex with `generic_file_fetcher` or `big_data_fetcher` (for large files), and assign a name for each file group in the third argument. For example:
```python
# To process all files starting with "demo" as a single "demographic" batch, set batch_size = 0. batch)size = 1 will process the files one by one.
prepare_final_signals(generic_file_fetcher("demo.*"), WORK_DIR, "demographic", batch_size=0, override="n")

# To process files starting with "lab" as "labs" using the big file fetcher (for files too large for memory), chunking data into batches of 1 million lines:
prepare_final_signals(big_data_fetcher("lab.*"), WORK_DIR, "labs", batch_size=1e6, override="n")
```
4. Run `load.py`
