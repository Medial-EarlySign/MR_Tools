cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(findRequiredSignals ${SRC_FILES})
add_linking_flags(findRequiredSignals)
