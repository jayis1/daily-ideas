# spiro_flow/firmware/Makefile
#
# Build firmware for CH32V203RBT6 (RISC-V RV32IMAC)
# Requires: riscv-none-embed-gcc toolchain + WCH CH32V20x HAL
#
# Toolchain: https://github.com/WCH-RV/gcc-riscv-none-embed
# HAL:       https://github.com/openwch/ch32v20x
#
# Build:
#   make
# Flash:
#   make flash  (uses WCH-LinkE SWD programmer)
#

# ── Toolchain ──
CC      = riscv-none-embed-gcc
OBJCOPY = riscv-none-embed-objcopy
SIZE    = riscv-none-embed-size

# ── Target MCU ──
MCU = ch32v20x
CHIP = CH32V203RBT6
CORE = rv32imac
ARCH = -march=rv32imac -mabi=ilp32 -msmall-data-limit=8

# ── Flags ──
CFLAGS = $(ARCH) -Os -g -std=gnu11 \
         -Wall -Wextra -Wno-unused-parameter \
         -ffunction-sections -fdata-sections \
         -fno-common -fno-builtin \
         -I. -I./wch_hal -I./wch_hal/core -I./wch_hal/peripheral \
         -DCH32V20x_D8C -DCH32V203RBT6

LDFLAGS = $(ARCH) -T linker.ld -nostartfiles \
          -Wl,--gc-sections -Wl,--no-relax \
          -Wl,-Map=spiro_flow.map

LIBS = -lc -lm

# ── Source files ──
SRCS = main.c spirometry.c sdp810.c bme280.c sh1106.c \
       ble_bridge.c flashlog.c buzzer.c ws2812.c \
       wch_hal/system_ch32v20x.c wch_hal/ch32v20x_it.c \
       startup_ch32v20x.S

OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.S=.o)

TARGET = spiro_flow.elf
BIN = spiro_flow.bin
HEX = spiro_flow.hex

# ── Build rules ──
.PHONY: all flash clean

all: $(TARGET) $(BIN) $(HEX)
	$(SIZE) $(TARGET)

$(TARGET): $(OBJS) linker.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)

$(BIN): $(TARGET)
	$(OBJCOPY) -O binary $< $@

$(HEX): $(TARGET)
	$(OBJCOPY) -O ihex $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.S
	$(CC) $(CFLAGS) -c $< -o $@

flash: $(BIN)
	# Flash via WCH-LinkE SWD programmer
	# Requires wchisp or WCH-LinkUtility
	wchisp flash $(BIN)

clean:
	rm -f $(OBJS) $(TARGET) $(BIN) $(HEX) spiro_flow.map