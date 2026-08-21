/* STM32L476RG_FLASH.ld — linker script for STM32L476RGT6 (1 MB Flash, 128 KB SRAM) */
ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
    .isr_vector :
    {
        . = ALIGN(8);
        KEEP(*(.isr_vector))
        . = ALIGN(8);
    } > FLASH

    .text :
    {
        . = ALIGN(8);
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(8);
        _etext = .;
    } > FLASH

    .data :
    {
        . = ALIGN(8);
        _sdata = .;
        *(.data .data.*)
        . = ALIGN(8);
        _edata = .;
    } > RAM AT > FLASH

    .bss :
    {
        . = ALIGN(8);
        _sbss = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(8);
        _ebss = .;
    } > RAM

    _sidata = LOADADDR(.data);
}