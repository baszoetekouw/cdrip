cmake_minimum_required(VERSION 3.15)
project(cd_info C)

set(CMAKE_C_STANDARD 11)

include_directories(. /opt/brew/include)
link_directories(/opt/brew/lib)


add_executable(cd-info
        cd-info.c)
target_link_libraries(cd-info cdio)
