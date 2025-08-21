#!/bin/bash
if [[ SignalsDependencies/SignalsDependencies.cpp -nt Linux/Release/SignalsDependencies ]]; then
  echo Update Code, need to compile
  #smake_rel
  #pushd CMakeBuild/Linux/Release && make -j 8; popd
fi

pushd CMakeBuild/Linux/Release && make -j 8 && popd
Linux/Release/SignalsDependencies

