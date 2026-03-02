add_executable(cirradio_tests
    test_main.cpp
    test_hal_interfaces.cpp
    test_sim_radio.cpp
    test_crypto.cpp
)
target_link_libraries(cirradio_tests PRIVATE
    cirradio_lib
    Catch2::Catch2WithMain
)
include(Catch)
catch_discover_tests(cirradio_tests)
