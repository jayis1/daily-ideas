# glyph_press/firmware/Makefile
#
# Build firmware for RP2040 (Dual Cortex-M0+ @ 133 MHz)
# Requires: arm-none-eabi-gcc toolchain + Raspberry Pi Pico SDK
#
# Toolchain: sudo apt install gcc-arm-none-eabi
# Pico SDK:  git clone https://github.com/raspberrypi/pico-sdk
#            export PICO_SDK_PATH=/path/to/pico-sdk
#
# Build:
#   mkdir build && cd build
#   cmake ..
#   make -j4
#
# Flash:
#   Hold BOOTSEL on RP2040, copy glyph_press.uf2 to the mounted drive
#   OR: picoprobe + OpenOCD
#
# ── Toolchain ──
CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

# ── Target MCU ──
MCU = rp2040
CORTEX = -mcpu=cortex-m0plus -mthumb

# ── Flags ──
CFLAGS = $(CORTEX) -Os -g -std=gnu11 \
         -Wall -Wextra -Wno-unused-parameter \
         -ffunction-sections -fdata-sections \
         -fno-common -fno-builtin \
         -I. -I$(PICO_SDK_PATH)/src/common/pico_stdlib/include \
         -I$(PICO_SDK_PATH)/src/rp2040/hardware_regs/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_gpio/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_adc/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_i2c/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_spi/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_uart/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/hardware_pwm/include \
         -I$(PICO_SDK_PATH)/src/rp2_common/pico_multicore/include

LDFLAGS = $(CORTEX) -T linker.ld -nostartfiles \
          -Wl,--gc-sections \
          -Wl,-Map=glyph_press.map

LIBS = -lc -lm -lnosys

# ── Source files ──
SRCS = main.c braille.c emboss.c feed.c sh1106.c ble_uart.c \
       sd_card.c flash_table.c buttons.c encoder.c ws2812.c \
       battery.c paper_sensor.c

OBJS = $(SRCS:.c=.o)

TARGET = glyph_press.elf
BIN = glyph_press.bin
HEX = glyph_press.hex
UF2 = glyph_press.uf2

# ── Build rules ──
.PHONY: all flash clean

all: $(TARGET) $(BIN) $(HEX) $(UF2)
	$(SIZE) $(TARGET)

$(TARGET): $(OBJS) linker.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)

$(BIN): $(TARGET)
	$(OBJCOPY) -O binary $< $@

$(HEX): $(TARGET)
	$(OBJCOPY) -O ihex $< $@

$(UF2): $(TARGET)
	$(OBJCOPY) -O uf2 $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

flash: $(UF2)
	# Copy UF2 to RP2040 BOOTSEL mass storage
	cp $(UF2) /media/$(USER)/RPI-RP2/

clean:
	rm -f $(OBJS) $(TARGET) $(BIN) $(HEX) $(UF2) glyph_press.map