/* STM32G474RET6 linker script (simplified). Use ST CubeMX generated script in production. */
ENTRY(Reset_Handler)
_estack = 0x20018000;
MEMORY {
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   (rwx): ORIGIN = 0x20000000, LENGTH = 96K
}
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text : { *(.text*) *(.rodata*) } > FLASH
  .ARM.exidx : { *(.ARM.exidx*) } > FLASH
  .data : AT (ADDR(.text)+SIZEOF(.text)) { *(.data*) } > RAM
  .bss : { *(.bss*) *(COMMON) } > RAM
  ._user_heap_stack : { . = . + 0x400; } > RAM
}