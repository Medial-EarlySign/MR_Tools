cmake_minimum_required(VERSION 2.8)

set(H_FILES 
	printModel.h
)
			
set(SRC_FILES
	printModel.cpp
)

add_executable(printModel ${H_FILES} ${SRC_FILES})
target_link_libraries(printModel -Wl,--start-group CommonLib InfraMed Logger Mars MedAlgo MedFeat MedProcessTools MedStat MedTime MedUtils QRF TQRF gbm micNet -Wl,--end-group libboost_regex.so libboost_program_options.so libboost_filesystem.so libboost_system.so /server/Work/SharedLibs/linux/lib64/${CMAKE_BUILD_TYPE}/libxgboost.so /server/Work/SharedLibs/linux/lib64/${CMAKE_BUILD_TYPE}/lib_lightgbm.so)


#include("$ENV{MR_ROOT}/Projects/Resources/CMakeUtils/CMakePrintProperties.txt")
