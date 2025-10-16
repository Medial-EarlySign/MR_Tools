#!/bin/bash
set -e -o pipefail
source ${1}/env.sh
TEST_NAME_=${0##*/}
TEST_NAME=${TEST_NAME_%.*}
PROJECT_DIR_=${0%/*}
PROJECT_DIR__=${PROJECT_DIR_%/*}
PROJECT_DIR=${PROJECT_DIR__##*/}
OVERRIDE=${3-0}

for PARAM in ${REQ_PARAMS[@]}; do
	if [ -z "${!PARAM}" ]; then
		echo "${PARAM} is missing in enviroment - skipping test ${TEST_NAME}"
		exit 1
	fi
done
#Run deps
SPECIFIC_DIR=${1%/*}
if [ $SPECIFIC_DIR = ${PROJECT_DIR__} ]; then
    PROJECT_DIR=$(cat ${PROJECT_DIR__}/run.sh| grep "AUTOTEST_LIB" | awk '{print $2}')
fi

if [ ! -z "${DEPENDS}" ]; then
    for TEST_NUM in ${DEPENDS[@]}; do
        echo "Running dependent test ${TEST_NUM}"    
        . ${CURR_PT}/autotest.specific_test ${PROJECT_DIR} ${TEST_NUM} ${OVERRIDE} ${SPECIFIC_DIR}
    done
fi
