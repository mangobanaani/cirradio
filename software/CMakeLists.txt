cmake_minimum_required(VERSION 3.20)
project(cirradio VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(CIRRADIO_BUILD_TESTS "Build tests" ON)
option(CIRRADIO_SIMULATE "Build with simulated HAL" ON)

find_package(Threads REQUIRED)
find_package(spdlog REQUIRED)
cmake_policy(SET CMP0167 NEW)
find_package(Boost REQUIRED)
find_package(OpenSSL REQUIRED)

add_subdirectory(src)

if(CIRRADIO_BUILD_TESTS)
    enable_testing()
    find_package(Catch2 3 REQUIRED)
    add_subdirectory(tests)
endif()
