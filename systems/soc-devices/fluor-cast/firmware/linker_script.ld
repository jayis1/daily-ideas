/*
 * linker_script.ld — STM32G474RET6 linker script
 * 512 KB Flash, 128 KB RAM (96 KB SRAM1 + 32 KB SRAM2 + CCM)
 */

ENTRY(Reset_Handler)

/* Memory map */
MEMORY
{
    FLASH (rx)      : ORIGIN = 0x08000000, LENGTH = 512K
    RAM   (xrw)     : ORIGIN = 0x20000000, LENGTH = 96K
    RAM2  (xrw)     : ORIGIN = 0x20018000, LENGTH = 32K
    CCM   (xrw)     : ORIGIN = 0x10000000, LENGTH = 16K
}

/* Stack at top of RAM */
_stack_top = ORIGIN(RAM) + LENGTH(RAM);

/* Minimum heap/stack size */
_min_heap_size = 0x400;
_min_stack_size = 0x800;

SECTIONS
{
    /* Vector table */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } >FLASH

    /* Code */
    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame)
        KEEP(*(.init))
        KEEP(*(.fini))
        . = ALIGN(4);
        _etext = .;
    } >FLASH

    /* Read-only data */
    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } >FLASH

    /* ARM exception tables */
    .ARM.extab :
    {
        *(.ARM.extab* .gnu.linkonce.armextab.*)
    } >FLASH
    .ARM :
    {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } >FLASH

    /* Preinit/preinit_array/init_array */
    .preinit_array :
    {
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array*))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    } >FLASH

    .init_array :
    {
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT(.init_array.*)))
        KEEP(*(.init_array*))
        PROVIDE_HIDDEN(__init_array_end = .);
    } >FLASH

    .fini_array :
    {
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT(.fini_array.*)))
        KEEP(*(.fini_array*))
        PROVIDE_HIDDEN(__fini_array_end = .);
    } >FLASH

    /* Library stubs */
    _sidata = LOADADDR(.data);
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } >RAM AT> FLASH

    /* BSS (zero-initialized) */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        __bss_start__ = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
        __bss_end__ = .;
    } >RAM

    /* Heap/stack */
    ._user_heap_stack :
    {
        . = ALIGN(8);
        PROVIDE(end = .);
        PROVIDE(_end = .);
        . = . + _min_heap_size;
        . = . + _min_stack_size;
        . = ALIGN(8);
    } >RAM

    /* Discard */
    /DISCARD/ :
    {
        *(.ARM.attributes)
        *(.comment)
    }
}