#!/bin/bash
set -e
version_txt=$(date +'Build_On_%Y%m%d_%H:%M:%S')
touch ${0%/*}/../utils.h

rm ${0%/*}/build/ -fr
mkdir ${0%/*}/build
pushd ${0%/*}/build
cmake .. -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
make -j 3 -e GIT_HEAD_VERSION="$version_txt"
popd
CURR_PATH=$(realpath ${0%/*})
strip ${CURR_PATH}/Linux/Release/AlgoMarker_Server

echo "App can be found here: ${CURR_PATH}/Linux/Release/AlgoMarker_Server"

