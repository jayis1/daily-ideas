/* preconc.c — Preconcentrator flash desorb controller
 *
 * Uses bang-bang control with a fast 50 Hz loop to achieve a ~3 second
 * ramp from ambient to 220 °C. The nichrome wire (0.1 mm, ~6 Ω) draws
 * ~2.5 W from the 5 V boost rail.
 */
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/adc.h"

#include "sdkconfig.h"
#include "preconc.h"

static const char *TAG = "preconc";

#define PREC_PIN_HEATER   3
#define PREC_PIN_NTC      6   /* ADC1_CH6 */
#define PREC_LEDC_CHAN    LEDC_CHANNEL_1
#define PREC_LEDC_TIMER   LEDC_TIMER_1
#define PREC_PWM_HZ       1000
#define PREC_PWM_RES      LEDC_TIMER_10_BIT

#define NTC_BETA   3950.0f
#define NTC_R0     10000.0f
#define NTC_T0     298.15f
#define NTC_PULLUP 10000.0f
#define ADC_VREF   3300.0f

static float s_temp = 25.0f;
static bool  s_active = false;

static float read_ntc(void)
{
    int raw = adc1_get_raw(ADC1_CHANNEL_6);
    float v = (float)raw * ADC_VREF / 4095.0f;
    if (v >= ADC_VREF - 1.0f) return 300.0f;
    float r = NTC_PULLUP * v / (ADC_VREF - v);
    if (r < 1.0f) r = 1.0f;
    float tk = 1.0f / (1.0f / NTC_T0 + (1.0f / NTC_BETA) * logf(r / NTC_R0));
    return tk - 273.15f;
}

float preconc_read_temp_c(void) { return s_temp; }
bool  preconc_heater_active(void) { return s_active; }

void preconc_heater_off(void)
{
    ledc_set_duty(PREC_LEDC_CHAN, 0);
    ledc_update_duty(PREC_LEDC_CHAN);
    s_active = false;
}

static void set_duty_pct(float pct)
{
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    uint32_t d = (uint32_t)(pct * (float)((1 << PREC_PWM_RES) - 1) / 100.0f);
    ledc_set_duty(PREC_LEDC_CHAN, d);
    ledc_update_duty(PREC_LEDC_CHAN);
    s_active = (pct > 0.1f);
}

void preconc_init(void)
{
    ESP_LOGI(TAG, "Initializing preconcentrator heater + NTC");
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);

    ledc_timer_config_t tim = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = PREC_PWM_RES,
        .timer_num = PREC_LEDC_TIMER,
        .freq_hz = PREC_PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&tim);
    ledc_channel_config_t ch = {
        .channel = PREC_LEDC_CHAN,
        .duty = 0,
        .gpio_num = PREC_PIN_HEATER,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_sel = PREC_LEDC_TIMER,
    };
    ledc_channel_config(&ch);
}

void preconc_flash_desorb(void)
{
    ESP_LOGI(TAG, "Flash desorb → 220°C");
    float target = (float)PLUME_PRECONC_DESORB_TEMP;

    /* Aggressive bang-bang ramp: 100% duty until target, then PID-ish hold */
    int64_t t_start = esp_timer_get_time();
    int hold_ms = PLUME_PRECONC_DESORB_TIME_S * 1000;

    /* Ramp phase: full power until we hit target */
    while (1) {
        s_temp = read_ntc();
        if (s_temp > PLUME_HEATER_WATCHDOG_TEMP_C) {
            ESP_LOGE(TAG, "OVERTEMP %.1f°C — abort!", s_temp);
            preconc_heater_off();
            return;
        }
        if (s_temp >= target) break;
        set_duty_pct(100.0f);
        vTaskDelay(pdMS_TO_TICKS(20));
    }

    int64_t t_ramp = esp_timer_get_time() - t_start;
    ESP_LOGI(TAG, "Ramp to 220°C in %.1fs", t_ramp / 1000.0f);

    /* Hold phase: maintain target for the desorb duration */
    int64_t t_hold_end = esp_timer_get_time() + hold_ms * 1000;
    while (esp_timer_get_time() < t_hold_end) {
        s_temp = read_ntc();
        if (s_temp > PLUME_HEATER_WATCHDOG_TEMP_C) {
            ESP_LOGE(TAG, "OVERTEMP during hold — abort!");
            break;
        }
        /* Simple proportional hold */
        float err = target - s_temp;
        set_duty_pct(err > 2 ? 60.0f : (err > 0 ? 25.0f : 0.0f));
        vTaskDelay(pdMS_TO_TICKS(20));
    }

    preconc_heater_off();
    ESP_LOGI(TAG, "Desorb complete, heater off");
}