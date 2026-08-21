/*
 * glyph_press/firmware/linker.ld — Linker script for RP2040
 *
 * RP2040: 16 KB ROM, 264 KB SRAM (6 banks), 2 MB external QSPI flash
 * Memory map:
 *   FLASH: 0x10000000 (XIP via QSPI) — 2 MB external
 *   SRAM:  0x20000000 — 264 KB (split across 6 banks)
 *   SRAM4/5 (scratch): 0x20040000 — 4 KB per core stack
 *
 * This is a simplified linker script for bare-metal RP2040.
 * The Pico SDK provides its own linker scripts (memmap_rp2040.ld)
 * which are used when building with CMake.
 */

ENTRY(_entry_point)

MEMORY
{
    FLASH(RX)  : ORIGIN = 0x10000000, LENGTH = 2048K
    RAM(RWX)   : ORIGIN = 0x20000000, LENGTH = 264K
    SCRATCH_X(RWX) : ORIGIN = 0x20040000, LENGTH = 4K
    SCRATCH_Y(RWX) : ORIGIN = 0x20041000, LENGTH = 4K
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