/* pump.c — Sample pump + 3-way valve control */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/ledc.h"

#include "sdkconfig.h"
#include "pump.h"

static const char *TAG = "pump";

#define PUMP_PIN        2
#define VALVE_PIN       15
#define PUMP_LEDC_CHAN  LEDC_CHANNEL_2
#define PUMP_LEDC_TIMER LEDC_TIMER_2
#define PUMP_PWM_HZ     500
#define PUMP_PWM_RES    LEDC_TIMER_10_BIT

static int64_t s_sample_start_us = 0;
static bool    s_sampling = false;

void pump_init(void)
{
    ESP_LOGI(TAG, "Initializing pump PWM + valve GPIO");

    ledc_timer_config_t tim = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = PUMP_PWM_RES,
        .timer_num = PUMP_LEDC_TIMER,
        .freq_hz = PUMP_PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&tim);
    ledc_channel_config_t ch = {
        .channel = PUMP_LEDC_CHAN,
        .duty = 0,
        .gpio_num = PUMP_PIN,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_sel = PUMP_LEDC_TIMER,
    };
    ledc_channel_config(&ch);

    gpio_config_t v = {
        .pin_bit_mask = (1ULL << VALVE_PIN),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&v);
    valve_set(VALVE_CARRIER);
}

void pump_set(float speed_pct)
{
    if (speed_pct < 0) speed_pct = 0;
    if (speed_pct > 100) speed_pct = 100;
    uint32_t d = (uint32_t)(speed_pct * (float)((1 << PUMP_PWM_RES) - 1) / 100.0f);
    ledc_set_duty(PUMP_LEDC_CHAN, d);
    ledc_update_duty(PUMP_LEDC_CHAN);
}

void pump_off(void)
{
    ledc_set_duty(PUMP_LEDC_CHAN, 0);
    ledc_update_duty(PUMP_LEDC_CHAN);
}

void valve_set(valve_state_t s)
{
    gpio_set_level(VALVE_PIN, (int)s);
}

void pump_start_sampling(void)
{
    s_sample_start_us = esp_timer_get_time();
    s_sampling = true;
}

float pump_stop_sampling(void)
{
    if (!s_sampling) return 0;
    int64_t elapsed_s = (esp_timer_get_time() - s_sample_start_us) / 1000000;
    s_sampling = false;
    float ml = (float)elapsed_s * PLUME_PUMP_FLOW_ML_MIN / 60.0f;
    ESP_LOGI(TAG, "Sampled %.1f mL in %.1fs", ml, (float)elapsed_s);
    return ml;
}

float pump_sample_volume(void)
{
    if (!s_sampling) return 0;
    int64_t elapsed_s = (esp_timer_get_time() - s_sample_start_us) / 1000000;
    return (float)elapsed_s * PLUME_PUMP_FLOW_ML_MIN / 60.0f;
}