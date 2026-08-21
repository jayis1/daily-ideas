/*
 * stm32g491_ret6.ld — linker script for STM32G491RET6
 * 256 KB flash @ 0x08000000, 128 KB SRAM @ 0x20000000
 * CCM SRAM (32 KB) @ 0x10000000 for the demodulation buffers (no DMA).
 */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 256K
    SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 112K
    CCM   (rwx) : ORIGIN = 0x10000000, LENGTH = 32K
}

_estack = ORIGIN(SRAM) + LENGTH(SRAM);

SECTIONS
{
    .isr_vector : {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    .text : {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .data : AT (_etext) {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > SRAM

    .bss (NOLOAD) : {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > SRAM

    .ccm (NOLOAD) : {
        . = ALIGN(4);
        *(.ccm)
        *(.ccm*)
        . = ALIGN(4);
    } > CCM

    PROVIDE(end = .);
}