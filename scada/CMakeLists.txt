cmake_minimum_required(VERSION 3.16)

project(SmartMineScada VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Mqtt)

qt_standard_project_setup()

qt_add_executable(SmartMineScada
    src/main.cpp
    src/services/imessagebus.h
)

target_link_libraries(SmartMineScada PRIVATE Qt6::Core Qt6::Mqtt)

if(MSVC)
    target_compile_options(SmartMineScada PRIVATE /W4 /utf-8)
endif()
