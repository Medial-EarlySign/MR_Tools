cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(bootstrap_app ${SRC_FILES})
add_linking_flags(bootstrap_app)
