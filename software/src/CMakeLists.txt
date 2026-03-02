add_library(cirradio_lib STATIC
    hal/SimChannel.cpp
    hal/SimRadioHal.cpp
)
target_include_directories(cirradio_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(cirradio_lib PUBLIC
    spdlog::spdlog
    Boost::boost
    OpenSSL::SSL
    OpenSSL::Crypto
    Threads::Threads
)

add_executable(cirradio main.cpp)
target_link_libraries(cirradio PRIVATE cirradio_lib)
