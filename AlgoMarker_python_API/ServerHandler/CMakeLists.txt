cmake_minimum_required(VERSION 3.5.0)
project(AlgoMarker_Server VERSION 1.0.0 LANGUAGES C CXX)
cmake_policy(SET CMP0074 NEW)
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.27")
    cmake_policy(SET CMP0144 NEW)
endif()


if(DEFINED ENV{BOOST_ROOT})
    message(STATUS "BOOST_ROOT is set to: $ENV{BOOST_ROOT}")
    set(BOOST_ROOT "$ENV{BOOST_ROOT}")
    set(Boost_INCLUDE_DIRS "${BOOST_ROOT}/include")
    include_directories(SYSTEM ${Boost_INCLUDE_DIRS})
else()
    find_package(Boost QUIET)
    if (NOT Boost_FOUND)
        message(STATUS "BOOST_ROOT environment variable is not set. Please set it to the Boost installation path, if you want to use a specific boost.")
        message(STATUS "Boost not found. Downloading headers...")
        include(FetchContent)
        FetchContent_Declare(
            boost_headers
                URL      https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.gz
                SOURCE_SUBDIR pathThatDoesNotExist
                DOWNLOAD_EXTRACT_TIMESTAMP ON
            )
            
            FetchContent_GetProperties(boost_headers)
            if(NOT boost_headers_POPULATED)
                FetchContent_MakeAvailable(boost_headers)
            endif()

            include_directories(${boost_headers_SOURCE_DIR})
    endif()
endif()

set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/Linux/${CMAKE_BUILD_TYPE}")

set(SRC_FILES 
utils.h
AlgoMarker.h
CMD_Args.h
utils.cpp
main.cpp)

set(BOOST_LIBS
    system
    program_options
)

set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"' -Wall -Wno-unused-function -Wno-unknown-pragmas -Wno-comment -Wno-sign-compare -Wno-reorder -Wunused-variable -Wformat -Wparentheses -Wmissing-braces -Wreturn-type -Werror=return-type --std=c++17 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -Ofast -fomit-frame-pointer")
#set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DGIT_HEAD_VERSION='\"'$(GIT_HEAD_VERSION)'\"' -Wall -Wno-unused-function -Wno-unknown-pragmas -Wno-comment -Wno-sign-compare -Wno-reorder -Wunused-variable -Wformat -Wparentheses -Wmissing-braces -Wreturn-type -Werror=return-type --std=c++17 -Wno-write-strings -Wuninitialized -fopenmp -msse2 -msse3 -msse4 -march=native --param inline-unit-growth=1000000 -ldl -Ofast -g")

# Find Boost
find_package(OpenMP REQUIRED)
add_executable(AlgoMarker_Server ${SRC_FILES})

IF (WIN32)
    message("IN WINDOWS!!")
    set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -fpermissive")
    target_include_directories(AlgoMarker_Server SYSTEM PRIVATE $ENV{BOOST_HOME} )
    target_link_libraries(AlgoMarker_Server ${ADDITIONAL_LINK_FLAGS} -Wl,-Bstatic,--whole-archive -LC:/Boost/boost_1_67_0/stage/lib
      -lboost_program_options-mgw132-mt-x64-1_67 -Wl,-no-whole-archive -Wl,-Bdynamic -lwsock32
      )
      target_link_libraries(AlgoMarker_Server ws2_32)
ELSE()

    set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -ldl")
    # target_include_directories Not needed in linux - Boost Already in CPATH Environment 
    target_link_libraries(AlgoMarker_Server ${ADDITIONAL_LINK_FLAGS} -Wl,-Bstatic,--whole-archive ${BOOST_STATIC_LIB_PATHS} -Wl,-no-whole-archive -Wl,-Bdynamic)
ENDIF()


