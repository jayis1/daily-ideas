/* column.c — PID column heater control + temperature program executor
 *
 * PID loop runs at 10 Hz. The nichrome band is driven by a 200 Hz PWM
 * (LEDC channel 0) on GPIO4 through an IRLML2502 MOSFET.
 *
 * Temperature is read from a 10 kΩ NTC (β=3950) in a voltage divider
 * with a 10 kΩ pull-up to 3.3 V on GPIO5 (ADC1_CH4):
 *
 *   V_therm = 3.3 * R_ntc / (R_ntc + 10k)
 *   R_ntc   = 10k * V_therm / (3.3 - V_therm)
 *   T(K)    = 1 / (1/T0 + (1/β) * ln(R/R0))     with T0=298.15K, R0=10k
 */
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/adc.h"
#include "driver/ledc.h"

#include "sdkconfig.h"
#include "column.h"

static const char *TAG = "column";

/* ---- Pin map ---- */
#define COL_PIN_HEATER    4
#define COL_PIN_NTC       5    /* ADC1_CH4 */
#define COL_PIN_FAN       16

/* ---- LEDC PWM config ---- */
#define COL_LEDC_TIMER    LEDC_TIMER_0
#define COL_LEDC_CHANNEL  LEDC_CHANNEL_0
#define COL_PWM_FREQ_HZ   200
#define COL_PWM_RESOLUTION LEDC_TIMER_10_BIT

/* ---- NTC constants ---- */
#define NTC_BETA          3950.0f
#define NTC_R0            10000.0f
#define NTC_T0            298.15f
#define NTC_PULLUP        10000.0f
#define ADC_VREF          3300.0f

/* ---- PID state ---- */
static float    s_kp = 8.0f, s_ki = 0.5f, s_kd = 2.0f;
static float    s_integral = 0.0f;
static float    s_prev_err = 0.0f;
static float    s_current_temp = 25.0f;
static float    s_target_temp = 25.0f;
static bool     s_heater_active = false;
static bool     s_ramp_done = false;
static TaskHandle_t s_pid_task_handle = NULL;

static column_method_t s_method = {
    .start_temp_c   = 35.0f,
    .hold_start_s   = 10,
    .ramp_c_per_min = 10.0f,
    .final_temp_c   = 180.0f,
    .hold_final_s   = 30,
};

/* ---- Temperature readout ---- */
static float read_ntc_temp(void)
{
    int raw = adc1_get_raw(ADC1_CHANNEL_4);
    float v = (float)raw * ADC_VREF / 4095.0f;
    if (v >= ADC_VREF - 1.0f) return 300.0f;  /* open circuit → hot fail-safe */
    float r_ntc = NTC_PULLUP * v / (ADC_VREF - v);
    if (r_ntc < 1.0f) r_ntc = 1.0f;
    float t_kelvin = 1.0f / (1.0f / NTC_T0 + (1.0f / NTC_BETA) * logf(r_ntc / NTC_R0));
    return t_kelvin - 273.15f;
}

float column_read_temp_c(void) { return s_current_temp; }
float column_read_target_c(void) { return s_target_temp; }
bool  column_heater_active(void) { return s_heater_active; }

void column_set_method(const column_method_t *m)
{
    memcpy(&s_method, m, sizeof(column_method_t));
}

const column_method_t *column_get_method(void) { return &s_method; }

void column_heater_off(void)
{
    ledc_set_duty(COL_LEDC_CHANNEL, 0);
    ledc_update_duty(COL_LEDC_CHANNEL);
    s_heater_active = false;
}

static void set_heater_duty_pct(float pct)
{
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    uint32_t duty = (uint32_t)(pct * (float)((1 << COL_PWM_RESOLUTION) - 1) / 100.0f);
    ledc_set_duty(COL_LEDC_CHANNEL, duty);
    ledc_update_duty(COL_LEDC_CHANNEL);
    s_heater_active = (pct > 0.1f);
}

/* ---- Temperature-program executor task ---- */
static void column_program_task(void *arg)
{
    ESP_LOGI(TAG, "Column program: hold %.1f°C for %ds, ramp %.1f°C/min to %.1f°C, hold %ds",
             s_method.start_temp_c, s_method.hold_start_s,
             s_method.ramp_c_per_min, s_method.final_temp_c,
             s_method.hold_final_s);

    /* Phase 1: initial hold */
    s_target_temp = s_method.start_temp_c;
    for (int i = 0; i < s_method.hold_start_s * 10; i++) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    /* Phase 2: ramp */
    float temp = s_method.start_temp_c;
    float step = s_method.ramp_c_per_min / 60.0f / 10.0f; /* °C per 100ms tick */
    while (temp < s_method.final_temp_c) {
        temp += step;
        if (temp > s_method.final_temp_c) temp = s_method.final_temp_c;
        s_target_temp = temp;
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    /* Phase 3: final hold */
    s_target_temp = s_method.final_temp_c;
    for (int i = 0; i < s_method.hold_final_s * 10; i++) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    s_ramp_done = true;
    ESP_LOGI(TAG, "Column program complete");
    vTaskDelete(NULL);
}

/* ---- PID task (10 Hz) ---- */
static void column_pid_task(void *arg)
{
    ESP_LOGI(TAG, "PID task started at 10 Hz");
    while (1) {
        s_current_temp = read_ntc_temp();

        /* Safety watchdog */
        if (s_current_temp > PLUME_HEATER_WATCHDOG_TEMP_C) {
            ESP_LOGE(TAG, "OVERTEMP %.1f°C — heater cutoff!", s_current_temp);
            column_heater_off();
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        float err = s_target_temp - s_current_temp;
        s_integral += err * 0.1f;
        if (s_integral > 80.0f) s_integral = 80.0f;   /* anti-windup */
        if (s_integral < 0.0f) s_integral = 0.0f;
        float deriv = (err - s_prev_err) / 0.1f;
        s_prev_err = err;

        float out = s_kp * err + s_ki * s_integral + s_kd * deriv;
        set_heater_duty_pct(out);

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void column_init(void)
{
    ESP_LOGI(TAG, "Initializing column heater + NTC");

    /* ADC for NTC */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_4, ADC_ATTEN_DB_11);

    /* LEDC PWM for heater */
    ledc_timer_config_t tim = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = COL_PWM_RESOLUTION,
        .timer_num = COL_LEDC_TIMER,
        .freq_hz = COL_PWM_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&tim);

    ledc_channel_config_t ch = {
        .channel = COL_LEDC_CHANNEL,
        .duty = 0,
        .gpio_num = COL_PIN_HEATER,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_sel = COL_LEDC_TIMER,
    };
    ledc_channel_config(&ch);

    /* Fan GPIO */
    gpio_config_t fan = {
        .pin_bit_mask = (1ULL << COL_PIN_FAN),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&fan);
    gpio_set_level(COL_PIN_FAN, 0);

    /* Start PID task */
    xTaskCreate(column_pid_task, "col_pid", 3072, NULL, 8, &s_pid_task_handle);
}

void column_start_ramp(void)
{
    s_ramp_done = false;
    s_integral = 0;
    s_prev_err = 0;
    s_target_temp = s_method.start_temp_c;
    xTaskCreate(column_program_task, "col_prog", 2048, NULL, 9, NULL);
}

void column_wait_done(void)
{
    while (!s_ramp_done) vTaskDelay(pdMS_TO_TICKS(200));
}

void column_cooldown(void)
{
    ESP_LOGI(TAG, "Starting active cooldown");
    s_target_temp = 25.0f;
    gpio_set_level(COL_PIN_FAN, 1);
}

void column_wait_cooldown(void)
{
    while (s_current_temp > 40.0f) {
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    gpio_set_level(COL_PIN_FAN, 0);
    ESP_LOGI(TAG, "Cooldown complete: %.1f°C", s_current_temp);
}