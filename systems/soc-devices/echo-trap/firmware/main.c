/*
 * Echo Trap — Acoustic Insect Trap
 * ESP32-S3 Firmware
 *
 * main.c — FreeRTOS task initialization and application entry point
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_sleep.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

/* FreeRTOS */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

#include "i2s_capture.h"
#include "preprocess.h"
#include "classifier.h"
#include "species.h"
#include "fan_control.h"
#include "uv_lure.h"
#include "sensors.h"
#include "lorawan.h"
#include "power.h"
#include "storage.h"

static const char *TAG = "echo-trap";

/* ---- Task Handles ---- */
static TaskHandle_t hCaptureTask;
static TaskHandle_t hClassifyTask;
static TaskHandle_t hTrapTask;
static TaskHandle_t hLoRaTask;
static TaskHandle_t hPowerTask;

/* ---- Queues ---- */
QueueHandle_t xCaptureQueue;       /* capture → classify: raw audio frames */
QueueHandle_t xDetectionQueue;     /* classify → trap/lorawan: detection events */
QueueHandle_t xUplinkQueue;        /* anything → lorawan: uplink packets */

/* ---- Global state ---- */
typedef struct {
    uint16_t    species_counts[SPECIES_COUNT];
    uint16_t    target_captures;
    uint16_t    beneficial_sighted;
    uint8_t     battery_pct;
    float       temperature_c;
    float       humidity_pct;
    float       light_lux;
    uint32_t    uptime_s;
    uint8_t     lora_joined;
    uint8_t     fan_active;
} system_state_t;

static system_state_t g_state;

/* ===================================================================== */
/*  Capture Task — I2S DMA double-buffer, hand frames to classify         */
/* ===================================================================== */
static void CaptureTask(void *arg)
{
    (void)arg;
    audio_frame_t frame;

    for (;;) {
        /* Blocking wait for a complete DMA buffer */
        if (i2s_capture_get_frame(&frame, portMAX_DELAY) == pdTRUE) {
            /* Pre-process: energy gate + autocorrelation pre-classifier */
            preprocess_result_t pp;
            int interesting = preprocess_frame(&frame, &pp);

            if (interesting) {
                /* Send the pre-processed frame to the classify task */
                xQueueSend(xCaptureQueue, &frame, 0);
            }
            /* If not interesting (ambient noise floor), skip — saves CPU */
        }
    }
}

/* ===================================================================== */
/*  Classify Task — FFT → CNN → species ID → capture decision              */
/* ===================================================================== */
static void ClassifyTask(void *arg)
{
    (void)arg;
    audio_frame_t frame;
    detection_event_t det;

    for (;;) {
        if (xQueueReceive(xCaptureQueue, &frame, portMAX_DELAY) == pdTRUE) {
            /* Run the int8 1D-CNN classifier on the FFT spectrum */
            uint8_t species_id;
            float confidence;
            float wb_freq;

            classifier_inference(&frame, &species_id, &confidence, &wb_freq);

            ESP_LOGD(TAG, "Classify: species=%d conf=%.2f wb=%.1f Hz",
                     species_id, confidence, wb_freq);

            /* Only emit a detection if confidence is high enough */
            if (confidence >= CONFIDENCE_THRESHOLD) {
                det.species_id  = species_id;
                det.confidence  = confidence;
                det.wingbeat_hz = wb_freq;
                det.timestamp_s = g_state.uptime_s;
                det.temperature_c = g_state.temperature_c;
                det.humidity_pct = g_state.humidity_pct;

                /* Update species counters */
                g_state.species_counts[species_id]++;
                if (species_is_target(species_id)) {
                    g_state.target_captures++;
                } else if (species_is_beneficial(species_id)) {
                    g_state.beneficial_sighted++;
                }

                /* Send to trap task (for fan activation if target) */
                xQueueSend(xDetectionQueue, &det, 0);

                /* Send to LoRaWAN task for immediate uplink if target */
                if (species_is_target(species_id)) {
                    uint8_t immediate = 1;
                    xQueueSend(xUplinkQueue, &immediate, 0);
                }

                ESP_LOGI(TAG, "DETECT: %s (conf=%.2f, wb=%.1f Hz) %s",
                         species_name(species_id), confidence, wb_freq,
                         species_is_target(species_id) ? "→ FAN" : "(beneficial/neutral)");
            }
        }
    }
}

/* ===================================================================== */
/*  Trap Task — Fan control + UV lure scheduling                           */
/* ===================================================================== */
static void TrapTask(void *arg)
{
    (void)arg;
    detection_event_t det;
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        /* Check for new detections */
        if (xQueueReceive(xDetectionQueue, &det, 0) == pdTRUE) {
            if (species_is_target(det.species_id)) {
                /* Activate the suction fan for the capture */
                uint16_t duration = (det.species_id == SPECIES_CODLING_MOTH ||
                                    det.species_id == SPECIES_ARMYWORM_MOTH)
                                    ? FAN_DURATION_MOTH_MS : FAN_DURATION_MS;
                fan_control_capture(duration);
                g_state.fan_active = 1;
                ESP_LOGI(TAG, "Fan ON for %d ms (captured %s)",
                         duration, species_name(det.species_id));
            }
        }

        /* Update UV lure schedule based on ambient light */
        float lux = g_state.light_lux;
        uv_lure_update(lux);

        /* Poll fan tachometer for stuck-fan detection */
        if (fan_control_check_fault()) {
            ESP_LOGW(TAG, "Fan fault detected!");
            /* Log fault, skip capture this cycle */
        }

        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(100));  /* 10 Hz */
    }
}

/* ===================================================================== */
/*  LoRaWAN Task — uplink queue + downlink handling                        */
/* ===================================================================== */
static void LoRaTask(void *arg)
{
    (void)arg;
    TickType_t last_uplink = xTaskGetTickCount();
    uint8_t immediate_flag;

    /* Attempt OTAA join */
    if (lorawan_join() == pdPASS) {
        g_state.lora_joined = 1;
        ESP_LOGI(TAG, "LoRaWAN joined successfully");
    } else {
        g_state.lora_joined = 0;
        ESP_LOGW(TAG, "LoRaWAN join failed — will retry");
    }

    for (;;) {
        /* Check for immediate-uplink request (pest detection) */
        if (xQueueReceive(xUplinkQueue, &immediate_flag, 0) == pdTRUE) {
            /* Build and send an uplink immediately */
            lorawan_uplink_t pkt;
            pkt.type = UPLINK_DETECTION;
            pkt.u.detection.species_id = 0;  /* filled from latest */
            pkt.u.detection.timestamp_s = g_state.uptime_s;
            lorawan_send_uplink(&pkt);
            last_uplink = xTaskGetTickCount();
        }

        /* Periodic uplink (every 15 min by default) */
        TickType_t now = xTaskGetTickCount();
        if ((now - last_uplink) >= pdMS_TO_TICKS(LORA_UPLINK_INTERVAL_S * 1000)) {
            /* Build summary uplink with species counts + env data */
            lorawan_uplink_t pkt;
            pkt.type = UPLINK_SUMMARY;
            for (int i = 0; i < SPECIES_COUNT; i++) {
                pkt.u.summary.counts[i] = g_state.species_counts[i];
            }
            pkt.u.summary.temperature_c = g_state.temperature_c;
            pkt.u.summary.humidity_pct  = g_state.humidity_pct;
            pkt.u.summary.battery_pct   = g_state.battery_pct;
            pkt.u.summary.target_captures = g_state.target_captures;
            pkt.u.summary.beneficial_sighted = g_state.beneficial_sighted;
            lorawan_send_uplink(&pkt);

            /* Reset species counters after each summary uplink */
            memset(g_state.species_counts, 0, sizeof(g_state.species_counts));
            g_state.target_captures = 0;
            g_state.beneficial_sighted = 0;

            last_uplink = now;
        }

        /* Process downlink commands */
        lorawan_process_downlink();

        /* Retry join if not joined */
        if (!g_state.lora_joined) {
            if (lorawan_join() == pdPASS) {
                g_state.lora_joined = 1;
                ESP_LOGI(TAG, "LoRaWAN joined (retry)");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* ===================================================================== */
/*  Power Task — fuel gauge, solar, light sleep management                */
/* ===================================================================== */
static void PowerTask(void *arg)
{
    (void)arg;
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        /* Update battery + solar voltage + temperature/humidity/light */
        power_update(&g_state.battery_pct, &g_state.temperature_c,
                     &g_state.humidity_pct, &g_state.light_lux);

        ESP_LOGD(TAG, "Pwr: bat=%d%% T=%.1f RH=%.1f lux=%.0f",
                 g_state.battery_pct, g_state.temperature_c,
                 g_state.humidity_pct, g_state.light_lux);

        /* Low battery handling */
        if (g_state.battery_pct <= BATTERY_CRIT_PCT) {
            ESP_LOGW(TAG, "Battery critical (%d%%) — entering deep sleep",
                     g_state.battery_pct);
            /* Turn off UV + fan before sleeping */
            uv_lure_off();
            fan_control_off();
            esp_deep_sleep_start();
        }

        /* Update charging LED */
        power_update_charge_led();

        g_state.uptime_s = esp_timer_get_time() / 1000000ULL;

        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(SENSOR_POLL_MS));
    }
}

/* ===================================================================== */
/*  Application entry point                                                */
/* ===================================================================== */
void app_main(void)
{
    ESP_LOGI(TAG, "Echo Trap v1.0 starting...");

    /* NVS init */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* Initialize global state */
    memset(&g_state, 0, sizeof(g_state));

    /* Initialize subsystems */
    storage_init();
    species_init();
    power_init();
    sensors_init();
    i2s_capture_init();
    preprocess_init();
    classifier_init();
    fan_control_init();
    uv_lure_init();
    lorawan_init();

    ESP_LOGI(TAG, "All subsystems initialized");

    /* Create queues */
    xCaptureQueue   = xQueueCreate(QUEUE_CAPTURE_LEN, sizeof(audio_frame_t));
    xDetectionQueue = xQueueCreate(QUEUE_DETECTION_LEN, sizeof(detection_event_t));
    xUplinkQueue    = xQueueCreate(QUEUE_UPLINK_LEN, sizeof(uint8_t));

    /* Create tasks — pin capture+power to core 0, classify+lorawan to core 1 */
    xTaskCreatePinnedToCore(CaptureTask,  "capture",  TASK_STACK_CAPTURE,  NULL,
                            TASK_PRIO_CAPTURE,  &hCaptureTask, 0);
    xTaskCreatePinnedToCore(ClassifyTask,  "classify", TASK_STACK_CLASSIFY, NULL,
                            TASK_PRIO_CLASSIFY, &hClassifyTask, 1);
    xTaskCreatePinnedToCore(TrapTask,      "trap",     TASK_STACK_TRAP,    NULL,
                            TASK_PRIO_TRAP,    &hTrapTask,     0);
    xTaskCreatePinnedToCore(LoRaTask,      "lorawan",  TASK_STACK_LORAWAN, NULL,
                            TASK_PRIO_LORAWAN, &hLoRaTask,    1);
    xTaskCreatePinnedToCore(PowerTask,     "power",    TASK_STACK_POWER,   NULL,
                            TASK_PRIO_POWER,   &hPowerTask,   0);

    ESP_LOGI(TAG, "Tasks created. System running.");

    /* Load LoRaWAN credentials from NVS (provisioned via BLE) */
    storage_load_lorawan_keys();
}