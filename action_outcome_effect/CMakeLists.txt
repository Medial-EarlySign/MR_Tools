cmake_minimum_required(VERSION 3.5)
project(action_outcome_effect)

set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/Linux/${CMAKE_BUILD_TYPE}")

#set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} --std=c++11 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -Ofast -g")
#set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} --std=c++11 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -Ofast -pg")
set(CMAKE_CXX_FLAGS   "${CMAKE_CXX_FLAGS} --std=c++11 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -Ofast -fomit-frame-pointer")

# Build with older GlibC
include_directories(SYSTEM /nas1/Work/Libs/Glibc_ubuntu_22.04/include)
include_directories(SYSTEM /nas1/Work/Libs/Glibc_ubuntu_22.04/include/x86_64-linux-gnu)
add_link_options( -L/nas1/Work/Libs/Glibc_ubuntu_22.04)
# End Old glibc

include_directories($ENV{MR_ROOT}/Libs)
include_directories($ENV{MR_ROOT}/Libs/External)
include_directories($ENV{MR_ROOT}/Libs/Internal)
include_directories($ENV{R_INCL_DIR})
include_directories(${PROJECT_SOURCE_DIR})
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/src)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/include)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/rabit/include)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/dmlc-core/include)
include_directories($ENV{MR_ROOT}/Libs/External/LightGBM/LightGBM/include)

# Add Internal libraries
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedPlotly/MedPlotly MedPlotly)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/InfraMed/InfraMed InfraMed)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/Logger/Logger Logger)
add_subdirectory($ENV{MR_ROOT}/Libs/External/Mars/Mars Mars)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedAlgo/MedAlgo MedAlgo)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedEmbed/MedEmbed MedEmbed)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedIO/MedIO MedIO)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedMat/MedMat MedMat)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedProcessTools/MedProcessTools MedProcessTools)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedSparseMat/MedSparseMat MedSparseMat)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedSplit/MedSplit MedSplit)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedStat/MedStat MedStat)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedTime/MedTime MedTime)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/MedUtils/MedUtils MedUtils)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/QRF/QRF QRF)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/SerializableObject/SerializableObject SerializableObject)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/TQRF/TQRF TQRF)
add_subdirectory($ENV{MR_ROOT}/Libs/Internal/micNet/micNet micNet)

add_subdirectory(action_outcome_effect)
add_subdirectory(build_treat_effect_data)

