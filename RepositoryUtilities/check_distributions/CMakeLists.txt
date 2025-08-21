cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(check_distributions ${SRC_FILES})
add_linking_flags(check_distributions)
