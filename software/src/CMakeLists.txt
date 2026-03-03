find_package(PkgConfig REQUIRED)
pkg_check_modules(CODEC2 REQUIRED codec2)

add_library(cirradio_lib STATIC
    hal/SimChannel.cpp
    hal/SimRadioHal.cpp
    security/CryptoEngine.cpp
    security/SoftCryptoHal.cpp
    security/KeyManager.cpp
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

add_executable(cirradio main.cpp)
target_link_libraries(cirradio PRIVATE cirradio_lib)
