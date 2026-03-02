add_executable(cirradio main.cpp)
target_link_libraries(cirradio PRIVATE
    spdlog::spdlog
    Boost::boost
    OpenSSL::SSL
    OpenSSL::Crypto
    Threads::Threads
)
target_include_directories(cirradio PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
