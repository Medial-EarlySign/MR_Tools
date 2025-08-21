cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(model_runner ${SRC_FILES})
add_linking_flags(model_runner)
