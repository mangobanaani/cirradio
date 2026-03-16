find_package(PkgConfig REQUIRED)
pkg_check_modules(CODEC2 REQUIRED codec2)

add_library(cirradio_lib STATIC
    hal/SimChannel.cpp
    hal/SimRadioHal.cpp
    security/EcSign.cpp
    security/ZeroizeEngine.cpp
    security/TamperMonitor.cpp
    security/SecurityManager.cpp
    security/KeyFillPort.cpp
    security/KeyManager.cpp
    security/Pkcs11Hsm.cpp
    security/SoftHsm.cpp
    fhss/HopSequencer.cpp
    tdma/SlotScheduler.cpp
    core/ComponentManager.cpp
    core/PropertyService.cpp
    network/RouteTable.cpp
    network/MeshRouter.cpp
    network/NetJoin.cpp
    network/PeerDiscovery.cpp
    voice/VoiceCodec.cpp
    voice/JitterBuffer.cpp
    voice/SimAudioHal.cpp
    mgmt/CLIShell.cpp
    node/RadioNode.cpp
)
target_include_directories(cirradio_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CODEC2_INCLUDE_DIRS}
)
target_link_libraries(cirradio_lib PUBLIC
    spdlog::spdlog
    Boost::boost
    OpenSSL::SSL
    OpenSSL::Crypto
    Threads::Threads
    ${CODEC2_LIBRARIES}
)
target_link_directories(cirradio_lib PUBLIC ${CODEC2_LIBRARY_DIRS})

# SoftHSM2 — cross-platform PKCS#11 test shim
find_library(SOFTHSM2_LIB softhsm2
    PATHS /usr/lib/softhsm
          /usr/lib/x86_64-linux-gnu/softhsm
          /opt/homebrew/lib/softhsm
    NO_DEFAULT_PATH)
if(NOT SOFTHSM2_LIB)
    message(FATAL_ERROR "SoftHSM2 library not found. Install softhsm2 (apt/brew).")
endif()
target_compile_definitions(cirradio_lib PRIVATE
    SOFTHSM2_LIB_PATH="${SOFTHSM2_LIB}")

add_executable(cirradio main.cpp)
target_link_libraries(cirradio PRIVATE cirradio_lib)
