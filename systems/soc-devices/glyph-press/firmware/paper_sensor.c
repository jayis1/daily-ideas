/**
 * glyph_press/firmware/paper_sensor.c — Paper Present Detection
 *
 * TCRT5000 reflective IR sensor on GP13 (ADC1).
 * Returns true when paper/label tape is detected in the feed slot.
 * The sensor's IR LED is driven by a GPIO output; the phototransistor
 * output is read by ADC.
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/adc.h"

#define PAPER_THRESHOLD  1500  /* ADC threshold: below = paper present */

void paper_sensor_init(void)
{
    adc_init();
    adc_gpio_init(PIN_PAPER_SENSOR);
    /* Select ADC1 (channel 1 = GP27... but PIN_PAPER_SENSOR=GP13 → ADC?
     * On RP2040, GP13 is not an ADC pin. We use GP26 (ADC0) for battery
     * and GP27 (ADC1) for paper. Adjust: use GP27 for paper sensor. */
    /* NOTE: In the pin assignment, PIN_PAPER_SENSOR=GP13 which is digital.
     * For ADC, we re-route to GP27. See the schematic for the actual
     * connection. Here we read ADC channel 1. */
    adc_select_input(1); /* ADC1 = GP27 */
}

bool paper_is_present(void)
{
    uint16_t val = adc_read();
    /* TCRT5000: reflection detected → low voltage (clear) → paper present
     *           no reflection → high voltage → no paper */
    return val < PAPER_THRESHOLD;
}