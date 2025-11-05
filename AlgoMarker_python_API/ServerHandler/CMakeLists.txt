cmake_minimum_required(VERSION 3.5.0)
project(AlgoMarker_Server VERSION 1.0.0 LANGUAGES C CXX)
cmake_policy(SET CMP0074 NEW)
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.27")
    cmake_policy(SET CMP0144 NEW)
endif()

if(DEFINED ENV{BOOST_ROOT})
    message(STATUS "BOOST_ROOT is set to: $ENV{BOOST_ROOT}")
    set(BOOST_ROOT "$ENV{BOOST_ROOT}")
else()
    message(STATUS "BOOST_ROOT environment variable is not set. Please set it to the Boost installation path.")
    # set(BOOST_ROOT "$ENV{HOME}/Documents/MES/Boost") #If you have compiled boost by yourself with -fPIC flag, please provide the path to folder with "/lib" with shared and static lib and "/include" for headers.
endif()

set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/Linux/${CMAKE_BUILD_TYPE}")

set(SRC_FILES 
utils.h
AlgoMarker.h
CMD_Args.h
utils.cpp
main.cpp)

set(BOOST_LIBS
    regex
    filesystem
    system
    program_options
)  # for certain version, you might need to add "atomic" also, in some other cases remove system

find_package(Boost REQUIRED)
if(Boost_VERSION VERSION_GREATER_EQUAL "1.69") # 1.69 is represented as 106900 in CMake
    # Remove "system" for newer versions (>= 1.69)
    # The list(REMOVE_ITEM) command is used to remove a specific item from a list variable.
    list(REMOVE_ITEM BOOST_LIBS "system")
    message(STATUS "Boost version is ${Boost_VERSION} (>= 1.69), removing 'system' from BOOST_LIBS.")
else()
    message(STATUS "Boost version is ${Boost_VERSION} (< 1.69), keeping 'system' in BOOST_LIBS.")
endif()

set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"' -Wall -Wno-unused-function -Wno-unknown-pragmas -Wno-comment -Wno-sign-compare -Wno-reorder -Wunused-variable -Wformat -Wparentheses -Wmissing-braces -Wreturn-type -Werror=return-type --std=c++17 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -Ofast -fomit-frame-pointer")
#set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"' -Wall -Wno-unused-function -Wno-unknown-pragmas -Wno-comment -Wno-sign-compare -Wno-reorder -Wunused-variable -Wformat -Wparentheses -Wmissing-braces -Wreturn-type -Werror=return-type --std=c++17 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -ldl -Ofast -g")

# Find Boost
find_package(OpenMP REQUIRED)

find_package(Boost REQUIRED COMPONENTS ${BOOST_LIBS})  # Example components
if (BOOST_ROOT)
    set(Boost_INCLUDE_DIRS "${BOOST_ROOT}/include")
endif()

include_directories(${Boost_INCLUDE_DIRS})

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


add_executable(AlgoMarker_Server ${SRC_FILES})

IF (WIN32)
    message("IN WINDOWS!!")
    set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -fpermissive")
    target_include_directories(AlgoMarker_Server SYSTEM PRIVATE $ENV{BOOST_HOME} )
    target_link_libraries(AlgoMarker_Server ${ADDITIONAL_LINK_FLAGS} -Wl,-Bstatic,--whole-archive -LC:/Boost/boost_1_67_0/stage/lib
    -lboost_regex-mgw132-mt-x64-1_67  -lboost_program_options-mgw132-mt-x64-1_67
     -lboost_filesystem-mgw132-mt-x64-1_67 -lboost_system-mgw132-mt-x64-1_67 -Wl,-no-whole-archive -Wl,-Bdynamic -lwsock32
      )
      target_link_libraries(AlgoMarker_Server ws2_32)
ELSE()

    set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -ldl")
    # target_include_directories Not needed in linux - Boost Already in CPATH Environment 
    target_link_libraries(AlgoMarker_Server ${ADDITIONAL_LINK_FLAGS} -Wl,-Bstatic,--whole-archive ${BOOST_STATIC_LIB_PATHS} -Wl,-no-whole-archive -Wl,-Bdynamic)
ENDIF()


