#!/bin/bash
PY_GOOD=$(python -c "import sys; print(1 if sys.executable.find('python-env')>=0 else 0)")
if [ ${PY_GOOD} -lt 1 ]; then
	echo -e "Bad python `which python`\nPlease use 'python_env' to choose right python version, before running this"
	exit -1
fi

ALGOMARKER_NAME=LGI
TEST_REPOSITORY_PATH=/nas1/Work/Users/coby/LGI/Japan/outputs/Repository/japan.repository