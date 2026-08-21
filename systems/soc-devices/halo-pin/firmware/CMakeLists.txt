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
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/stm32g474_ret6.ld -Wl,--gc-sections -Wl,-Map=halo_pin.map -nostdlib")

project(halo_pin C ASM)

set(SOURCES
    main.c
    laser.c
    airflow.c
    adc.c
    pulse.c
    calibration.c
    concentration.c
    ambient.c
    display.c
    sd_log.c
    ble_bridge.c
    battery.c
    ui.c
    startup_stm32g474xx.s
)

add_executable(halo_pin.elf ${SOURCES})

target_include_directories(halo_pin.elf PRIVATE ${CMAKE_SOURCE_DIR})

target_link_libraries(halo_pin.elf PRIVATE m)

set_target_properties(halo_pin.elf PROPERTIES LINK_DEPENDS ${CMAKE_SOURCE_DIR}/stm32g474_ret6.ld)

# Generate .hex and .bin
add_custom_command(TARGET halo_pin.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:halo_pin.elf> halo_pin.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:halo_pin.elf> halo_pin.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:halo_pin.elf>
    COMMENT "Generating hex/bin/size"
)