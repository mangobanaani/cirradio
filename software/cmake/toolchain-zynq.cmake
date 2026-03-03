# Zynq ARM cross-compilation toolchain
# Requires Xilinx SDK / PetaLinux toolchain to be installed
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Set these to your Xilinx SDK paths
# set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
# set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)
# set(CMAKE_SYSROOT /opt/petalinux/sysroot)

message(STATUS "Zynq cross-compilation toolchain loaded (stub)")
