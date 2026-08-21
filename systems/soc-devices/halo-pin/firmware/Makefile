# Makefile for Halo Pin firmware — arm-none-eabi-gcc bare-metal
# Build: make
# Flash: make flash (via st-flash or openocd)

CROSS    = arm-none-eabi-
CC       = $(CROSS)gcc
OBJCOPY  = $(CROSS)objcopy
SIZE     = $(CROSS)size

MCU      = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
CFLAGS   = $(MCU) -std=c11 -Wall -Wextra -Os -ffunction-sections -fdata-sections -g3
LDFLAGS  = $(MCU) -T stm32g474_ret6.ld -Wl,--gc-sections -Wl,-Map=halo_pin.map -nostdlib
LIBS     = -lm

SRCS    = main.c laser.c airflow.c adc.c pulse.c calibration.c concentration.c \
          ambient.c display.c sd_log.c ble_bridge.c battery.c ui.c
ASMS    = startup_stm32g474xx.s
OBJS    = $(SRCS:.c=.o) $(ASMS:.s=.o)

TARGET  = halo_pin.elf

all: $(TARGET) halo_pin.hex halo_pin.bin

$(TARGET): $(OBJS) stm32g474_ret6.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)
	$(SIZE) $@

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.s
	$(CC) $(CFLAGS) -c -o $@ $<

halo_pin.hex: $(TARGET)
	$(OBJCOPY) -O ihex $< $@

halo_pin.bin: $(TARGET)
	$(OBJCOPY) -O binary $< $@

flash: $(TARGET)
	st-flash write halo_pin.bin 0x08000000

clean:
	rm -f $(OBJS) $(TARGET) halo_pin.hex halo_pin.bin halo_pin.map

.PHONY: all flash clean