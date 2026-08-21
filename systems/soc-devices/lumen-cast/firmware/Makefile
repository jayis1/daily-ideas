# lumen_cast/firmware/Makefile
#
# Build firmware for STM32G491RET6 (Cortex-M4F @ 170 MHz)
# Requires: arm-none-eabi-gcc toolchain + STM32G4 HAL
#
# Toolchain: sudo apt install gcc-arm-none-eabi
# HAL:       STM32CubeG4 from ST or libopencm3
#
# Build:
#   make
# Flash:
#   make flash  (uses OpenOCD + ST-Link V2)
#
# ── Toolchain ──
CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

# ── Target MCU ──
MCU = stm32g491
CHIP = STM32G491RET6
CORTEX = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard

# ── Flags ──
CFLAGS = $(CORTEX) -Os -g -std=gnu11 \
         -Wall -Wextra -Wno-unused-parameter \
         -ffunction-sections -fdata-sections \
         -fno-common -fno-builtin \
         -I. -I./stm32g4_hal -I./stm32g4_hal/Inc \
         -DUSE_HAL_DRIVER -DSTM32G491xx

LDFLAGS = $(CORTEX) -T linker.ld -nostartfiles \
          -Wl,--gc-sections \
          -Wl,-Map=lumen_cast.map

LIBS = -lc -lm -lnosys

# ── Source files ──
SRCS = main.c goniometry.c photometer.c color.c motor.c servo.c \
       sh1106.c ble_bridge.c flashlog.c ds3231.c ws2812.c \
       stm32g4_hal/system_stm32g4xx.c stm32g4_hal/stm32g4xx_it.c \
       startup_stm32g491xx.s

OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.s=.o)

TARGET = lumen_cast.elf
BIN = lumen_cast.bin
HEX = lumen_cast.hex

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

%.o: %.s
	$(CC) $(CFLAGS) -c $< -o $@

flash: $(BIN)
	# Flash via ST-Link V2 + OpenOCD
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program $(BIN) 0x08000000 verify reset exit"

clean:
	rm -f $(OBJS) $(TARGET) $(BIN) $(HEX) lumen_cast.map