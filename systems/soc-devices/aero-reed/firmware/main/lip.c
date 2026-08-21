/*
 * lip.c — lip/bite force sensor (FSR-402 voltage divider on ADC1)
 *
 * FSR-402 + 10 kΩ pull-down: more force → lower resistance → higher voltage.
 * We map force to pitch bend (bite-down bends pitch up, like a reed) and
 * brightness CC74.
 */
#include "lip.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include <math.h>

static const char *TAG = "lip";

static adc_oneshot_unit_handle_t *adc1;
static adc_channel_t lip_chan;
static int offset_adc = 0;
static float force_f = 0.0f;

/* Pitch bend range in cents (configurable per patch, default ±2 semitone) */
#define LIP_BEND_RANGE_CENTS 200

void lip_init(void)
{
    /* Use ADC1 channel 3 (GPIO3) — note this is shared with touch T3,
     * so in production we recommend ADS1115. For the demo build we
     * use a separate analog pin (GPIO17 ADC1_CH6 is breath, so we
     * use ADC1_CH3 via the ADS1115 I2C path; here we stub-configure it). */
    lip_chan = (adc_channel_t)3;
    /* Calibrate offset (no-force baseline) */
    int sum = 0;
    for (int i = 0; i < 30; i++) {
        /* In real build: adc_oneshot_read(adc1, lip_chan, &raw);
         * For the reference impl we use a placeholder read */
        int raw = 200;  /* placeholder - actual code uses ADS1115 */
        sum += raw;
    }
    offset_adc = sum / 30;
    ESP_LOGI(TAG, "Lip sensor ready (offset=%d). Use ADS1115 for production.", offset_adc);
}

void lip_scan(void)
{
    /* In production: read ADS1115 channel for FSR voltage.
     * Convert to force 0..1 with logarithmic curve (FSR is log-response). */
    int raw = offset_adc;  /* placeholder - ADS1115 read */
    int delta = raw - offset_adc;
    if (delta < 0) delta = 0;
    float target = (float)delta / 2048.0f;  /* normalize */
    if (target > 1.0f) target = 1.0f;
    target = powf(target, 0.5f);  /* expand low end (log response) */

    /* Smooth */
    force_f = force_f * 0.8f + target * 0.2f;
}

int16_t lip_get_bend_cents(void)
{
    /* Bite harder → pitch goes up (sax-like). Map force 0..1 → 0..+range */
    return (int16_t)(force_f * LIP_BEND_RANGE_CENTS);
}

uint8_t lip_get_brightness(void)
{
    /* More bite → brighter (CC74) */
    return (uint8_t)(force_f * 127.0f);
}

float lip_get_force(void)
{
    return force_f;
}