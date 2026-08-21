/* main.c — Taste Bead main entry point
 *
 * Core 0 (PRO_CPU): EIS sweep engine — AD5941 control, frequency sweep,
 *                   impedance DSP, feature extraction
 * Core 1 (APP_CPU): k-NN classifier, UI (OLED + buttons), SD logging,
 *                    BLE/Wi-Fi communication
 *
 * The two cores communicate via a shared measurement buffer protected
 * by a FreeRTOS mutex + task notification.
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "esp_timer.h"

#include "sdkconfig.h"
#include "ad5941.h"
#include "mux.h"
#include "eis.h"
#include "features.h"
#include "classifier.h"
#include "library.h"
#include "display.h"
#include "sd_log.h"
#include "ble.h"
#include "bme280.h"
#include "ui.h"
#include "calibrate.h"

static const char *TAG = "taste_bead";

/* ---- Inter-core communication ---- */
static QueueHandle_t meas_queue;     /* EIS result → classifier */
static QueueHandle_t result_queue;   /* classification result → UI */
static SemaphoreHandle_t shared_mutex;

typedef struct {
    eis_result_t eis;              /* raw impedance spectra */
    float features[NUM_FEATURES]; /* extracted feature vector */
    bme280_data_t ambient;        /* temperature/humidity at measurement time */
    int64_t timestamp_us;
} measurement_t;

typedef struct {
    char label[LIBRARY_MAX_NAME_LEN];
    float confidence;
    float distance;
    int lib_index;
    int64_t timestamp_us;
} result_t;

/* ---- EIS sweep task (Core 0) ---- */
static void eis_sweep_task(void *arg)
{
    ESP_LOGI(TAG, "EIS sweep task started on core %d", xPortGetCoreID());

    measurement_t meas;
    bme280_data_t ambient;

    while (1) {
        /* Wait for trigger from UI (button press or monitor timer) */
        uint32_t cmd = 0;
        xQueueReceive(ui_trigger_queue(), &cmd, portMAX_DELAY);

        if (cmd == UI_CMD_IDLE) {
            continue;
        }

        ESP_LOGI(TAG, "Starting EIS sweep (cmd=%d)", cmd);

        /* Read ambient conditions */
        bme280_read(&ambient);
        meas.ambient = ambient;
        meas.timestamp_us = esp_timer_get_time();

        /* Run full EIS sweep: 5 electrodes × 20 frequencies */
        esp_err_t ret = eis_sweep(&meas.eis);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "EIS sweep failed: %s", esp_err_to_name(ret));
            ui_set_status("Sweep failed!");
            continue;
        }

        /* Extract features from impedance spectra */
        features_extract(&meas.eis, meas.features, &ambient);

        /* Send measurement to classifier task */
        xQueueSend(meas_queue, &meas, portMAX_DELAY);
    }
}

/* ---- Classification task (Core 1) ---- */
static void classifier_task(void *arg)
{
    ESP_LOGI(TAG, "Classifier task started on core %d", xPortGetCoreID());

    measurement_t meas;
    result_t result;

    while (1) {
        if (xQueueReceive(meas_queue, &meas, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        ESP_LOGI(TAG, "Classifying measurement...");

        /* Run k-NN classification */
        classifier_result_t clf;
        esp_err_t ret = classifier_classify(meas.features, &clf);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Classification failed");
            strcpy(result.label, "Error");
            result.confidence = 0;
        } else {
            strncpy(result.label, clf.label, LIBRARY_MAX_NAME_LEN - 1);
            result.label[LIBRARY_MAX_NAME_LEN - 1] = '\0';
            result.confidence = clf.confidence;
            result.distance = clf.nearest_distance;
            result.lib_index = clf.lib_index;
        }
        result.timestamp_us = meas.timestamp_us;

        ESP_LOGI(TAG, "Result: %s (%.1f%% confidence)", result.label, result.confidence);

        /* Send result to UI */
        xQueueSend(result_queue, &result, portMAX_DELAY);

        /* Log to SD card */
        sd_log_measurement(&meas.eis, meas.features, &result, &meas.ambient);

        /* Send via BLE */
        ble_send_result(&result);
        ble_send_spectrum(&meas.eis);
    }
}

/* ---- Main entry point ---- */
void app_main(void)
{
    ESP_LOGI(TAG, "=== Taste Bead — Pocket Electronic Tongue ===");
    ESP_LOGI(TAG, "ESP32-S3 + AD5941, %d electrodes, %d freqs",
             NUM_ELECTRODES, NUM_FREQS);

    /* Initialize NVS for library storage */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    /* Initialize hardware peripherals */
    xSemaphoreCreateStatic  /* placeholder; use dynamic */
    shared_mutex = xSemaphoreCreateMutex();
    assert(shared_mutex != NULL);

    /* Initialize I2C bus (BME280 + OLED) */
    bme280_init(PIN_I2C_SDA, PIN_I2C_SCL);

    /* Initialize OLED display */
    display_init();
    display_show_splash("Taste Bead", "Initializing...");

    /* Initialize AD5941 analog front-end */
    ad5941_init(PIN_SPI_CS_AD5941, PIN_SPI_SCK, PIN_SPI_MISO,
                PIN_SPI_MOSI, PIN_AD5941_IRQ, PIN_AD5941_RESET);

    /* Initialize electrode multiplexer */
    mux_init(PIN_MUX_EN, PIN_MUX_S0, PIN_MUX_S1, PIN_MUX_S2);

    /* Initialize EIS engine */
    eis_init();

    /* Initialize SD card */
    sd_init();

    /* Initialize calibration */
    calibrate_init();
    calibrate_status_t cal = calibrate_get_status();
    if (!cal.open_done || !cal.short_done || !cal.kcl_done) {
        ESP_LOGW(TAG, "Calibration incomplete! Run calibrate mode.");
        display_show_message("WARNING:", "Calibration needed!");
        vTaskDelay(pdMS_TO_TICKS(2000));
    }

    /* Load reference library from NVS */
    library_init();
    int lib_count = library_count();
    ESP_LOGI(TAG, "Reference library: %d/%d entries", lib_count, LIBRARY_MAX_ENTRIES);

    /* Initialize classifier */
    classifier_init();

    /* Initialize UI (buttons + mode state machine) */
    ui_init();
    display_show_message("Taste Bead", lib_count > 0 ?
                         "Ready to identify" : "Library empty — Learn mode");

    /* Initialize BLE */
    ble_init();

    /* Create inter-core queues */
    meas_queue = xQueueCreate(2, sizeof(measurement_t));
    result_queue = xQueueCreate(4, sizeof(result_t));
    assert(meas_queue && result_queue);

    /* Start EIS sweep task on Core 0 */
    xTaskCreatePinnedToCore(eis_sweep_task, "eis_sweep", 8192, NULL,
                             5, NULL, 0);

    /* Start classifier task on Core 1 */
    xTaskCreatePinnedToCore(classifier_task, "classifier", 8192, NULL,
                             4, NULL, 1);

    /* UI task runs on Core 1 (created by ui_init) */
    ui_start(result_queue);

    ESP_LOGI(TAG, "All tasks started. Waiting for button press...");

    /* Main loop: update display with results */
    result_t last_result;
    while (1) {
        if (xQueueReceive(result_queue, &last_result, pdMS_TO_TICKS(100)) == pdTRUE) {
            if (strlen(last_result.label) > 0) {
                char line1[32];
                char line2[32];
                snprintf(line1, sizeof(line1), "%s", last_result.label);
                snprintf(line2, sizeof(line2), "%.0f%% confidence",
                         last_result.confidence);
                display_show_result(line1, line2, last_result.confidence);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}