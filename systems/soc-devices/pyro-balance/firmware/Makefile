# Pyro Balance — STM32G474 Firmware

TARGET = pyro-balance
BUILD_DIR = build
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

CPU = -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb
FLAGS = $(CPU) -O2 -Wall -g -ffunction-sections -fdata-sections -fno-common
FLAGS += -ICore/Inc -I.
LDFLAGS = $(CPU) -T STM32G474RET6_FLASH.ld -Wl,--gc-sections -Wl,-Map=$(BUILD_DIR)/$(TARGET).map

LDLIBS = -lm -lc -lnosys

# CMSIS startup
STARTUP = Core/Src/startup_stm32g474xx.s

C_SRCS = \
	Core/Src/main.c \
	Core/Src/furnace.c \
	Core/Src/balance.c \
	Core/Src/ads122u04.c \
	Core/Src/tga.c \
	Core/Src/bme280.c \
	Core/Src/oled_display.c \
	Core/Src/sd_logger.c \
	Core/Src/safety.c \
	Core/Src/esp32_link.c \
	Core/Src/purge.c \
	Core/Src/flash_store.c \
	Core/Src/stm32g4xx_hal_msp.c \
	Core/Src/stm32g4xx_it.c \
	Core/Src/system_stm32g4xx.c

OBJS = $(patsubst %.c,$(BUILD_DIR)/%.o,$(C_SRCS)) $(BUILD_DIR)/$(STARTUP:.s=.o)

all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin

$(BUILD_DIR)/$(TARGET).elf: $(OBJS) STM32G474RET6_FLASH.ld
	$(CC) $(LDFLAGS) $(OBJS) $(LDLIBS) -o $@
	$(SIZE) $@

$(BUILD_DIR)/$(TARGET).hex: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/$(TARGET).bin: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(FLAGS) -c $< -o $@

$(BUILD_DIR)/%.o: %.s
	@mkdir -p $(dir $@)
	$(CC) $(FLAGS) -x assembler-with-cpp -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)

flash: $(BUILD_DIR)/$(TARGET).bin
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program $(BUILD_DIR)/$(TARGET).bin verify reset exit 0x08000000"

.PHONY: all clean flash