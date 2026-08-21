/*
 * Therma Weave — Temperature Sensor
 * temp_sensor.c — 74HC4051 multiplexed NTC thermistor reading
 *
 * SPDX-License-Identifier: MIT
 */

#include "temp_sensor.h"
#include <math.h>
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/adc.h"

static const char *TAG = "TEMP_SENS";

void temp_sensor_init(temp_sensor_t *ts, uint8_t mux_a, uint8_t mux_b,
                       uint8_t mux_c, uint8_t mux_en)
{
    ts->mux_a_pin = mux_a;
    ts->mux_b_pin = mux_b;
    ts->mux_c_pin = mux_c;
    ts->mux_en_pin = mux_en;

    for (int i = 0; i < NUM_THERMISTORS; i++) {
        ts->raw_adc[i] = 0;
        ts->temp_c[i] = 0.0f;
        ts->open_circuit[i] = false;
        ts->short_circuit[i] = false;
    }
    for (int i = 0; i < NUM_ZONES; i++) {
        ts->zone_temp[i] = 25.0f;  /* Default to room temperature */
    }

    ESP_LOGI(TAG, "Temperature sensor initialized (74HC4051 mux on pins A=%d, B=%d, C=%d, EN=%d)",
             mux_a, mux_b, mux_c, mux_en);
}

void temp_sensor_scan_all(temp_sensor_t *ts)
{
    for (int ch = 0; ch < NUM_THERMISTORS; ch++) {
        /* Select the channel on the 74HC4051 */
        gpio_set_level(ts->mux_a_pin, (ch >> 0) & 1);
        gpio_set_level(ts->mux_b_pin, (ch >> 1) & 1);
        gpio_set_level(ts->mux_c_pin, (ch >> 2) & 1);

        /* Enable the mux (active low) */
        gpio_set_level(ts->mux_en_pin, 0);

        /* Small delay for mux settling and ADC sampling */
        /* In real firmware: ets_delay_us(100); */

        /* Read ADC */
        int adc_raw = 0;
        /* Real: adc2_get_raw(ADC2_CHANNEL_0, ADC_WIDTH_BIT_12, &adc_raw); */
        adc_raw = 2048;  /* Placeholder: midpoint */

        /* Disable mux after reading */
        gpio_set_level(ts->mux_en_pin, 1);

        ts->raw_adc[ch] = (uint16_t)adc_raw;

        /* Check for open/short circuit */
        if (adc_raw <= 10) {
            ts->open_circuit[ch] = true;   /* Very low = NTC open (infinite resistance) */
            ts->temp_c[ch] = -127.0f;       /* Invalid temperature */
            ESP_LOGW(TAG, "Thermistor %d: open circuit (ADC=%d)", ch, adc_raw);
            continue;
        }
        if (adc_raw >= 4085) {
            ts->short_circuit[ch] = true;   /* Very high = NTC short (zero resistance) */
            ts->temp_c[ch] = 200.0f;        /* Invalid temperature */
            ESP_LOGW(TAG, "Thermistor %d: short circuit (ADC=%d)", ch, adc_raw);
            continue;
        }

        /* Convert ADC → resistance → temperature */
        float resistance = temp_sensor_adc_to_resistance((uint16_t)adc_raw);
        float temp = temp_sensor_resistance_to_temp(resistance);
        ts->temp_c[ch] = temp;

        /* Clear fault flags for valid reading */
        ts->open_circuit[ch] = false;
        ts->short_circuit[ch] = false;
    }

    /* Average thermistors per zone (2 per zone) */
    for (int z = 0; z < NUM_ZONES; z++) {
        int ch1 = z * 2;
        int ch2 = z * 2 + 1;

        /* Use valid thermistor readings only */
        bool t1_valid = !ts->open_circuit[ch1] && !ts->short_circuit[ch1];
        bool t2_valid = !ts->open_circuit[ch2] && !ts->short_circuit[ch2];

        if (t1_valid && t2_valid) {
            ts->zone_temp[z] = (ts->temp_c[ch1] + ts->temp_c[ch2]) / 2.0f;
        } else if (t1_valid) {
            ts->zone_temp[z] = ts->temp_c[ch1];
        } else if (t2_valid) {
            ts->zone_temp[z] = ts->temp_c[ch2];
        }
        /* If both invalid, keep previous reading */
    }
}

float temp_sensor_get_zone_temp(temp_sensor_t *ts, uint8_t zone)
{
    if (zone >= NUM_ZONES) return -127.0f;
    return ts->zone_temp[zone];
}

float temp_sensor_adc_to_resistance(uint16_t adc_val)
{
    /*
     * Voltage divider: 3.3V ---[R_SERIES 10kΩ]---+---[NTC]--- GND
     *                                               |
     *                                          ADC input
     *
     * V_adc = 3.3 * R_ntc / (R_series + R_ntc)
     * R_ntc = R_series * V_adc / (3.3 - V_adc)
     *       = R_series * adc_val / (4095 - adc_val)
     */
    if (adc_val >= 4095) return 1000000.0f;  /* Open circuit */
    if (adc_val == 0) return 0.01f;          /* Short circuit */

    return (float)R_SERIES * (float)adc_val / (4095.0f - (float)adc_val);
}

float temp_sensor_resistance_to_temp(float resistance)
{
    /*
     * Simplified Steinhart-Hart equation (Beta parameter equation):
     * 1/T = 1/T0 + (1/Beta) * ln(R/R0)
     *
     * T0 = 298.15K (25°C)
     * R0 = 10000Ω (resistance at T0)
     * Beta = 3950
     */
    if (resistance <= 0.0f) return -127.0f;

    float t_inv = (1.0f / T_NOMINAL) + (1.0f / BETA) * logf(resistance / R_NOMINAL);
    float temp_k = 1.0f / t_inv;
    float temp_c = temp_k - 273.15f;

    return temp_c;
}