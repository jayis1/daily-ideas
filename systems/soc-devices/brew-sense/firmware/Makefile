# Brew Sense Firmware Makefile
# STM32L476RG using ARM GCC toolchain

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# Project
TARGET = brew_sense
BUILD_DIR = build

# MCU settings
MCU = cortex-m4
FPU = -mfpu=fpv4-sp-d16 -mfloat-abi=hard

# CPU flags
CPU_FLAGS = -mcpu=$(MCU) -mthumb $(FPU)

# Include paths
INCLUDES = \
	-ICore/Inc \
	-IDrivers/STM32L4xx_HAL_Driver/Inc \
	-IDrivers/STM32L4xx_HAL_Driver/Inc/Legacy \
	-IDrivers/CMSIS/Device/ST/STM32L4xx/Include \
	-IDrivers/CMSIS/Include \
	-IMiddlewares/ST_BLE

# Source files
C_SOURCES = \
	Core/Src/main.c \
	Core/Src/sensor_manager.c \
	Core/Src/densitometer.c \
	Core/Src/fermentation.c \
	Core/Src/ble_service.c \
	Core/Src/wifi_uplink.c \
	Core/Src/power_manager.c \
	Core/Src/display.c \
	Core/Src/alarm.c \
	Core/Src/calibration.c \
	Core/Src/stm32l4xx_it.c \
	Core/Src/stm32l4xx_hal_msp.c \
	Core/Src/system_stm32l4xx.c

# ASM sources
ASM_SOURCES = \
	Core/Src/startup_stm32l476xx.s

# Compiler flags
CFLAGS = $(CPU_FLAGS) $(INCLUDES) \
	-Wall -Wextra -Wshadow -Wundef \
	-Os -g3 \
	-ffunction-sections -fdata-sections \
	-DSTM32L476xx \
	-DUSE_HAL_DRIVER \
	-DARM_MATH_CM4

# Linker flags
LDFLAGS = $(CPU_FLAGS) \
	-TSTM32L476RGTX_FLASH.ld \
	-Wl,--gc-sections \
	-Wl,--print-memory-usage \
	-specs=nano.specs \
	-specs=nosys.specs \
	-lm \
	-lc

# Object files
OBJECTS = $(C_SOURCES:.c=.o) $(ASM_SOURCES:.s=.o)

# Default target
all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/$(TARGET).elf: $(OBJECTS) | $(BUILD_DIR)
	$(CC) $(LDFLAGS) -o $@ $^
	$(SIZE) $@

$(BUILD_DIR)/$(TARGET).hex: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/$(TARGET).bin: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.s
	$(CC) $(CPU_FLAGS) -c -o $@ $<

flash: $(BUILD_DIR)/$(TARGET).elf
	openocd -f interface/stlink.cfg -f target/stm32l4x.cfg \
		-c "program $< verify reset exit"

clean:
	rm -rf $(BUILD_DIR) $(OBJECTS)

.PHONY: all flash clean