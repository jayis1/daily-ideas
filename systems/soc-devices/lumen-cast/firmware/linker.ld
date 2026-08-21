/*
 * lumen_cast/firmware/linker.ld — Linker script for STM32G491RET6
 *
 * STM32G491RET6: 512 KB flash, 112 KB SRAM, LQFP64
 * Memory map:
 *   FLASH: 0x08000000 - 0x0807FFFF  (512 KB)
 *   SRAM:  0x20000000 - 0x2001BFFF  (112 KB)
 *   CCM:   0x10000000 - 0x1000FFFF  (64 KB, not used here)
 */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 512K
    RAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 112K
}

SECTIONS
{
    .vectors :
    {
        . = ALIGN(4);
        KEEP(*(.vectors))
        . = ALIGN(4);
    } > FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text) *(.text.*)
        *(.rodata) *(.rodata.*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data) *(.data.*)
        . = ALIGN(4);
        _edata = .;
    } > RAM AT > FLASH

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss) *(.bss.*) *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM

    _sidata = LOADADDR(.data);

    .stack (NOLOAD) :
    {
        . = ALIGN(8);
        _sstack = .;
        . = . + 4096;
        . = ALIGN(8);
        _estack = .;
    } > RAM
}