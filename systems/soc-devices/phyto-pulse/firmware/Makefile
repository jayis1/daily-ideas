# Makefile — Phyto Pulse firmware (STM32G474RET6)
# Uses arm-none-eabi-gcc toolchain

TARGET = phyto-pulse
BUILD_DIR = build

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# MCU flags
CPU = -mcpu=cortex-m4
FPU = -mfpu=fpv4-sp-d16
FLOAT_ABI = -mfloat-abi=hard
MCU = $(CPU) $(FPU) $(FLOAT_ABI)

# Includes
C_DEFS = -DUSE_HAL_DRIVER -DSTM32G474xx -DARM_MATH_CM4
C_INCLUDES = \
  -ICore/Inc \
  -IDrivers/STM32G4xx_HAL_Driver/Inc \
  -IDrivers/STM32G4xx_HAL_Driver/Inc/Legacy \
  -IDrivers/CMSIS/Device/ST/STM32G4xx/Include \
  -IDrivers/CMSIS/Include \
  -IMiddlewares/Third_Party/FatFs/src \
  -IMiddlewares/CMSIS/NN/Include

# Source files
C_SOURCES = \
  Core/Src/main.c \
  Core/Src/ads1256.c \
  Core/Src/ina333.c \
  Core/Src/spike_detect.c \
  Core/Src/spike_classify.c \
  Core/Src/slow_wave.c \
  Core/Src/experiment.c \
  Core/Src/sd_logger.c \
  Core/Src/esp32_link.c \
  Core/Src/oled_display.c \
  Core/Src/bme280.c \
  Core/Src/power_manager.c \
  Core/Src/stm32g4xx_it.c \
  Core/Src/stm32g4xx_hal_msp.c \
  Core/Src/system_stm32g4xx.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_adc.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_dma.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_flash.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_gpio.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2c.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_pwr.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_rcc.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_spi.c \
  Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_uart.c \
  Middlewares/Third_Party/FatFs/src/fatfs.c \
  Middlewares/Third_Party/FatFs/src/diskio.c \
  Middlewares/CMSIS/NN/Source/ConvolutionFunctions/arm_conv_s8.c \
  Middlewares/CMSIS/NN/Source/FullyConnectedFunctions/arm_fullyconnected_s8.c

ASM_SOURCES = \
  Drivers/CMSIS/Device/ST/STM32G4xx/Source/Templates/gcc/startup_stm32g474xx.s

# Compiler flags
CFLAGS = $(MCU) $(C_DEFS) $(C_INCLUDES) -O2 -Wall -fdata-sections -ffunction-sections -g -std=c11
LDFLAGS = $(MCU) -T STM32G474RETX_FLASH.ld -Wl,--gc-sections -lc -lm -lnosys

# Build objects
OBJECTS = $(C_SOURCES:.c=.o)
ASM_OBJECTS = $(ASM_SOURCES:.s=.o)

all: $(BUILD_DIR)/$(TARGET).bin

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.o: %.s
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -x assembler-with-cpp -c $< -o $@

$(BUILD_DIR)/$(TARGET).elf: $(addprefix $(BUILD_DIR)/, $(OBJECTS)) $(addprefix $(BUILD_DIR)/, $(ASM_OBJECTS))
	$(CC) $(LDFLAGS) $^ -o $@
	$(SIZE) $@

$(BUILD_DIR)/$(TARGET).bin: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)

flash: $(BUILD_DIR)/$(TARGET).bin
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
	  -c "program $(BUILD_DIR)/$(TARGET).bin exit 0x08000000"

.PHONY: all clean flash