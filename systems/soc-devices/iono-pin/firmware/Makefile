# Makefile — Iono Pin firmware (STM32G474RET6)
# Toolchain: arm-none-eabi-gcc + STM32Cube HAL + CMSIS-DSP
# Alternative build to CMake (see firmware/main/CMakeLists.txt for ESP-IDF-style)

CROSS   = arm-none-eabi-
CC      = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE    = $(CROSS)size

MCPU    = -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb
CFLAGS  = $(MCPU) -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra -std=c11 \
          -I. -Imain -I/usr/include/cmsis -I/usr/include/stm32cubehal
LDFLAGS = $(MCPU) -T main/stm32g474_ret6.ld -Wl,--gc-sections -nostartfiles \
          -L/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+fp/hard -larm_cortexM4lf_math

SRCS = main/startup_stm32g474xx.s \
       main/main.c main/hv_supply.c main/shutter.c main/ionizer.c \
       main/electrometer.c main/ims.c main/library.c main/pump.c \
       main/bme280.c main/ds18b20.c main/display.c main/sd_log.c \
       main/ble_bridge.c main/safety.c main/buttons.c

OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.s=.o)

all: iono_pin.elf

iono_pin.elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)
	$(SIZE) $@
	$(OBJCOPY) -O ihex $@ iono_pin.hex
	$(OBJCOPY) -O binary $@ iono_pin.bin

clean:
	rm -f $(OBJS) iono_pin.elf iono_pin.hex iono_pin.bin

flash: iono_pin.elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program iono_pin.elf verify reset exit"

.PHONY: all clean flash