# Makefile — Helio Tilt firmware (alternative to CMake)
# Target: STM32G474RET6 (ARM Cortex-M4F, 170 MHz)
# Toolchain: arm-none-eabi-gcc + STM32Cube HAL + CMSIS-DSP

CROSS   = arm-none-eabi-
CC      = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE    = $(CROSS)size

MCPU    = -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb
CFLAGS  = $(MCPU) -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra -std=c11 \
          -I. -I/usr/include/cmsis -I/usr/include/stm32cubehal
LDFLAGS = $(MCPU) -T stm32g474_ret6.ld -Wl,--gc-sections -nostartfiles \
          -L/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+fp/hard -larm_cortexM4lf_math

SRCS = startup_stm32g474xx.s main.c solar_pos.c gps.c imu.c stepper.c \
       filter_wheel.c detector.c radiometry.c langley.c display.c \
       sd_log.c ble_bridge.c battery.c ui.c

OBJS = $(SRCS:.c=.o)

all: helio_tilt.elf

helio_tilt.elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)
	$(SIZE) $@
	$(OBJCOPY) -O ihex $@ helio_tilt.hex
	$(OBJCOPY) -O binary $@ helio_tilt.bin

clean:
	rm -f $(OBJS) helio_tilt.elf helio_tilt.hex helio_tilt.bin

flash: helio_tilt.elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program helio_tilt.elf verify reset exit"

.PHONY: all clean flash