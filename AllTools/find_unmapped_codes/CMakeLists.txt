cmake_minimum_required(VERSION 3.5.0)
file(GLOB SRC_FILES
     "*.h"
     "*.cpp"
)

add_executable(find_unmapped_codes ${SRC_FILES})
add_linking_flags(find_unmapped_codes)
