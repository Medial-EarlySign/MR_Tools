#!/bin/bash
BLDDIR=$(realpath ${BASH_SOURCE[0]%/*})
pushd ${BLDDIR}
GIT_COMMIT_HASH=$(git rev-parse HEAD)
version_txt=$(date +'Commit_'${GIT_COMMIT_HASH}'_Build_On_%Y%m%d_%H:%M:%S')

mkdir -p ${BLDDIR}/build/Release
pushd ${BLDDIR}/build/Release
cmake -DCMAKE_BUILD_TYPE:STRING=Release -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE -S${BLDDIR} -B${BLDDIR}/build/Release -G "Unix Makefiles"

export GIT_HEAD_VERSION=$version_txt
cmake --build ${BLDDIR}/build/Release --config Release --target all -j $(nproc) --

popd 
popd