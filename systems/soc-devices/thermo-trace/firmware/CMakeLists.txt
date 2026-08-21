cmake_minimum_required(VERSION 3.22)

# ---- Toolchain: arm-none-eabi-gcc ----
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR cortex-m4)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(CMAKE_C_FLAGS "${MCU_FLAGS} -std=c11 -Wall -Wextra -Os -ffunction-sections -fdata-sections -g3")
set(CMAKE_ASM_FLAGS "${MCU_FLAGS} -x assembler-with-cpp")
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/stm32g491_lqfp64.ld -Wl,--gc-sections -Wl,-Map=thermo_trace.map -nostdlib")

project(thermo_trace C ASM)

set(SOURCES
    main.c
    heater.c
    rtd.c
    ads122.c
    dsc.c
    ramp.c
    library.c
    display.c
    sd_log.c
    ble_bridge.c
    safety.c
    battery.c
    ui.c
    startup_stm32g491xx.s
)

add_executable(thermo_trace.elf ${SOURCES})

target_include_directories(thermo_trace.elf PRIVATE ${CMAKE_SOURCE_DIR})

target_link_libraries(thermo_trace.elf PRIVATE m)

set_target_properties(thermo_trace.elf PROPERTIES LINK_DEPENDS ${CMAKE_SOURCE_DIR}/stm32g491_lqfp64.ld)

# Generate .hex and .bin
add_custom_command(TARGET thermo_trace.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:thermo_trace.elf> thermo_trace.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:thermo_trace.elf> thermo_trace.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:thermo_trace.elf>
    COMMENT "Generating hex/bin/size"
)