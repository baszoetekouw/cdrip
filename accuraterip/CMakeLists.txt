cmake_minimum_required(VERSION 3.15)
project(accuraterip C)

set(CMAKE_C_STANDARD 11)
include_directories(. /opt/brew/include)
link_directories(/opt/brew/lib)

add_executable(accuraterip
        accuraterip.c
        accuraterip.h
        cmdline.c main.c util.c file.c)
target_link_libraries(accuraterip sndfile)
