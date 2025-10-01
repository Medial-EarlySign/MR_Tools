# Test Kit Scripts

## Overview

The `test_kit/` directory contains entry-point scripts for running the main validation workflows. These scripts orchestrate the execution of test suites for different validation scenarios (Development, External Silent Run, External Validation After SR).

## Main Scripts
- **test_Development.sh**: Runs the development test suite
- **test_External_Silent_Run.sh**: Runs the silent run validation suite
- **test_External_validation_after_SR.sh**: Runs the validation suite after silent run
- **env.sh**: Sets up environment variables for test execution

## Usage Example
To run the development test suite:

```bash
cd test_kit
bash test_Development.sh
```