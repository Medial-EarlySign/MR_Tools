cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(cross_files ${SRC_FILES})
add_linking_flags(cross_files)
