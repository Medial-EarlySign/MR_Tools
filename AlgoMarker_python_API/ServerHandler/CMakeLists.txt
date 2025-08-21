cmake_minimum_required(VERSION 3.5.0)
project(AlgoMarker_Server VERSION 1.0.0 LANGUAGES C CXX)

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
) # for certain version, you might need to add "atomic" also

#set(BOOST_ROOT "$ENV{HOME}/boost-pic-install") #If you have compiled boost by yourself with -fPIC flag, please provide the path to folder with "/lib" with shared and static lib and "/include" for headers.

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


