/*
 * aux_adc.c — ADS1115 aux channel reads (temp, etc.)
 *
 * ADS1115 on I2C1 (address 0x48) provides 4× 16-bit aux channels.
 * DS18B20 on PC15 (1-Wire) provides phantom temperature.
 */

#include "aux_adc.h"
#include "stm32g474_conf.h"
#include <stddef.h>

void aux_adc_init(void)
{
    /* ADS1115 shares I2C1 with the OLED; already initialized in display_init */
}

float aux_adc_read(int channel)
{
    if (channel < 0 || channel > 3) return 0.0f;
    /* Simplified: real code configures ADS1115 and reads */
    return 1.65f;   /* Placeholder */
}

float aux_adc_read_temp(void)
{
    /* DS18B20 on PC15 (1-Wire, bit-banged)
     * Real code sends convert-T command, waits 750 ms, reads scratchpad.
     */
    return 22.0f;   /* Placeholder: 22 °C */
}