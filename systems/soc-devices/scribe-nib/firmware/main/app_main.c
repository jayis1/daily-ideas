/*
 * Scribe Nib — Smart Pen Clip Handwriting Digitizer
 * app_main.c — Entry point, NVS init, task launch
 *
 * ESP32-S3-MINI-1 based pen-clip device that uses a 9-axis IMU to
 * track handwriting motion, recognizes characters with an on-device
 * CNN, and streams text over BLE HID keyboard.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "driver/i2c.h"
#include "driver/ledc.h"

#include "imu_driver.h"
#include "stroke_segmenter.h"
#include "trajectory_recon.h"
#include "char_recognizer.h"
#include "lang_model.h"
#include "ble_hid.h"
#include "ble_custom.h"
#include "oled_display.h"
#include "power_manager.h"
#include "calibration.h"
#include "gesture_handler.h"
#include "haptic_feedback.h"

static const char *TAG = "scribe_nib";

/* ---- Shared queues ---- */
static QueueHandle_t imu_sample_queue;    /* imu_sample_t items from ISR */
static QueueHandle_t stroke_queue;        /* stroke_event_t from segmenter */
static QueueHandle_t char_queue;          /* char_result_t from recognizer */

/* ---- User profile (NVS) ---- */
#define NVS_NAMESPACE   "scribenib"
#define NVS_PROFILE_KEY "profile"
static uint8_t active_profile = 0;

/* ---- Touch pad config for wake / mode switch ---- */
#define TOUCH_PAD_INNER  GPIO_NUM_1
#define TOUCH_PAD_OUTER  GPIO_NUM_2
#define BOOT_BUTTON      GPIO_NUM_15

static void init_gpio(void)
{
    /* Boot button with pull-up */
    gpio_config_t boot_cfg = {
        .pin_bit_mask = (1ULL << BOOT_BUTTON),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&boot_cfg);

    /* Capacitive touch pads (ESP32-S3 touch peripheral) */
    touch_pad_init();
    touch_pad_set_voltage(TOUCH_HVOLT_2V7, TOUCH_LVOLT_0V5, TOUCH_HVOLT_ATTEN_1V);
    touch_pad_config(TOUCH_PAD_NUM1);  /* inner clip */
    touch_pad_config(TOUCH_PAD_NUM2);  /* outer clip */
    touch_pad_filter_start(10);  /* 10ms filter period */

    ESP_LOGI(TAG, "GPIO and touch pads initialized");
}

static void init_spi_bus(void)
{
    spi_bus_config_t spi_cfg = {
        .mosi_io_num = GPIO_NUM_5,
        .miso_io_num = GPIO_NUM_0,
        .sclk_io_num = GPIO_NUM_4,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &spi_cfg, SPI_DMA_CH_AUTO));
    ESP_LOGI(TAG, "SPI bus initialized (HSPI)");
}

static void init_i2c_bus(void)
{
    i2c_config_t i2c_cfg = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = GPIO_NUM_7,
        .scl_io_num = GPIO_NUM_8,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 400000,  /* 400kHz fast mode */
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_NUM_0, &i2c_cfg));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0));
    ESP_LOGI(TAG, "I²C bus initialized at 400kHz");
}

/* ---- IMU sampling task (high priority, pinned to Core 1) ---- */
static void imu_task(void *arg)
{
    imu_sample_t samples[IMU_FIFO_WATERMARK];
    ESP_LOGI(TAG, "IMU task started on core %d", xPortGetCoreID());

    while (1) {
        int n = imu_driver_read_fifo(samples, IMU_FIFO_WATERMARK);
        if (n > 0) {
            /* Send samples to stroke segmenter */
            for (int i = 0; i < n; i++) {
                xQueueSend(imu_sample_queue, &samples[i], 0);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1));  /* ~1kHz check rate */
    }
}

/* ---- Stroke segmentation task (Core 0) ---- */
static void segmenter_task(void *arg)
{
    imu_sample_t sample;
    ESP_LOGI(TAG, "Segmenter task started");

    while (1) {
        if (xQueueReceive(imu_sample_queue, &sample, portMAX_DELAY)) {
            stroke_event_t stroke;
            if (stroke_segmenter_update(&sample, &stroke)) {
                xQueueSend(stroke_queue, &stroke, 10);
            }
        }
    }
}

/* ---- Recognition task (Core 0, lower priority) ---- */
static void recognition_task(void *arg)
{
    stroke_event_t stroke;
    ESP_LOGI(TAG, "Recognition task started");

    while (1) {
        if (xQueueReceive(stroke_queue, &stroke, portMAX_DELAY)) {
            /* Check for gesture first */
            gesture_type_t gesture = gesture_handler_detect(&stroke);
            if (gesture != GESTURE_NONE) {
                ESP_LOGI(TAG, "Gesture detected: %d", gesture);
                switch (gesture) {
                    case GESTURE_SPACE:
                        ble_hid_send_key(' ');
                        break;
                    case GESTURE_BACKSPACE:
                        ble_hid_send_key(0x08);  /* backspace */
                        break;
                    case GESTURE_ENTER:
                        ble_hid_send_key(0x0D);  /* enter */
                        break;
                    case GESTURE_CAPS_LOCK:
                        char_recognizer_toggle_caps();
                        haptic_feedback_pulse(50);
                        break;
                    case GESTURE_MODE_SWITCH:
                        char_recognizer_toggle_mode();
                        haptic_feedback_double(30);
                        break;
                    case GESTURE_UNDO:
                        ble_hid_send_key(0x08);  /* backspace = undo last */
                        break;
                    default:
                        break;
                }
                oled_display_glyph(gesture == GESTURE_SPACE ? ' ' :
                                   gesture == GESTURE_CAPS_LOCK ? 'C' : '?');
                continue;
            }

            /* Reconstruct 2D trajectory from 3D IMU data */
            traj_2d_t traj;
            trajectory_recon_project(&stroke, &traj);

            /* Classify character with CNN */
            char_pred_t pred = char_recognizer_classify(&traj);

            if (pred.char_id >= 0 && pred.confidence > 0.15f) {
                /* Apply n-gram language model correction */
                char corrected = lang_model_correct(pred.char_id, pred.confidence);

                /* Send recognized character over BLE */
                ble_hid_send_key(corrected);
                ble_custom_update_char(corrected, pred.confidence);

                /* Visual and haptic feedback */
                oled_display_char(corrected);
                haptic_feedback_pulse(15);  /* 15ms buzz on recognition */

                /* Update language model context */
                lang_model_update_context(corrected);

                ESP_LOGI(TAG, "Recognized: '%c' (raw=%d conf=%.2f corr='%c')",
                         (char)pred.char_id, pred.char_id, pred.confidence, corrected);
            } else {
                ESP_LOGW(TAG, "Low confidence: char_id=%d conf=%.2f — skipped",
                         pred.char_id, pred.confidence);
                oled_display_glyph('?');
            }
        }
    }
}

/* ---- Power management task (lowest priority) ---- */
static void power_task(void *arg)
{
    ESP_LOGI(TAG, "Power task started");

    while (1) {
        power_manager_update();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* ---- Touch event handler (runs in timer context) ---- */
static int touch_tap_count = 0;
static int64_t last_touch_time = 0;

static void touch_event_handler(void *arg)
{
    uint16_t touch_val_inner, touch_val_outer;
    touch_pad_read(TOUCH_PAD_NUM1, &touch_val_inner);
    touch_pad_read(TOUCH_PAD_NUM2, &touch_val_outer);

    int64_t now = esp_timer_get_time();

    /* Simple touch detection: value below threshold = touched */
    bool touched = (touch_val_inner < 40 || touch_val_outer < 40);

    if (touched && (now - last_touch_time > 200000)) {  /* 200ms debounce */
        touch_tap_count++;
        last_touch_time = now;

        if (touch_tap_count == 1) {
            /* Single tap: wake from sleep if sleeping */
            power_manager_wake();
        } else if (touch_tap_count == 2) {
            /* Double tap: switch user profile */
            active_profile = (active_profile + 1) % 4;
            calibration_load_profile(active_profile);
            haptic_feedback_double(20);
            oled_display_printf("P%d", active_profile);
            ESP_LOGI(TAG, "Switched to profile %d", active_profile);
        }
    }

    /* Reset tap counter after 500ms window */
    if (now - last_touch_time > 500000) {
        touch_tap_count = 0;
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "=== Scribe Nib starting ===");
    ESP_LOGI(TAG, "ESP32-S3 @ 240MHz, IDF version: %s", esp_get_idf_version());

    /* Initialize NVS for profile storage */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS partition truncated, erasing...");
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Load active profile from NVS */
    nvs_handle_t nvs_handle;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle) == ESP_OK) {
        nvs_get_u8(nvs_handle, NVS_PROFILE_KEY, &active_profile);
        nvs_close(nvs_handle);
    }
    ESP_LOGI(TAG, "Active profile: %d", active_profile);

    /* Initialize hardware buses */
    init_gpio();
    init_spi_bus();
    init_i2c_bus();

    /* Create inter-task queues */
    imu_sample_queue = xQueueCreate(512, sizeof(imu_sample_t));
    stroke_queue = xQueueCreate(16, sizeof(stroke_event_t));
    char_queue = xQueueCreate(16, sizeof(char_result_t));

    /* Initialize subsystems */
    imu_driver_init(SPI2_HOST, IMU_ODR_200HZ, IMU_ACCEL_RANGE_16G, IMU_GYRO_RANGE_2000DPS);
    stroke_segmenter_init();
    trajectory_recon_init();
    char_recognizer_init();     /* loads CNN model from flash partition */
    lang_model_init();          /* loads n-gram model from flash partition */
    ble_hid_init("ScribeNib");  /* BLE HID keyboard */
    ble_custom_init();          /* Custom GATT service */
    oled_display_init();        /* SSD1306 64×32 */
    power_manager_init();       /* Sleep state machine */
    calibration_load_profile(active_profile);
    haptic_feedback_init(GPIO_NUM_42, LEDC_TIMER_0, LEDC_CHANNEL_0);
    gesture_handler_init();

    /* Show startup screen */
    oled_display_printf("SbN");

    /* Launch tasks — pin IMU to Core 1 for deterministic timing */
    xTaskCreatePinnedToCore(imu_task,         "imu",        4096, NULL, 10, NULL, 1);
    xTaskCreatePinnedToCore(segmenter_task,    "segmenter",  4096, NULL,  8, NULL, 0);
    xTaskCreatePinnedToCore(recognition_task, "recognize",  8192, NULL,  5, NULL, 0);
    xTaskCreatePinnedToCore(power_task,       "power",     2048, NULL,  2, NULL, 0);

    /* Periodic touch pad polling timer (every 50ms) */
    esp_timer_handle_t touch_timer;
    esp_timer_create_args_t touch_timer_args = {
        .callback = touch_event_handler,
        .name = "touch_poll"
    };
    esp_timer_create(&touch_timer_args, &touch_timer);
    esp_timer_start_periodic(touch_timer, 50000);  /* 50ms */

    ESP_LOGI(TAG, "=== Scribe Nib ready ===");
    oled_display_clear();

    /* Main loop does nothing — all work in FreeRTOS tasks */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}