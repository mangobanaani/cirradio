add_executable(cirradio_tests test_main.cpp)
target_link_libraries(cirradio_tests PRIVATE Catch2::Catch2WithMain)
include(Catch)
catch_discover_tests(cirradio_tests)
