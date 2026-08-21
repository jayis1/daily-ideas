# dent-scope / firmware/Makefile
# STM32G474RET6 build for Dent Scope — Pocket Instrumented Indentation Tester
# Requires: arm-none-eabi-gcc toolchain, STM32G4 HAL

PROJECT  = dent-scope
DEVICE   = STM32G474RET6
CORE     = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
OPT      = -Os
CC       = arm-none-eabi-gcc
LD       = arm-none-eabi-gcc
OBJCOPY  = arm-none-eabi-objcopy
SIZE     = arm-none-eabi-size

HAL_DIR  = Drivers/STM32G4xx_HAL_Driver
CMSIS    = Drivers/CMSIS/Device/ST/STM32G4xx/Source/Templates/system_stm32g4xx.c

CFLAGS   = $(CORE) $(OPT) -Wall -g3 \
           -I. -ICore/Inc \
           -I$(HAL_DIR)/Inc -I$(HAL_DIR)/Inc/Legacy \
           -IDrivers/CMSIS/Device/ST/STM32G4xx/Include \
           -IDrivers/CMSIS/Include \
           -DUSE_HAL_DRIVER -DSTM32G474xx

LDSCRIPT  = STM32G474RET6_FLASH.ld
LDFLAGS   = $(CORE) -T$(LDSCRIPT) -Wl,--gc-sections -Wl,-Map=$(PROJECT).map --specs=nano.specs --specs=nosys.specs

SRC_C    = Core/Src/main.c \
           Core/Src/stepper.c \
           Core/Src/loadcell.c \
           Core/Src/displacement.c \
           Core/Src/indentation.c \
           Core/Src/ds18b20.c \
           Core/Src/imu.c \
           Core/Src/oled_display.c \
           Core/Src/sd_logger.c \
           Core/Src/safety.c \
           Core/Src/esp32_link.c \
           Core/Src/flash_store.c \
           Core/Src/database.c \
           Core/Src/stm32g4xx_it.c \
           Core/Src/stm32g4xx_hal_msp.c \
           Core/Src/system_stm32g4xx.c

SRC_HAL  = $(wildcard $(HAL_DIR)/Src/*.c)
SRC_HAL  := $(filter-out %_template.c,$(SRC_HAL))

OBJ      = $(SRC_C:.c=.o) $(SRC_HAL:.c=.o) $(CMSIS:.c=.o)

all: $(PROJECT).elf $(PROJECT).hex

$(PROJECT).elf: $(OBJ) $(LDSCRIPT)
	$(LD) $(LDFLAGS) -o $@ $(OBJ) -lc -lm

$(PROJECT).hex: $(PROJECT).elf
	$(OBJCOPY) -O ihex $< $@
	$(SIZE) $<

clean:
	rm -f *.o *.elf *.hex *.map Core/Src/*.o

flash: $(PROJECT).elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
	  -c "program $(PROJECT).elf verify reset exit"

.PHONY: all clean flash