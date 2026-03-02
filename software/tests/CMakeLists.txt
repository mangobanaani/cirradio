add_executable(cirradio_tests
    test_main.cpp
    test_hal_interfaces.cpp
)
target_link_libraries(cirradio_tests PRIVATE Catch2::Catch2WithMain)
target_include_directories(cirradio_tests PRIVATE ${CMAKE_SOURCE_DIR}/src)
include(Catch)
catch_discover_tests(cirradio_tests)
