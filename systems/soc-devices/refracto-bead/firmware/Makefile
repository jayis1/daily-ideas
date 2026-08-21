# Refracto Bead — Pocket Digital Abbe Refractometer
# STM32G491RET6 Build (arm-none-eabi-gcc + STM32Cube HAL)

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# MCU flags
MCU = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard

# Includes
INCLUDES = \
    -ICore/Inc \
    -IDrivers/STM32G4xx_HAL_Driver/Inc \
    -IDrivers/STM32G4xx_HAL_Driver/Inc/Legacy \
    -IDrivers/CMSIS/Device/ST/STM32G4xx/Include \
    -IDrivers/CMSIS/Include

# C flags
CFLAGS = $(MCU) $(INCLUDES) -O2 -Wall -Wextra -std=c11 \
         -DUSE_HAL_DRIVER -DSTM32G491xx \
         -ffunction-sections -fdata-sections

# Linker
LDFLAGS = $(MCU) -T STM32G491RETX_FLASH.ld \
          --gc-sections -Wl,--Map=build/refracto-bead.map

# Source files
SRC = \
    Core/Src/main.c \
    Core/Src/tsl1402r.c \
    Core/Src/edge_detect.c \
    Core/Src/refract_calc.c \
    Core/Src/compound_lib.c \
    Core/Src/ds18b20.c \
    Core/Src/bme280.c \
    Core/Src/oled_display.c \
    Core/Src/sd_logger.c \
    Core/Src/esp32_link.c \
    Core/Src/power_manager.c \
    Core/Src/stm32g4xx_it.c \
    Core/Src/stm32g4xx_hal_msp.c \
    Core/Src/system_stm32g4xx.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_adc.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2c.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_spi.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_tim.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_uart.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_gpio.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_pwr.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_rcc.c \
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_cortex.c

OBJ = $(patsubst %.c, build/%.o, $(SRC))

# Build targets
.PHONY: all clean flash

all: build/refracto-bead.elf build/refracto-bead.bin build/refracto-bead.hex

build/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

build/refracto-bead.elf: $(OBJ)
	$(CC) $(LDFLAGS) $(OBJ) -o $@
	$(SIZE) $@

build/refracto-bead.bin: build/refracto-bead.elf
	$(OBJCOPY) -O binary $< $@

build/refracto-bead.hex: build/refracto-bead.elf
	$(OBJCOPY) -O ihex $< $@

flash: build/refracto-bead.elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
	        -c "program $< verify reset exit"

clean:
	rm -rf build/