/* battery.c — 18650 voltage monitor via ADC divider
 *
 * 2:1 divider on GPIO13 (ADC1_CH3): Vbat → 100k → GPIO13 → 100k → GND
 * So Vbat = 2 × ADC_reading × 3.3V / 4095
 */
#include "esp_log.h"
#include "driver/adc.h"
#include "sdkconfig.h"
#include "battery.h"

static const char *TAG = "battery";

#define BAT_PIN_CHANNEL  ADC1_CHANNEL_3
#define DIVIDER_RATIO    2.0f
#define ADC_VREF_MV      3300.0f

void battery_init_internal(void)
{
    static bool init = false;
    if (!init) {
        adc1_config_channel_atten(BAT_PIN_CHANNEL, ADC_ATTEN_DB_11);
        init = true;
    }
}

float battery_read_mv(void)
{
    battery_init_internal();
    /* Average 8 readings */
    int sum = 0;
    for (int i = 0; i < 8; i++) sum += adc1_get_raw(BAT_PIN_CHANNEL);
    float avg = (float)sum / 8.0f;
    float v = avg * ADC_VREF_MV / 4095.0f * DIVIDER_RATIO;
    return v;
}

bool battery_ok_for_run(void)
{
    float v = battery_read_mv();
    if (v < PLUME_BATTERY_MIN_MV) {
        ESP_LOGW(TAG, "Battery %.0f mV < %d mV — run blocked", v, PLUME_BATTERY_MIN_MV);
        return false;
    }
    return true;
}