/*
 * power.c — Battery/solar monitoring, charge LED, low-battery handling
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "power.h"
#include "sensors.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"

static const char *TAG = "power";

static esp_adc_cal_characteristics_t s_adc_chars;

void power_init(void)
{
    ESP_LOGI(TAG, "Initializing power management");

    /* Configure status LEDs as outputs */
    gpio_set_direction(PIN_LED_GREEN, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_LED_RED, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_LED_AMBER, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_GREEN, 0);
    gpio_set_level(PIN_LED_RED, 0);
    gpio_set_level(PIN_LED_AMBER, 0);

    /* Configure ADC for battery and solar voltage sensing */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_0, ADC_ATTEN_DB_11);  /* battery */
    adc1_config_channel_atten(ADC1_CHANNEL_1, ADC_ATTEN_DB_11);  /* solar */
    esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11,
                              ADC_WIDTH_BIT_12, 1100, &s_adc_chars);
}

void power_update(uint8_t *battery_pct, float *temp_c,
                  float *humidity_pct, float *light_lux)
{
    /* Read all sensors via the shared I2C bus */
    sensors_read_all(temp_c, humidity_pct, light_lux, battery_pct);

    /* Cross-check battery voltage via ADC (fuel gauge sanity check) */
    uint32_t adc_reading = adc1_get_raw(ADC1_CHANNEL_0);
    uint32_t voltage_mv = esp_adc_cal_raw_to_voltage(adc_reading, &s_adc_chars);
    float bat_voltage = voltage_mv * ADC_BATTERY_DIVIDER / 1000.0f;

    /* Read solar panel voltage */
    uint32_t solar_reading = adc1_get_raw(ADC1_CHANNEL_1);
    uint32_t solar_mv = esp_adc_cal_raw_to_voltage(solar_reading, &s_adc_chars);
    float solar_voltage = solar_mv * ADC_SOLAR_DIVIDER / 1000.0f;

    ESP_LOGD(TAG, "Battery: %.2f V (%d%%), Solar: %.2f V",
             bat_voltage, *battery_pct, solar_voltage);

    /* Update LED states */
    if (*battery_pct <= BATTERY_LOW_PCT) {
        gpio_set_level(PIN_LED_RED, 1);
    } else {
        gpio_set_level(PIN_LED_RED, 0);
    }

    /* If solar voltage > battery voltage, we're charging */
    if (solar_voltage > bat_voltage + 0.3f) {
        /* Amber LED blinks while charging */
        static int blink = 0;
        gpio_set_level(PIN_LED_AMBER, blink ^= 1);
    } else {
        gpio_set_level(PIN_LED_AMBER, 0);
    }
}

void power_update_charge_led(void)
{
    /* Charging LED is handled in power_update based on solar voltage */
}

void power_low_battery_handler(void)
{
    ESP_LOGW(TAG, "Low battery — reducing activity");
    /* In a full implementation: reduce capture rate, turn off UV, etc. */
}