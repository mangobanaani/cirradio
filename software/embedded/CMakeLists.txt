# software/embedded/CMakeLists.txt
# Cross-compilation for Zynq-7045 PS (Cortex-A9, ARMv7-A hard-float)
# Requires PetaLinux 2024.2 SDK:
#   source /opt/pkg/petalinux/2024.2/environment-setup-cortexa9t2hf-neon-xilinx-linux-gnueabi

cmake_minimum_required(VERSION 3.20)
project(cirradio_embedded CXX)
set(CMAKE_CXX_STANDARD 20)

if(NOT CMAKE_CROSSCOMPILING)
    message(FATAL_ERROR
        "This CMakeLists.txt is for cross-compilation only.\n"
        "Source the PetaLinux SDK environment first:\n"
        "  source /opt/pkg/petalinux/2024.2/environment-setup-cortexa9t2hf-neon-xilinx-linux-gnueabi\n"
        "Then configure with: cmake -DCMAKE_TOOLCHAIN_FILE=... ..")
endif()

add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../software/src src_phase1)

find_package(Python3 REQUIRED)
add_custom_target(check_regmap ALL
    COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/../../fpga/scripts/check_regmap.py
    COMMENT "Checking AXI register map sync between RTL and driver"
    VERBATIM
)

add_library(cirradio_hal_embedded STATIC
    drivers/axi_regs.cpp
    drivers/iio_radio.cpp
    drivers/gps_hal.cpp
    hal/zynq7045_hal.cpp
)
target_include_directories(cirradio_hal_embedded PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/drivers
    ${CMAKE_CURRENT_SOURCE_DIR}/hal
    ${CMAKE_CURRENT_SOURCE_DIR}/../../software/src
)
add_dependencies(cirradio_hal_embedded check_regmap)

find_library(LIBIIO iio REQUIRED)
find_library(LIBGPS gps REQUIRED)
target_link_libraries(cirradio_hal_embedded PUBLIC ${LIBIIO} ${LIBGPS})

add_executable(cirradio_app
    ${CMAKE_CURRENT_SOURCE_DIR}/../../software/src/main.cpp
)
target_link_libraries(cirradio_app PRIVATE cirradio_hal_embedded)
