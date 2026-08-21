/*
 * Therma Weave — ESP32-C3 Multi-Zone Heated Textile Controller
 * app_main.c — Entry point, NVS init, task launch
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "driver/ledc.h"
#include "driver/i2c.h"

#include "zone_controller.h"
#include "temp_sensor.h"
#include "current_monitor.h"
#include "ble_service.h"
#include "oled_display.h"
#include "activity_detect.h"
#include "ambient_sensor.h"
#include "power_manager.h"
#include "safety_watchdog.h"
#include "nvs_storage.h"

static const char *TAG = "THERMA_WEAVE";

/* ========== GPIO Pin Definitions ========== */

#define I2C_SDA_PIN        0
#define I2C_SCL_PIN        1
#define ZONE0_PWM_PIN      2
#define ZONE1_PWM_PIN      3
#define ZONE2_PWM_PIN      4
#define ZONE3_PWM_PIN      5
#define MUX_A_PIN          6
#define MUX_B_PIN          7
#define MUX_C_PIN          8
#define MUX_EN_PIN         9
#define THERM_ADC_PIN      10  /* ADC2_CH0 */
#define CURRENT_ALERT_PIN  11
#define VBAT_ADC_PIN       21  /* ADC2_CH1 */
#define SAFETY_SHUTDOWN_PIN 20

/* ========== I2C Configuration ========== */

#define I2C_MASTER_NUM     I2C_NUM_0
#define I2C_MASTER_FREQ_HZ 400000
#define I2C_MASTER_TIMEOUT_MS 100

/* ========== PWM Configuration ========== */

#define LEDC_TIMER         LEDC_TIMER_0
#define LEDC_SPEED_MODE    LEDC_LOW_SPEED_MODE
#define LEDC_DUTY_RES      LEDC_TIMER_10_BIT  /* 0-1023 */
#define LEDC_FREQ_HZ       1000               /* 1 kHz PWM */

static const int zone_pwm_pins[NUM_ZONES] = {
    ZONE0_PWM_PIN, ZONE1_PWM_PIN, ZONE2_PWM_PIN, ZONE3_PWM_PIN
};

static const ledc_channel_t zone_ledc_channels[NUM_ZONES] = {
    LEDC_CHANNEL_0, LEDC_CHANNEL_1, LEDC_CHANNEL_2, LEDC_CHANNEL_3
};

/* ========== Global State ========== */

static zone_controller_t zones[NUM_ZONES];
static temp_sensor_t     temp_sens;
static current_monitor_t current_mon;
static ambient_sensor_t  ambient;
static activity_detect_t  activity;
static oled_display_t    oled;
static safety_watchdog_t safety;

/* ========== I2C Master Init ========== */

static esp_err_t i2c_master_init(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA_PIN,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = I2C_SCL_PIN,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t err = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (err != ESP_OK) return err;
    return i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
}

/* ========== PWM Init ========== */

static void pwm_init(void)
{
    ledc_timer_config_t timer_conf = {
        .speed_mode     = LEDC_SPEED_MODE,
        .duty_resolution = LEDC_DUTY_RES,
        .timer_num       = LEDC_TIMER,
        .freq_hz         = LEDC_FREQ_HZ,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_conf);

    for (int i = 0; i < NUM_ZONES; i++) {
        ledc_channel_config_t ch_conf = {
            .gpio_num   = zone_pwm_pins[i],
            .speed_mode = LEDC_SPEED_MODE,
            .channel    = zone_ledc_channels[i],
            .intr_type  = LEDC_INTR_DISABLE,
            .timer_sel   = LEDC_TIMER,
            .duty       = 0,  /* Start with heaters OFF */
            .hpoint     = 0,
        };
        ledc_channel_config(&ch_conf);
    }
}

/* ========== MUX GPIO Init ========== */

static void mux_gpio_init(void)
{
    gpio_config_t mux_conf = {
        .pin_bit_mask = (1ULL << MUX_A_PIN) | (1ULL << MUX_B_PIN) |
                        (1ULL << MUX_C_PIN) | (1ULL << MUX_EN_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&mux_conf);

    /* Disable mux by default (active low enable) */
    gpio_set_level(MUX_EN_PIN, 1);
    gpio_set_level(MUX_A_PIN, 0);
    gpio_set_level(MUX_B_PIN, 0);
    gpio_set_level(MUX_C_PIN, 0);
}

/* ========== Safety Shutdown GPIO Init ========== */

static void safety_gpio_init(void)
{
    gpio_config_t safety_conf = {
        .pin_bit_mask = (1ULL << SAFETY_SHUTDOWN_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&safety_conf);

    /* Safety shutdown is active HIGH (OR gate to MOSFET enables) */
    /* LOW = heaters enabled, HIGH = all heaters forced OFF */
    gpio_set_level(SAFETY_SHUTDOWN_PIN, 0);

    /* Current alert input */
    gpio_config_t alert_conf = {
        .pin_bit_mask = (1ULL << CURRENT_ALERT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&alert_conf);
}

/* ========== ADC Init ========== */

static void adc_init(void)
{
    adc2_config_channel_atten(ADC2_CHANNEL_0, ADC_ATTEN_DB_11);  /* Thermistor mux */
    adc2_config_channel_atten(ADC2_CHANNEL_1, ADC_ATTEN_DB_11);  /* Battery voltage */
}

/* ========== FreeRTOS Tasks ========== */

static void temp_sensor_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Temperature sensor task started");

    while (1) {
        /* Scan all 8 thermistor channels through the mux */
        temp_sensor_scan_all(&temp_sens);

        /* Update zone controllers with new temperature readings */
        for (int z = 0; z < NUM_ZONES; z++) {
            float temp = temp_sensor_get_zone_temp(&temp_sens, z);
            zone_controller_update_temp(&zones[z], temp);
        }

        vTaskDelay(pdMS_TO_TICKS(250));  /* 4 updates/sec per zone (2 thermistors, 2Hz each) */
    }
}

static void pid_control_task(void *pvParameters)
{
    ESP_LOGI(TAG, "PID control task started");

    while (1) {
        uint64_t now = esp_timer_get_time();

        for (int z = 0; z < NUM_ZONES; z++) {
            if (!zones[z].enabled) {
                ledc_set_duty(LEDC_SPEED_MODE, zone_ledc_channels[z], 0);
                ledc_update_duty(LEDC_SPEED_MODE, zone_ledc_channels[z]);
                continue;
            }

            /* Check if safety shutdown is active */
            if (safety_watchdog_is_shutdown(&safety)) {
                ledc_set_duty(LEDC_SPEED_MODE, zone_ledc_channels[z], 0);
                ledc_update_duty(LEDC_SPEED_MODE, zone_ledc_channels[z]);
                continue;
            }

            /* Run PID calculation */
            float duty_pct = zone_controller_pid_compute(&zones[z], now);

            /* Convert duty % to 10-bit PWM value */
            uint32_t duty_raw = (uint32_t)(duty_pct * 1023.0f / 100.0f);
            if (duty_raw > 972) duty_raw = 972;  /* Cap at 95% */

            ledc_set_duty(LEDC_SPEED_MODE, zone_ledc_channels[z], duty_raw);
            ledc_update_duty(LEDC_SPEED_MODE, zone_ledc_channels[z]);

            zones[z].duty_pct = duty_pct;
        }

        vTaskDelay(pdMS_TO_TICKS(250));  /* 4 Hz PID loop */
    }
}

static void current_monitor_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Current monitor task started");

    while (1) {
        /* Read current from INA199 (cycling through zones via mux) */
        for (int z = 0; z < NUM_ZONES; z++) {
            float current_ma = current_monitor_read_zone(&current_mon, z);
            zones[z].current_ma = current_ma;

            /* Check for over-current */
            if (current_ma > 4000.0f) {
                ESP_LOGE(TAG, "Zone %d over-current: %.0f mA", z, current_ma);
                safety_watchdog_fault(&safety, FAULT_OVERCURRENT, z);
                zones[z].enabled = false;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(100));  /* 10 Hz per zone */
    }
}

static void activity_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Activity detection task started");

    while (1) {
        activity_detect_update(&activity);

        /* Adjust zone target temperatures based on activity level */
        float offset = 0.0f;
        switch (activity.level) {
        case ACTIVITY_STILL:   offset = 0.0f;  break;  /* Full target temp */
        case ACTIVITY_WALKING: offset = -3.0f; break;  /* Reduce by 3°C */
        case ACTIVITY_RUNNING: offset = -6.0f; break;  /* Reduce by 6°C */
        default:               offset = 0.0f;  break;
        }

        for (int z = 0; z < NUM_ZONES; z++) {
            zones[z].activity_offset = offset;
        }

        vTaskDelay(pdMS_TO_TICKS(20));  /* 50 Hz IMU sample rate */
    }
}

static void oled_task(void *pvParameters)
{
    ESP_LOGI(TAG, "OLED display task started");

    while (1) {
        oled_display_update(&oled, zones, &ambient, &activity, &safety);
        vTaskDelay(pdMS_TO_TICKS(1000));  /* 1 Hz display update */
    }
}

static void power_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Power management task started");

    while (1) {
        float vbat = power_manager_read_battery(&current_mon);
        ESP_LOGI(TAG, "Battery: %.2f V", vbat);

        /* Low battery cutoff at 10.5V (3S LiPo minimum) */
        if (vbat < 10.5f && vbat > 1.0f) {
            ESP_LOGW(TAG, "Low battery! Shutting down all zones.");
            for (int z = 0; z < NUM_ZONES; z++) {
                zones[z].enabled = false;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(10000));  /* 0.1 Hz battery check */
    }
}

/* ========== Main ========== */

void app_main(void)
{
    ESP_LOGI(TAG, "=== Therma Weave v1.0 ===");
    ESP_LOGI(TAG, "Multi-Zone Heated Textile Controller");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize peripherals */
    i2c_master_init();
    adc_init();
    pwm_init();
    mux_gpio_init();
    safety_gpio_init();

    /* Initialize subsystems */
    nvs_storage_init();
    temp_sensor_init(&temp_sens, MUX_A_PIN, MUX_B_PIN, MUX_C_PIN, MUX_EN_PIN);
    current_monitor_init(&current_mon, I2C_MASTER_NUM);
    ambient_sensor_init(&ambient, I2C_MASTER_NUM);
    activity_detect_init(&activity, I2C_MASTER_NUM);
    oled_display_init(&oled, I2C_MASTER_NUM);
    safety_watchdog_init(&safety, SAFETY_SHUTDOWN_PIN);
    ble_service_init();

    /* Load saved zone settings from NVS */
    nvs_storage_load_zones(zones);

    /* Initialize zone controllers with default PID parameters */
    for (int z = 0; z < NUM_ZONES; z++) {
        zone_controller_init(&zones[z], z);
        /* Default target: 40°C, initially disabled */
        zones[z].target_temp = nvs_storage_get_target(z);
        if (zones[z].target_temp == 0) zones[z].target_temp = 40.0f;
        zones[z].enabled = false;  /* Start disabled for safety */
    }

    /* Set BLE callbacks */
    ble_service_set_zone_controllers(zones);
    ble_service_set_safety_watchdog(&safety);

    /* Create FreeRTOS tasks */
    xTaskCreate(safety_watchdog_task,  "safety",  2048, &safety,    8, NULL);
    xTaskCreate(pid_control_task,      "pid",     4096, NULL,       7, NULL);
    xTaskCreate(current_monitor_task,  "current", 2048, NULL,       6, NULL);
    xTaskCreate(temp_sensor_task,      "temp",    4096, NULL,       5, NULL);
    xTaskCreate(activity_task,         "imu",     2048, NULL,       4, NULL);
    xTaskCreate(ble_service_task,      "ble",     4096, NULL,       3, NULL);
    xTaskCreate(oled_task,             "oled",    3072, NULL,       2, NULL);
    xTaskCreate(power_task,            "power",   2048, NULL,       1, NULL);

    ESP_LOGI(TAG, "All tasks started. Waiting for BLE connection...");

    /* Main loop is empty — all work is in FreeRTOS tasks */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}