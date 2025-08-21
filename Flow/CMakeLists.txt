cmake_minimum_required(VERSION 3.5)
project(Flow VERSION 1.1.0 LANGUAGES C CXX)
 
set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/Linux/${CMAKE_BUILD_TYPE}")
 
set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"' -Wall -Wno-unused-function -Wno-unknown-pragmas -Wno-comment -Wno-sign-compare -Wno-reorder -Wunused-variable -Wformat -Wparentheses -Wmissing-braces -Wreturn-type -Werror=return-type --std=c++17 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -ldl -Ofast -fomit-frame-pointer")
#for debug symbols add "-g" and remove "-fomit-frame-pointer"
 
function(add_linking_flags TARGET_NAME)
    # Apply linking flags
    target_link_libraries(${TARGET_NAME} ${ADDITIONAL_LINK_FLAGS}  -Wl,--start-group InfraMed Logger Mars MedAlgo MedEmbed MedIO MedMat MedPlotly MedProcessTools MedSparseMat MedSplit MedStat MedTime MedUtils QRF SerializableObject TQRF micNet -Wl,--end-group -L/nas1/Work/Libs/Boost/boost_1_85_0/installation/lib libboost_regex.so libboost_program_options.so libboost_filesystem.so libboost_system.so libboost_atomic.so /nas1/Work/SharedLibs/linux/ubuntu/${CMAKE_BUILD_TYPE}/libxgboost.so /nas1/Work/SharedLibs/linux/ubuntu/${CMAKE_BUILD_TYPE}/lib_lightgbm.so)
endfunction()

# Build with older GlibC
include_directories(SYSTEM /nas1/Work/Libs/Glibc_ubuntu_22.04/include)
include_directories(SYSTEM /nas1/Work/Libs/Glibc_ubuntu_22.04/include/x86_64-linux-gnu)
add_link_options( -L/nas1/Work/Libs/Glibc_ubuntu_22.04)
# End Old glibc

include_directories(SYSTEM /server/Work/Libs/Boost/boost_1_85_0)
include_directories($ENV{MR_ROOT}/Libs)
include_directories($ENV{MR_ROOT}/Libs/External)
include_directories($ENV{MR_ROOT}/Libs/Internal)
include_directories($ENV{MR_ROOT}/Libs/InternalOrig)
include_directories(${PROJECT_SOURCE_DIR})
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/src)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/include)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/rabit/include)
include_directories($ENV{MR_ROOT}/Libs/External/xgboost/dmlc-core/include)
include_directories($ENV{MR_ROOT}/Libs/External/LightGBM_2.2.3/LightGBM-2.2.3/include)
 
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

# Current project
add_subdirectory(${PROJECT_SOURCE_DIR}/Flow Flow)