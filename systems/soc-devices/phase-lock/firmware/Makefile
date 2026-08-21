# Makefile — Phase Lock firmware (alt to CMake)
# Target: STM32G491RET6
# Usage: make && make flash   (requires arm-none-eabi-gcc + STM32Cube HAL + CMSIS-DSP)
#        make openocd         (flash via ST-Link)
#        make clean

CROSS   = arm-none-eabi-
CC      = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE    = $(CROSS)size

MCUFLAGS = -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb
CFLAGS = $(MCUFLAGS) -Os -g3 -ffunction-sections -fdata-sections \
         -Wall -Wextra -std=c11 -I. -I/usr/include/cmsis -I/usr/include/stm32cubehal
LDFLAGS = $(MCUFLAGS) -Tstm32g491_ret6.ld -Wl,--gc-sections -nostartfiles
LIBS = -larm_cortexM4lf_math -lc -lnosys

SRCS = main.c ref_osc.c adc.c demod.c pga.c power_amp.c sweep.c display.c \
       sd_log.c ble_bridge.c aux_adc.c battery.c ui.c
OBJS = startup_stm32g491xx.o $(SRCS:.c=.o)

all: phase_lock.elf

phase_lock.elf: $(OBJS) stm32g491_ret6.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)
	$(SIZE) $@

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.s
	$(CC) $(CFLAGS) -x assembler-with-cpp -c -o $@ $<

flash: phase_lock.elf
	$(OBJCOPY) -O ihex phase_lock.elf phase_lock.hex
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program phase_lock.elf verify reset exit"

clean:
	rm -f *.o phase_lock.elf phase_lock.hex