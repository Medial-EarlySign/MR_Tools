# AlgoMarker Scripts

## Overview

The `AlgoMarker_scripts/` directory provides shell scripts and configuration files for orchestrating model scoring, comparison, and testing workflows. These scripts are used to automate the process of running model validations and comparing results across different configurations.

## Main Scripts
- **create_score_compare.sh**: Runs model scoring and compares results
- **env.sh**: Sets up environment variables for validation workflows
- **full_test.sh**: Executes the full suite of tests
- **test_single.sh**: Runs a single test scenario

## Configurations
- **configs/**: Contains JSON and TSV files for signal definitions, regex filters, and renaming rules

## Usage Example
To run a full test:

```bash
cd AlgoMarker_scripts
bash full_test.sh
```

To run a single test:

```bash
bash test_single.sh <test_config>
```