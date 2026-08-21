/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Linker Script
 *
 * STM32WL55JC: 256 KB Flash, 64 KB SRAM1, 32 KB SRAM2
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

ENTRY(Reset_Handler)

/* Stack starts at top of SRAM1 */
_estack = ORIGIN(RAM) + LENGTH(RAM);

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 256K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
    /* SRAM2 (32K) reserved for LoRaWAN stack + NVRAM */
    SRAM2 (rwx) : ORIGIN = 0x20010000, LENGTH = 32K
}

SECTIONS
{
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .data : AT (_sidata)
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM

    _sidata = LOADADDR(.data);

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM

    /* Stack grows downward from _estack */
    . = ALIGN(8);
    _end = .;
}