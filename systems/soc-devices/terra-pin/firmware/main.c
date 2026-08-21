/**
 * terra_pin/main.c — Terra Pin Soil Microbiome Activity Probe
 *
 * ESP32-S3-WROOM-1 main firmware. FreeRTOS tasks:
 *   flux_task      — SCD41 chamber CO2 rise rate → respiration
 *   ambient_task   — SCD41 ambient CO2 baseline
 *   orp_task       — EZO-ORP redox potential (mV)
 *   ec_task        — EZO-EC conductivity (µS/cm)
 *   moisture_task  — capacitive VWC via PCNT frequency
 *   temp_task      — DS18B20 soil temperature
 *   shi_task       — Soil Health Index fusion (0–100)
 *   display_task   — SH1106 OLED UI
 *   sdlog_task     — FAT32 CSV logging
 *   ble_task       — BLE GATT notifications
 *   button_task    — button + encoder polling
 *
 * Build: see firmware/CMakeLists.txt
 */

#include "main.h"
#include "scd41.h"
#include "ezo_orp.h"
#include "ezo_ec.h"
#include "ds18b20.h"
#include "moisture.h"
#include "sh1106.h"

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_sleep.h"
#include "nvs_flash.h"
#include "driver/adc.h"
#include "driver/rmt_tx.h"
#include "led_strip.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include <math.h>
#include <string.h>

static const char *TAG = "TERRA";

/* ── Global state ─────────────────────────────────────────────────── */

QueueHandle_t      g_reading_queue;
SemaphoreHandle_t  g_i2c_mutex;
volatile terra_mode_t g_mode = MODE_POINT;
volatile bool      g_measure_trigger = false;

/* Latest sensor values (shared between tasks) */
static volatile uint16_t s_co2_chamber = 0;
static volatile uint16_t s_co2_ambient = 420;
static volatile int16_t  s_orp_mv = 0;
static volatile uint16_t s_ec_us = 0;
static volatile float    s_moisture_vwc = 0.0f;
static volatile float    s_temp_c = 20.0f;
static volatile float    s_pressure_hpa = 1013.0f;
static volatile float    s_humidity_pct = 50.0f;

/* CO2 flux slope (computed by flux_task) */
static volatile float    s_flux_ppm_min = 0.0f;
static volatile float    s_flux_mgC = 0.0f;

static led_strip_handle_t s_led_strip;
static uint32_t g_session_id = 0;

/* ── Utility: Unix time (simple compile-time sync, no NTP in point mode) ── */

static uint64_t s_boot_time_us = 0;

uint64_t rtc_get_unix_time(void)
{
    if (s_boot_time_us == 0)
        return esp_timer_get_time() / 1000000ULL;
    return s_boot_time_us / 1000000ULL + esp_timer_get_time() / 1000000ULL;
}

void rtc_sync_from_compile(void)
{
    s_boot_time_us = esp_timer_get_time();
}

/* ── RGB LED ──────────────────────────────────────────────────────── */

void rgb_set_color(uint8_t shi)
{
    uint8_t r, g, b;
    if (shi >= 70) {
        /* Green — healthy soil */
        r = 0; g = 80; b = 0;
    } else if (shi >= 50) {
        /* Yellow — moderate */
        r = 80; g = 60; b = 0;
    } else {
        /* Red — needs amendment */
        r = 80; g = 0; b = 0;
    }
    led_strip_set_pixel(s_led_strip, 0, r, g, b);
    led_strip_refresh(s_led_strip);
}

/* ── Battery monitoring ───────────────────────────────────────────── */

uint8_t battery_read_pct(void)
{
    /* ADC1 channel 1 = GPIO22 on ESP32-S3 (check datasheet mapping) */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_1, ADC_ATTEN_DB_11);

    int raw = adc1_get_raw(ADC1_CHANNEL_1);
    /* 2:1 divider: Vbat = raw * 2 * 3.3 / 4095 */
    float vbat = (float)raw * 2.0f * 3.3f / 4095.0f;

    /* LiPo: 4.2V = 100%, 3.0V = 0% */
    float pct = (vbat - 3.0f) / (4.2f - 3.0f) * 100.0f;
    if (pct > 100.0f) pct = 100.0f;
    if (pct < 0.0f)   pct = 0.0f;
    return (uint8_t)(pct + 0.5f);
}

/* ── CO2 flux computation ─────────────────────────────────────────── */

static void compute_flux(const float *co2_history, int n_samples,
                          float chamber_temp_c, float pressure_hpa)
{
    /* Linear regression slope: ppm per second → convert to ppm/min */
    if (n_samples < 2) {
        s_flux_ppm_min = 0.0f;
        s_flux_mgC = 0.0f;
        return;
    }

    /* Least squares: y = a + b*x, b = slope */
    float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
    for (int i = 0; i < n_samples; i++) {
        float x = (float)i;          /* sample index (5 s interval) */
        float y = co2_history[i];
        sum_x  += x;
        sum_y  += y;
        sum_xy += x * y;
        sum_x2 += x * x;
    }
    float n = (float)n_samples;
    float denom = n * sum_x2 - sum_x * sum_x;
    if (fabsf(denom) < 1e-6f) {
        s_flux_ppm_min = 0.0f;
        s_flux_mgC = 0.0f;
        return;
    }
    float slope = (n * sum_xy - sum_x * sum_y) / denom;
    /* slope = ppm per 5-second interval → ppm per minute */
    s_flux_ppm_min = slope * (60.0f / 5.0f);

    /* Convert ppm/min to mg CO2-C m⁻² h⁻¹:
     *   flux = (dC/dt) * V_chamber * P / (R * T) * M_C * (12/44)
     * where:
     *   dC/dt in ppm/min = s_flux_ppm_min
     *   V_chamber in L = CHAMBER_VOL_ML / 1000
     *   P in Pa = pressure_hpa * 100
     *   R = 8.314 J/(mol·K)
     *   T in K = chamber_temp_c + 273.15
     *   M_C = 12 g/mol (carbon fraction)
     *   44 g/mol = molar mass of CO2
     *   Area in m² = CHAMBER_AREA_CM2 / 10000
     *   Convert /min → /h: × 60
     */
    float V_L = CHAMBER_VOL_ML / 1000.0f;
    float P_Pa = pressure_hpa * 100.0f;
    float T_K = chamber_temp_c + 273.15f;
    float A_m2 = CHAMBER_AREA_CM2 / 10000.0f;

    /* moles of air in chamber = PV/RT */
    float n_air = P_Pa * (V_L * 1e-3f) / (8.314f * T_K);
    /* dC/dt in mol/min = (s_flux_ppm_min * 1e-6) * n_air */
    float dn_co2 = (s_flux_ppm_min * 1e-6f) * n_air;
    /* mg CO2-C per min = dn_co2 * 44 g/mol * 1000 mg/g * (12/44) = dn_co2 * 12000 */
    float mgC_per_min = dn_co2 * 12000.0f;
    /* per hour per m² */
    s_flux_mgC = mgC_per_min * 60.0f / A_m2;

    ESP_LOGI(TAG, "Flux: %.2f ppm/min → %.1f mg C m⁻² h⁻¹", s_flux_ppm_min, s_flux_mgC);
}

/* ── FreeRTOS tasks ───────────────────────────────────────────────── */

/**
 * flux_task — Chamber CO2 measurement for soil respiration rate.
 * In point mode: triggered by MEASURE button, runs 60 s.
 * In continuous mode: runs continuously with 5 s periodic measurement.
 */
static void flux_task(void *arg)
{
    float co2_history[16];  /* max 60s / 5s = 12 samples, use 16 for safety */
    int sample_count = 0;

    while (1) {
        if (g_mode == MODE_POINT && !g_measure_trigger) {
            vTaskDelay(pdMS_TO_TICKS(200));
            continue;
        }

        ESP_LOGI(TAG, "Starting CO2 flux measurement (60 s)");
        sample_count = 0;
        scd41_start_periodic_chamber();

        for (int i = 0; i < 12; i++) {
            uint16_t co2;
            float temp, rh;
            esp_err_t ret = scd41_measure_chamber(&co2, &temp, &rh);
            if (ret == ESP_OK) {
                s_co2_chamber = co2;
                co2_history[sample_count++] = (float)co2;
                s_humidity_pct = rh;
                /* Use SCD41 temperature as chamber temp, fall back to DS18B20 */
            }
            vTaskDelay(pdMS_TO_TICKS(5000));  /* SCD41 periodic = 5 s */
        }

        scd41_stop_periodic_chamber();

        /* Compute flux slope */
        float chamber_temp = (s_temp_c > 0) ? s_temp_c : 20.0f;
        compute_flux(co2_history, sample_count, chamber_temp, s_pressure_hpa);

        if (g_mode == MODE_POINT)
            g_measure_trigger = false;  /* one-shot complete */
        else
            vTaskDelay(pdMS_TO_TICKS(10000));  /* continuous: 10 s gap */
    }
}

/**
 * ambient_task — Periodically reads ambient CO2 from the handle sensor.
 */
static void ambient_task(void *arg)
{
    while (1) {
        uint16_t co2;
        float temp, rh;
        esp_err_t ret = scd41_measure_ambient(&co2, &temp, &rh);
        if (ret == ESP_OK) {
            s_co2_ambient = co2;
            ESP_LOGI(TAG, "Ambient CO2: %u ppm", co2);
        }
        vTaskDelay(pdMS_TO_TICKS(AMBIENT_UPDATE_MS));
    }
}

/**
 * orp_task — Reads redox potential from EZO-ORP.
 */
static void orp_task(void *arg)
{
    while (1) {
        if (g_mode == MODE_POINT && !g_measure_trigger) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        int16_t orp;
        if (ezo_orp_read(&orp) == ESP_OK)
            s_orp_mv = orp;
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

/**
 * ec_task — Reads electrical conductivity from EZO-EC.
 * Sends temperature compensation from DS18B20 before each reading.
 */
static void ec_task(void *arg)
{
    while (1) {
        if (g_mode == MODE_POINT && !g_measure_trigger) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }

        /* Send temperature compensation to EZO-EC */
        char t_cmd[16];
        snprintf(t_cmd, sizeof(t_cmd), "T,%.1f", s_temp_c);
        /* (would send via UART — simplified here) */

        uint16_t ec;
        if (ezo_ec_read(&ec) == ESP_OK)
            s_ec_us = ec;
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

/**
 * moisture_task — Reads capacitive moisture probe via PCNT.
 */
static void moisture_task(void *arg)
{
    while (1) {
        if (g_mode == MODE_POINT && !g_measure_trigger) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        float vwc;
        if (moisture_read(&vwc) == ESP_OK)
            s_moisture_vwc = vwc;
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/**
 * temp_task — Reads DS18B20 soil temperature.
 */
static void temp_task(void *arg)
{
    while (1) {
        float temp;
        if (ds18b20_read(&temp) == ESP_OK)
            s_temp_c = temp;
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

/**
 * shi_task — Fuses all sensor data into Soil Health Index.
 * Triggered after flux measurement completes, or periodically in
 * continuous mode.
 */
static void shi_task(void *arg)
{
    terra_reading_t reading;

    while (1) {
        /* Wait for measurement to complete (or continuous interval) */
        vTaskDelay(pdMS_TO_TICKS(5000));

        memset(&reading, 0, sizeof(reading));

        reading.co2_chamber  = s_co2_chamber;
        reading.co2_ambient  = s_co2_ambient;
        reading.flux_ppm_min = s_flux_ppm_min;
        reading.flux_mgC     = s_flux_mgC;
        reading.orp_mv       = s_orp_mv;
        reading.ec_us        = s_ec_us;
        reading.moisture_vwc = s_moisture_vwc;
        reading.temp_c       = s_temp_c;
        reading.pressure_hpa = s_pressure_hpa;
        reading.humidity_pct = s_humidity_pct;
        reading.timestamp    = (uint32_t)rtc_get_unix_time();
        reading.mode         = (uint8_t)g_mode;

        /* Compute SHI */
        shi_compute(&reading);
        reading.valid = true;

        /* Send to display, SD log, BLE */
        xQueueSend(g_reading_queue, &reading, 0);

        /* Update RGB LED */
        rgb_set_color(reading.shi);
    }
}

/**
 * display_task — Updates the OLED display at 10 Hz.
 */
static void display_task(void *arg)
{
    terra_reading_t last_reading;
    memset(&last_reading, 0, sizeof(last_reading));
    bool has_reading = false;

    while (1) {
        terra_reading_t r;
        if (xQueueReceive(g_reading_queue, &r, 0) == pdTRUE) {
            memcpy(&last_reading, &r, sizeof(r));
            has_reading = true;

            /* Log to SD */
            sdlog_write(&r, g_session_id);

            /* BLE notify */
            ble_notify_reading(&r);
        }

        uint8_t bat = battery_read_pct();
        if (has_reading)
            sh1106_update(&last_reading, bat, g_mode);

        vTaskDelay(pdMS_TO_TICKS(100));  /* 10 Hz */
    }
}

/**
 * button_task — Polls buttons and encoder at 100 Hz with debounce.
 */
static void button_task(void *arg)
{
    uint8_t btn_meas_state = 1, btn_mode_state = 1;
    uint8_t btn_meas_prev = 1, btn_mode_prev = 1;
    int meas_debounce = 0, mode_debounce = 0;

    while (1) {
        uint8_t meas = gpio_get_level(PIN_BTN_MEASURE);
        uint8_t mode = gpio_get_level(PIN_BTN_MODE);

        /* Debounce MEASURE button */
        if (meas != btn_meas_prev) {
            meas_debounce = 0;
            btn_meas_prev = meas;
        }
        if (++meas_debounce >= 5) {
            if (btn_meas_state == 1 && meas == 0) {
                ESP_LOGI(TAG, "MEASURE pressed");
                g_measure_trigger = true;
            }
            btn_meas_state = meas;
            meas_debounce = 5;
        }

        /* Debounce MODE button */
        if (mode != btn_mode_prev) {
            mode_debounce = 0;
            btn_mode_prev = mode;
        }
        if (++mode_debounce >= 5) {
            if (btn_mode_state == 1 && mode == 0) {
                g_mode = (terra_mode_t)((g_mode + 1) % 3);
                ESP_LOGI(TAG, "Mode → %d", g_mode);
            }
            btn_mode_state = mode;
            mode_debounce = 5;
        }

        vTaskDelay(pdMS_TO_TICKS(10));  /* 100 Hz */
    }
}

/* ── Main ─────────────────────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "=== Terra Pin Soil Microbiome Activity Probe ===");
    ESP_LOGI(TAG, "ESP32-S3-WROOM-1 firmware starting...");

    /* NVS init */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Sync RTC */
    rtc_sync_from_compile();

    /* Create sync primitives */
    g_i2c_mutex = xSemaphoreCreateMutex();
    g_reading_queue = xQueueCreate(8, sizeof(terra_reading_t));

    /* Initialize GPIO for buttons */
    gpio_set_direction(PIN_BTN_MEASURE, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIN_BTN_MEASURE, GPIO_PULLUP_ONLY);
    gpio_set_direction(PIN_BTN_MODE, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIN_BTN_MODE, GPIO_PULLUP_ONLY);

    /* Initialize WS2812B RGB LED */
    led_strip_config_t strip_cfg = {
        .strip_gpio_num = PIN_WS2812,
        .max_leds = 1,
    };
    led_strip_rmt_config_t rmt_cfg = {
        .resolution_hz = 10 * 1000 * 1000,
    };
    led_strip_new_rmt_device(&strip_cfg, &rmt_cfg, &s_led_strip);
    led_strip_clear(s_led_strip);

    /* Initialize sensors */
    scd41_init();
    ezo_orp_init();
    ezo_ec_init();
    ds18b20_init();
    moisture_init();
    sh1106_init();

    /* Initialize SD logging */
    if (sdlog_init() == ESP_OK) {
        g_session_id = 1;  /* simplified; sdlog_init sets the real value */
    }

    /* Initialize BLE */
    ble_init();

    ESP_LOGI(TAG, "All subsystems initialized. Starting tasks...");

    /* Create FreeRTOS tasks */
    xTaskCreate(flux_task,     "flux",     4096, NULL, 5, NULL);
    xTaskCreate(ambient_task,  "ambient",  3072, NULL, 3, NULL);
    xTaskCreate(orp_task,      "orp",      3072, NULL, 4, NULL);
    xTaskCreate(ec_task,       "ec",       3072, NULL, 4, NULL);
    xTaskCreate(moisture_task, "moisture", 2048, NULL, 3, NULL);
    xTaskCreate(temp_task,     "temp",     2048, NULL, 3, NULL);
    xTaskCreate(shi_task,      "shi",      4096, NULL, 6, NULL);
    xTaskCreate(display_task,  "display",  3072, NULL, 2, NULL);
    xTaskCreate(button_task,   "button",   2048, NULL, 3, NULL);

    ESP_LOGI(TAG, "Terra Pin ready. Press MEASURE to take a reading.");
}