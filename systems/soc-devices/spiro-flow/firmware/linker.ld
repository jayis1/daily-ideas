/*
 * spiro_flow/firmware/linker.ld — Linker script for CH32V203RBT6
 *
 * CH32V203RBT6: 128 KB flash, 64 KB SRAM, LQFP64
 * Memory map:
 *   FLASH: 0x08000000 - 0x0801FFFF  (128 KB)
 *   SRAM:  0x20000000 - 0x2000FFFF  (64 KB)
 */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 128K
    RAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
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