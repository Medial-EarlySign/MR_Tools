cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(learn_from_matrix ${SRC_FILES})
add_linking_flags(learn_from_matrix)
