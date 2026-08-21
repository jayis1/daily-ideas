# Makefile — Bone Echo firmware (alternative to CMake)
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

SRCS = startup_stm32g474xx.s main.c tx_pulser.c rx_chain.c adc.c sos.c bua.c \
       stiffness.c normative.c phantom.c heel_caliper.c display.c sd_log.c \
       ble_bridge.c aux_adc.c battery.c patient.c ui.c

OBJS = $(SRCS:.c=.o)

all: bone_echo.elf

bone_echo.elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)
	$(SIZE) $@
	$(OBJCOPY) -O ihex $@ bone_echo.hex
	$(OBJCOPY) -O binary $@ bone_echo.bin

clean:
	rm -f $(OBJS) bone_echo.elf bone_echo.hex bone_echo.bin

flash: bone_echo.elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program bone_echo.elf verify reset exit"

.PHONY: all clean flash