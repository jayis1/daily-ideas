/**
 * glyph_press/firmware/battery.c — Battery Voltage Monitor
 *
 * Reads LiPo voltage via ADC0 (GP26) through a 2:1 voltage divider.
 * Reports battery voltage in millivolts.
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/adc.h"

#define ADC_VREF        3300   /* 3.3V reference in mV */
#define DIVIDER_RATIO   2.0f   /* R1=R2 → 2:1 divider */
#define ADC_RESOLUTION  4095   /* 12-bit ADC */

void battery_init(void)
{
    adc_init();
    adc_gpio_init(PIN_BATT_ADC);
    adc_select_input(0); /* ADC0 = GP26 */
}

uint16_t battery_read_mv(void)
{
    uint16_t raw = adc_read();
    uint32_t mv = (uint32_t)((raw * ADC_VREF) / ADC_RESOLUTION);
    return (uint16_t)(mv * DIVIDER_RATIO);
}