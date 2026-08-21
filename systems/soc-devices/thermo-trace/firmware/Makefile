PROJECT = thermo_trace
BUILD_DIR = build

all: $(BUILD_DIR)/thermo_trace.elf

$(BUILD_DIR)/thermo_trace.elf:
	@mkdir -p $(BUILD_DIR)
	cd $(BUILD_DIR) && cmake .. -DCMAKE_TOOLCHAIN_FILE=../toolchain.cmake && make -j$(nproc)

clean:
	rm -rf $(BUILD_DIR)

flash: $(BUILD_DIR)/thermo_trace.elf
	openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
		-c "program $(BUILD_DIR)/thermo_trace.elf verify reset exit"

.PHONY: all clean flash