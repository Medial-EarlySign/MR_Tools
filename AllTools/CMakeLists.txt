cmake_minimum_required(VERSION 3.14)
project(Test VERSION 1.0 LANGUAGES CXX)

set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/Linux/${CMAKE_BUILD_TYPE}")

SET(LIBS_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../MR_LIBS") #Path to libs

#set(BOOST_ROOT "$ENV{HOME}/boost-pic-install") #If you have compiled boost by yourself with -fPIC flag, please provide the path to folder with "/lib" with shared and static lib and "/include" for headers.

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp -Wall -Wno-write-strings -Wno-sign-compare -Wno-reorder -Wno-unknown-pragmas -Wno-unused-function -ldl  --param inline-unit-growth=1000000 -msse4 -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"'")

set(BOOST_LIBS
    regex
    filesystem
    system
    program_options
) # for certain version, you might need to add "atomic" also

set (MEDIAL_INTERNAL_LIBS InfraMed Logger MedAlgo MedEmbed MedIO MedMat MedPlotly MedProcessTools MedSparseMat MedSplit MedStat MedTime MedUtils QRF SerializableObject TQRF micNet CommonLib
) #CommonLib if needed

# Dynamic linking
function(add_linking_flags TARGET_NAME)
    set(BUILD_STATIC_LIB OFF CACHE BOOL "Build XGBoost as a dynamic library" FORCE)
    target_link_libraries(${TARGET_NAME} ${ADDITIONAL_LINK_FLAGS} -Wl,--start-group ${MEDIAL_INTERNAL_LIBS} xgboost _lightgbm  -Wl,--end-group  ${Boost_LIBRARIES} )
endfunction()

#Static linking
function(add_linking_flags_static TARGET_NAME)
    set(BOOST_STATIC_LIB_PATHS "")
    foreach(lib IN LISTS BOOST_LIBS)
	string(TOUPPER "${lib}" LIB_VAR)
        if (NOT BOOST_ROOT)
            find_library(BOOST_${LIB_VAR}_STATIC
                NAMES "libboost_${lib}.a"
            )
        else()
            set(BOOST_${LIB_VAR}_STATIC ${BOOST_ROOT}/lib/libboost_${lib}.a)
        endif()

        if(NOT BOOST_${LIB_VAR}_STATIC)
            message(FATAL_ERROR "Could not find static Boost library: boost_${lib}.a")
        endif()

        list(APPEND BOOST_STATIC_LIB_PATHS ${BOOST_${LIB_VAR}_STATIC})
    endforeach()

    set(BUILD_STATIC_LIB ON CACHE BOOL "Build XGBoost as a static library" FORCE)
    target_link_libraries(${TARGET_NAME} ${ADDITIONAL_LINK_FLAGS} -Bstatic,--whole-archive ${MEDIAL_INTERNAL_LIBS} xgboost _lightgbm_static ${BOOST_STATIC_LIB_PATHS} -Wl,-no-whole-archive -Wl,-Bdynamic)

endfunction()

include_directories(${LIBS_PATH})
include_directories(${LIBS_PATH}/External)
include_directories(${LIBS_PATH}/Internal)
include_directories(${PROJECT_SOURCE_DIR})
include_directories(${LIBS_PATH}/External/xgboost/src)
include_directories(${LIBS_PATH}/External/xgboost/include)
include_directories(${LIBS_PATH}/External/xgboost/rabit/include)
include_directories(${LIBS_PATH}/External/xgboost/dmlc-core/include)
include_directories(${LIBS_PATH}/External/LightGBM_2.2.3/LightGBM-2.2.3/include)

# Find Boost
find_package(OpenMP REQUIRED)

find_package(Boost REQUIRED COMPONENTS ${BOOST_LIBS})  # Example components
if (BOOST_ROOT)
    set(Boost_INCLUDE_DIRS "${BOOST_ROOT}/include")
endif()

include_directories(${Boost_INCLUDE_DIRS})
# Add Internal libraries
foreach(mes_lib IN LISTS MEDIAL_INTERNAL_LIBS)
    add_subdirectory(${LIBS_PATH}/Internal/${mes_lib}/${mes_lib} ${mes_lib})
endforeach()

# External Libraries
add_subdirectory(${LIBS_PATH}/External/xgboost xgboost)
add_subdirectory(${LIBS_PATH}/External/LightGBM_2.2.3/LightGBM-2.2.3 _lightgbm)


# Or add each project:
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../Flow/Flow Flow)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../RepoLoadUtils/text_file_processor/text_file_processor text_file_processor)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../action_outcome_effect/action_outcome_effect action_outcome_effect)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../action_outcome_effect/build_treat_effect_data build_treat_effect_data)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../bootstrap_app/bootstrap_app bootstrap_app)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/create_registry create_registry)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../model_runner/model_runner model_runner)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../SignalsDependencies/SignalsDependencies SignalsDependencies)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../CompareStatsFiles/CompareStatsFiles CompareStatsFiles)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../RepoLoadUtils/SignalPrinter SignalPrinter)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/adjust_model adjust_model)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../FilesUtils/search_codes search_codes)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../FilesUtils/PrintPreds PrintPreds)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/learn learn)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/predict predict)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/analyze_model analyze_model)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/apply_calibrator apply_calibrator)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/cv cv)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/cv_on_matrix cv_on_matrix)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/filter filter)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/findRequiredSignals findRequiredSignals)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/getMatrix getMatrix)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/getSamples getSamples)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/getStats getStats)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/iterativeSelector iterativeSelector)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/learn_calibrator learn_calibrator)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/Optimize_HyperParams Optimize_HyperParams)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/predict_on_matrix predict_on_matrix)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/printData printData)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/printObject printObject)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/prob_to_score prob_to_score)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/processMatrix processMatrix)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/processSamples processSamples)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../MedProcessUtils/shuffleMatrix shuffleMatrix)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../Tutorials/SimpleHttpServer SimpleHttpServer)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../Optimizer/Optimizer Optimizer)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../change_model change_model)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/TestCalibration TestCalibration)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/CreateExplainReport CreateExplainReport)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/TestModelExternal TestModelExternal)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/TimeRangeMerger TimeRangeMerger)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/FilterSamples FilterSamples)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/HJson_Prettfier HJson_Prettfier)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/PerformanceFromCalibration PerformanceFromCalibration)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/model_signals_importance model_signals_importance)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/find_unmapped_codes find_unmapped_codes)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../AllTools/count_signal_len count_signal_len)

add_custom_target(all_done ALL
    COMMAND ${CMAKE_COMMAND} -E echo "=== INFO ==="
    COMMAND ${CMAKE_COMMAND} -E echo "TO execute executables, please run:"
    COMMAND ${CMAKE_COMMAND} -E echo "export LD_LIBRARY_PATH=${Boost_LIBRARY_DIRS}"
    COMMAND ${CMAKE_COMMAND} -E echo "prior to running the executables."
    COMMAND ${CMAKE_COMMAND} -E echo "=== INFO ==="
)

# Make it depend on your real targets
add_dependencies(all_done Flow 
    text_file_processor
    action_outcome_effect
    build_treat_effect_data
    bootstrap_app
    create_registry
    model_runner
    SignalsDependencies
    CompareStatsFiles
    SignalPrinter
    adjust_model
    search_codes
    PrintPreds
    learn
    predict
    analyze_model
    apply_calibrator
    cv
    cv_on_matrix
    filter
    findRequiredSignals
    getMatrix
    getSamples
    getStats
    iterativeSelector
    learn_calibrator
    Optimize_HyperParams
    predict_on_matrix
    printData
    printObject
    prob_to_score
    processMatrix
    processSamples
    shuffleMatrix
    SimpleHttpServer 
    Optimizer 
    change_model 
    TestCalibration 
    CreateExplainReport 
    TestModelExternal 
    TimeRangeMerger 
    FilterSamples 
    HJson_Prettfier 
    PerformanceFromCalibration 
    model_signals_importance 
    find_unmapped_codes 
    count_signal_len)

# Inside each project:
#file(GLOB SRC_FILES
#     "*.h"
#     "*.cpp"
#)
#add_executable(Test ${SRC_FILES})
#add_linking_flags_dynamic(Test)
#add_linking_flags_static(Test)