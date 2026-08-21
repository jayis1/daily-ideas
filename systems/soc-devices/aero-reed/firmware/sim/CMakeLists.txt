# Aero Reed — native simulation build (no ESP-IDF required)
#
# Build:  cmake -B build -S sim && cmake --build build
# Run:    ./build/aero_reed_sim
cmake_minimum_required(VERSION 3.16)
project(aero_reed_sim C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_FLAGS "-Wall -Wextra -O2 -lm")

# Simulation sources: synth + sim stubs + harness
add_executable(aero_reed_sim
    ../main/synth.c
    ../main/patch.c
    ../port_sim.c
)

target_include_directories(aero_reed_sim PRIVATE ../main stubs)
target_link_libraries(aero_reed_sim m)