cmake_minimum_required(VERSION 3.16)

project(SmartMineScada VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Mqtt)

qt_standard_project_setup()

qt_add_executable(SmartMineScada
    src/main.cpp

    src/models/role.h
    src/models/permissionpolicy.h
    src/models/permissionpolicy.cpp

    src/services/imessagebus.h
    src/services/mqttservice.h
    src/services/mqttservice.cpp
    src/services/sessionservice.h
    src/services/sessionservice.cpp

    src/viewmodels/mainviewmodel.h
    src/viewmodels/mainviewmodel.cpp

    src/views/mainwindow.h
    src/views/mainwindow.cpp
    src/views/logindialog.h
    src/views/logindialog.cpp
)

qt_add_resources(SmartMineScada "styles"
    PREFIX "/styles"
    BASE "resources"
    FILES resources/dark.qss
)

target_link_libraries(SmartMineScada PRIVATE Qt6::Core Qt6::Widgets Qt6::Mqtt)

target_include_directories(SmartMineScada PRIVATE src)

if(MSVC)
    target_compile_options(SmartMineScada PRIVATE /W4 /utf-8)
endif()
