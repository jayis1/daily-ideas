/*
 * stm32g474_ret6.ld — linker script for STM32G474RET6
 * 512 KB flash, 128 KB SRAM, LQFP64
 */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);

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
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .data : AT (_etext)
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM

    .heap :
    {
        . = ALIGN(4);
        _sheap = .;
        . = . + 0x4000;
        . = ALIGN(4);
        _eheap = .;
    } > RAM

    .stack :
    {
        . = ALIGN(4);
        _sstack = .;
        . = . + 0x2000;
        . = ALIGN(4);
        _estack_section = .;
    } > RAM
}

PROVIDE(_estack_top = _estack);