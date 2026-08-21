/*
 * kappa-pin / firmware / main / main.c
 * Main application — Kappa Pin thermal conductivity meter
 *
 * State machine, UI, BLE/Wi-Fi init, measurement orchestration.
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"

#include "adc24.h"
#include "heater.h"
#include "probe.h"
#include "measurement.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "ble_stream.h"
#include "wifi_web.h"
#include "flash_store.h"
#include "database.h"
#include "buttons.h"

static const char *TAG = "kappa-pin";

static material_t current_material = MAT_WET_SOIL;
static int menu_index = 0;

/* Menu items */
static const char *menu_items[] = {
    "Material: ",
    "Calibrate",
    "Info",
    "Reset Config",
    "Exit",
};
#define MENU_COUNT 5

/* ---- BLE command callback ---- */
static void ble_cmd_handler(uint8_t cmd, const uint8_t *payload, int len)
{
    switch (cmd) {
    case BLE_CMD_START:
        ESP_LOGI(TAG, "BLE: Start measurement");
        measurement_start(current_material);
        break;
    case BLE_CMD_STOP:
        ESP_LOGI(TAG, "BLE: Stop measurement");
        measurement_cancel();
        break;
    case BLE_CMD_SET_MATERIAL:
        if (len >= 1 && payload[0] < MAT_COUNT) {
            current_material = (material_t)payload[0];
            ESP_LOGI(TAG, "BLE: Material set to %d", current_material);
        }
        break;
    case BLE_CMD_CALIBRATE:
        ESP_LOGI(TAG, "BLE: Calibration requested");
        /* Run glycerin calibration measurement */
        current_material = MAT_LIQUID;
        measurement_start(MAT_LIQUID);
        break;
    default:
        ESP_LOGW(TAG, "BLE: Unknown cmd 0x%02x", cmd);
    }
}

/* ---- ADC handle for ESP32-S3 on-chip ADC (voltage monitor) ---- */
adc_oneshot_unit_handle_t adc1_handle = NULL;
adc_oneshot_unit_handle_t adc2_handle = NULL;

static void adc_internal_init(void)
{
    adc_oneshot_unit_init_cfg_t init1 = { .unit_id = ADC_UNIT_1 };
    adc_oneshot_new_unit(&init1, &adc1_handle);

    adc_oneshot_unit_init_cfg_t init2 = { .unit_id = ADC_UNIT_2 };
    adc_oneshot_new_unit(&init2, &adc2_handle);
}

/* ---- UI update task ---- */
static void ui_task(void *arg)
{
    (void)arg;
    meas_state_t last_state = MEAS_IDLE;
    int last_sample_count = 0;

    while (1) {
        meas_state_t state = measurement_get_state();
        const material_preset_t *preset = measurement_get_preset(current_material);
        const probe_info_t *pinfo = probe_get_info();

        float temp = probe_read_temperature();

        switch (state) {
        case MEAS_IDLE:
            oled_show_idle(temp, current_material, pinfo->name);
            break;

        case MEAS_ARMING:
            {
                float drift = 0;  /* Would compute from probe history */
                oled_show_arming(temp, drift, false);
            }
            break;

        case MEAS_BASELINE:
        case MEAS_HEATING:
            {
                int n = measurement_get_sample_count();
                if (n > 0) {
                    const meas_sample_t *s = measurement_get_samples(&n);
                    if (n > 0) {
                        oled_show_measuring(s[n-1].t_s, s[n-1].dt_mk,
                                           s[n-1].q_w, preset->power_w);
                    }
                }
            }
            break;

        case MEAS_COOLING:
            {
                int n = measurement_get_sample_count();
                if (n > 0) {
                    const meas_sample_t *s = measurement_get_samples(&n);
                    if (n > 0) {
                        oled_show_measuring(s[n-1].t_s, s[n-1].dt_mk, 0, 0);
                    }
                }
            }
            break;

        case MEAS_ANALYZING:
            oled_show_idle(temp, current_material, "Analyzing...");
            break;

        case MEAS_DONE:
            {
                const meas_result_t *r = measurement_get_result();
                if (state != last_state) {
                    oled_show_result(r);
                    /* Send via BLE */
                    ble_stream_send_result(r);
                    /* Update web UI */
                    wifi_web_update_result(r);
                    /* Log to SD */
                    if (sd_logger_is_mounted()) {
                        int count;
                        const meas_sample_t *samps = measurement_get_samples(&count);
                        sd_logger_start(r, current_material);
                        for (int i = 0; i < count; i++) {
                            sd_logger_write_sample(&samps[i]);
                        }
                        sd_logger_write_result(r);
                        sd_logger_close();
                    }
                    /* Find matching material */
                    int match = database_find_match(r->lambda, r->alpha);
                    if (match >= 0) {
                        ESP_LOGI(TAG, "Material match: %s", database_get_name(match));
                    }
                    /* Increment counter */
                    flash_store_increment_measurements();
                }
            }
            break;

        case MEAS_ERROR:
            oled_show_idle(temp, current_material, "ERROR");
            break;
        }

        /* Stream live samples via BLE during measurement */
        if (state == MEAS_HEATING || state == MEAS_COOLING) {
            int n = measurement_get_sample_count();
            if (n > last_sample_count && ble_stream_is_connected()) {
                const meas_sample_t *s = measurement_get_samples(&n);
                for (int i = last_sample_count; i < n; i++) {
                    ble_stream_send_sample(&s[i]);
                }
            }
            last_sample_count = n;
        } else {
            last_sample_count = 0;
        }

        last_state = state;
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* ---- Button handler task ---- */
static void button_task(void *arg)
{
    (void)arg;
    bool in_menu = false;

    while (1) {
        button_event_t ev = buttons_poll();

        if (ev == BTN_NONE) {
            vTaskDelay(pdMS_TO_TICKS(20));
            continue;
        }

        meas_state_t state = measurement_get_state();

        if (!in_menu) {
            /* Normal mode */
            switch (ev) {
            case BTN_MEASURE_PRESS:
                if (state == MEAS_IDLE || state == MEAS_DONE || state == MEAS_ERROR) {
                    ESP_LOGI(TAG, "Starting measurement: material=%d", current_material);
                    measurement_start(current_material);
                }
                break;

            case BTN_MODE_PRESS:
                if (state == MEAS_IDLE || state == MEAS_DONE) {
                    /* Cycle material preset */
                    current_material = (material_t)((current_material + 1) % (MAT_COUNT - 1));
                    ESP_LOGI(TAG, "Material: %s",
                             measurement_get_preset(current_material)->name);
                }
                break;

            case BTN_MENU_PRESS:
                if (state == MEAS_IDLE || state == MEAS_DONE) {
                    in_menu = true;
                    menu_index = 0;
                }
                break;

            case BTN_MEASURE_LONG:
                /* Long press = cancel */
                if (state != MEAS_IDLE) {
                    measurement_cancel();
                }
                break;

            default:
                break;
            }
        } else {
            /* Menu mode */
            switch (ev) {
            case BTN_MODE_PRESS:
                menu_index = (menu_index + 1) % MENU_COUNT;
                break;

            case BTN_MEASURE_PRESS:
                /* Select menu item */
                switch (menu_index) {
                case 0: /* Cycle material */
                    current_material = (material_t)((current_material + 1) % (MAT_COUNT - 1));
                    break;
                case 1: /* Calibrate */
                    measurement_start(MAT_LIQUID);
                    in_menu = false;
                    break;
                case 2: /* Info */
                    /* Display firmware version, probe, calibration */
                    break;
                case 3: /* Reset */
                    flash_store_reset();
                    break;
                case 4: /* Exit */
                    in_menu = false;
                    break;
                }
                if (menu_index != 0 && menu_index != 4) {
                    in_menu = false;
                }
                break;

            case BTN_MENU_PRESS:
                in_menu = false;
                break;

            default:
                break;
            }

            if (in_menu) {
                oled_show_menu(menu_index, menu_items, MENU_COUNT);
            }
        }
    }
}

/* ---- Main ---- */
void app_main(void)
{
    ESP_LOGI(TAG, "=== Kappa Pin — Pocket Thermal Conductivity Meter ===");
    ESP_LOGI(TAG, "Firmware v1.0 — ESP32-S3-WROOM-1");

    /* Initialize internal ADCs (for heater voltage monitor + probe ID) */
    adc_internal_init();

    /* Initialize NVS / flash storage */
    flash_store_init();
    const flash_config_t *cfg = flash_store_get();
    current_material = (material_t)cfg->last_material;

    /* Apply calibration to measurement engine */
    measurement_set_calibration(cfg->calibration_factor);

    /* Initialize SPI bus (shared by ADC, digital pot, OLED, SD) */
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = 5,   /* SPI_MOSI */
        .miso_io_num = 6,   /* SPI_MISO */
        .sclk_io_num = 7,   /* SPI_SCK */
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };
    esp_err_t ret = spi_bus_initialize(SPI_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
    }

    /* Initialize 24-bit ADC */
    ESP_ERROR_CHECK(adc24_init());

    /* Initialize heater driver */
    ESP_ERROR_CHECK(heater_init());

    /* Detect probe */
    probe_type_t pt = probe_detect();
    if (pt == PROBE_NONE) {
        ESP_LOGW(TAG, "No probe detected!");
    } else {
        const probe_info_t *pinfo = probe_get_info();
        heater_set_resistance(pinfo->heater_resistance);
        heater_set_length(pinfo->active_length);
        ESP_LOGI(TAG, "Probe: %s (%s)", pinfo->name, pinfo->standard);
    }

    /* Initialize OLED */
    oled_init();

    /* Initialize SD card logger */
    sd_err_t sd_err = sd_logger_init();
    if (sd_err != SD_OK) {
        ESP_LOGW(TAG, "SD card not available (err=%d)", sd_err);
    }

    /* Initialize buttons */
    buttons_init();

    /* Initialize BLE */
    ble_stream_init();
    ble_stream_set_cmd_callback(ble_cmd_handler);

    /* Initialize Wi-Fi AP + web server */
    wifi_web_init();

    /* Start measurement task (core 0) */
    xTaskCreatePinnedToCore(measurement_task, "meas", 8192, NULL, 5, NULL, 0);

    /* Start UI task (core 1) */
    xTaskCreatePinnedToCore(ui_task, "ui", 4096, NULL, 4, NULL, 1);

    /* Start button handler task (core 1) */
    xTaskCreatePinnedToCore(button_task, "btn", 2048, NULL, 3, NULL, 1);

    ESP_LOGI(TAG, "Initialization complete. Ready for measurements.");
    ESP_LOGI(TAG, "Connect via BLE (KappaPin) or Wi-Fi AP (KappaPin-XXXX)");

    /* Main loop — housekeeping */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        /* Periodic probe temperature monitoring */
        probe_update();

        /* Safety check: if heater somehow stuck on, kill it */
        if (heater_is_active()) {
            float dt = probe_read_temperature() - measurement_get_result()->t0_c;
            if (dt > (HEATER_MAX_TEMP_RISE_C + 2.0f)) {
                ESP_LOGE(TAG, "Safety: ΔT=%.2f K, emergency stop!", dt);
                heater_emergency_stop();
            }
        }
    }
}