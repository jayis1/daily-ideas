# Hive Mind — STM32WL55JC Firmware Makefile
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 jayis1

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# CPU flags
CPU = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard

# Include paths
INCLUDES = \
  -ICore/Inc \
  -IDrivers/STM32WLxx_HAL_Driver/Inc \
  -IDrivers/STM32WLxx_HAL_Driver/Inc/Legacy \
  -IDrivers/CMSIS/Device/ST/STM32WLxx/Include \
  -IDrivers/CMSIS/Include \
  -IMiddlewares/FreeRTOS/Include \
  -IMiddlewares/LoRaWAN/Inc

# Compiler flags
CFLAGS = $(CPU) $(INCLUDES) -Wall -Wextra -Werror=implicit-function-declaration \
  -O2 -ffunction-sections -fdata-sections -std=gnu11 \
  -DSTM32WL55xx -DUSE_HAL_DRIVER -DARM_MATH_CM4

# Linker flags
LDFLAGS = $(CPU) -TSTM32WL55JC.ld \
  -Wl,--gc-sections -Wl,--print-memory-usage \
  -Wl,-Map=hive_mind.map,--cref \
  -specs=nano.specs -specs=nosys.specs

# Source files
C_SOURCES = \
  Core/Src/main.c \
  Core/Src/weight_sensor.c \
  Core/Src/temp_chain.c \
  Core/Src/acoustic_analyzer.c \
  Core/Src/bee_counter.c \
  Core/Src/bme280_driver.c \
  Core/Src/oled_display.c \
  Core/Src/lorawan_uplink.c \
  Core/Src/power_manager.c \
  Core/Src/hive_health.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_rcc.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_rcc_ex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_gpio.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_i2c.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_i2s.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_spi.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_uart.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_uart_ex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_adc.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_adc_ex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_rtc.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_rtc_ex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_pwr.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_pwr_ex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_cortex.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_dma.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_flash.c \
  Drivers/STM32WLxx_HAL_Driver/Src/stm32wlxx_hal_flash_ex.c \
  Middlewares/FreeRTOS/croutine.c \
  Middlewares/FreeRTOS/event_groups.c \
  Middlewares/FreeRTOS/list.c \
  Middlewares/FreeRTOS/queue.c \
  Middlewares/FreeRTOS/stream_buffer.c \
  Middlewares/FreeRTOS/tasks.c \
  Middlewares/FreeRTOS/timers.c \
  Middlewares/FreeRTOS/portable/GCC/ARM_CM4F/port.c \
  Middlewares/FreeRTOS/portable/MemMang/heap_4.c

# Object files
OBJECTS = $(C_SOURCES:.c=.o)

# Targets
TARGET = hive_mind

all: $(TARGET).elf $(TARGET).bin $(TARGET).hex

$(TARGET).elf: $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@
	$(SIZE) $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET).elf $(TARGET).bin $(TARGET).hex $(TARGET).map

flash: $(TARGET).bin
	st-flash write $(TARGET).bin 0x08000000

.PHONY: all clean flash