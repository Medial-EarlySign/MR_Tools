cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(create_registry ${SRC_FILES})
add_linking_flags(create_registry)
