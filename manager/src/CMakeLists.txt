cmake_minimum_required(VERSION 2.8.10)

project(load_balancer)

find_package(rabbitmq-c REQUIRED)

add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} rabbitmq)
