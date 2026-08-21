/**
 * app_main.c — Echo Mote Room Acoustic Analyzer
 *
 * Entry point: initializes all peripherals, precomputes inverse chirp,
 * registers button handlers, and runs the main measurement state machine.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "nvs_flash.h"
#include "nvs.h"

#include "i2s_manager.h"
#include "chirp_generator.h"
#include "impulse_response.h"
#include "acoustic_params.h"
#include "room_modes.h"
#include "noise_analyzer.h"
#include "lcd_display.h"
#include "ble_service.h"
#include "wifi_server.h"
#include "bme280_driver.h"
#include "power_manager.h"

static const char *TAG = "echo_mote";

/* Measurement modes */
typedef enum {
    MODE_RT60 = 0,
    MODE_FREQ,
    MODE_ROOM_MODES,
    MODE_CLARITY,
    MODE_NOISE,
    MODE_COUNT
} measure_mode_t;

static const char *mode_names[MODE_COUNT] = {
    "RT60", "FREQ", "MODES", "CLARITY", "NOISE"
};

/* GPIO assignments */
#define BTN_MEASURE    17
#define BTN_MODE       18
#define BTN_POWER      19
#define AMP_SD         20
#define LED_DATA       21

/* Shared state */
static volatile measure_mode_t current_mode = MODE_RT60;
static volatile bool measure_pending = false;
static SemaphoreHandle_t measure_sem = NULL;
static SemaphoreHandle_t mode_sem = NULL;

/* ISR handlers */
static void IRAM_ATTR measure_isr(void *arg) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(measure_sem, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) portYIELD_FROM_ISR();
}

static void IRAM_ATTR mode_isr(void *arg) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(mode_sem, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) portYIELD_FROM_ISR();
}

static void IRAM_ATTR power_isr(void *arg) {
    /* Long press = deep sleep; handled in button task with timer */
}

/* Button task: debounce and handle */
static void button_task(void *pv) {
    bool measure_held = false;
    int64_t measure_press_time = 0;

    while (1) {
        /* Mode button */
        if (xSemaphoreTake(mode_sem, pdMS_TO_TICKS(10)) == pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(50));  // debounce
            if (gpio_get_level(BTN_MODE) == 0) {
                current_mode = (current_mode + 1) % MODE_COUNT;
                ESP_LOGI(TAG, "Mode: %s", mode_names[current_mode]);
                lcd_display_mode_select(current_mode);
            }
        }

        /* Measure button */
        if (xSemaphoreTake(measure_sem, pdMS_TO_TICKS(10)) == pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(50));  // debounce
            if (gpio_get_level(BTN_MEASURE) == 0) {
                measure_press_time = esp_timer_get_time();
                measure_held = true;

                /* Wait for release */
                while (gpio_get_level(BTN_MEASURE) == 0) {
                    vTaskDelay(pdMS_TO_TICKS(10));
                }
                int64_t hold_time = esp_timer_get_time() - measure_press_time;

                if (hold_time > 3000000) {
                    /* Long press (>3s): enter calibration mode */
                    ESP_LOGI(TAG, "Entering calibration mode...");
                    /* TODO: trigger speaker SPL calibration */
                } else {
                    /* Short press: start measurement */
                    measure_pending = true;
                }
                measure_held = false;
            }
        }

        /* Power button: enter deep sleep on press */
        if (gpio_get_level(BTN_POWER) == 0) {
            vTaskDelay(pdMS_TO_TICKS(50));
            if (gpio_get_level(BTN_POWER) == 0) {
                ESP_LOGI(TAG, "Power button: entering deep sleep");
                lcd_display_off();
                gpio_set_level(AMP_SD, 0);
                esp_deep_sleep_start();
            }
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

/* Run a complete measurement cycle */
static void run_measurement(measure_mode_t mode) {
    float temp = 22.0f, hum = 50.0f, pres = 1013.0f;
    bme280_read(&temp, &hum, &pres);
    float speed_of_sound = 331.3f * sqrtf(1.0f + temp / 273.15f);
    ESP_LOGI(TAG, "Speed of sound: %.1f m/s (T=%.1f°C, RH=%.0f%%)", speed_of_sound, temp, hum);

    lcd_display_measuring(mode, 0);

    /* Mute amp during setup */
    gpio_set_level(AMP_SD, 0);

    /* Determine capture parameters based on mode */
    uint32_t sample_rate = 48000;
    uint32_t capture_seconds;
    switch (mode) {
        case MODE_NOISE:     capture_seconds = 30; break;
        case MODE_ROOM_MODES: capture_seconds = 25; break;
        default:             capture_seconds = 8; break;
    }
    uint32_t total_samples = sample_rate * capture_seconds;

    /* Allocate capture buffers in PSRAM */
    int16_t *captured_l = malloc(total_samples * sizeof(int16_t));
    int16_t *captured_r = malloc(total_samples * sizeof(int16_t));
    if (!captured_l || !captured_r) {
        ESP_LOGE(TAG, "Failed to allocate capture buffers");
        free(captured_l);
        free(captured_r);
        return;
    }

    /* Start dual-mic I2S capture */
    i2s_manager_start_capture(sample_rate);

    if (mode != MODE_NOISE) {
        /* Unmute and play excitation signal */
        gpio_set_level(AMP_SD, 1);
        vTaskDelay(pdMS_TO_TICKS(50));  // let amp settle

        if (mode == MODE_ROOM_MODES) {
            room_modes_play_pings(sample_rate);
        } else {
            chirp_generator_play_sweep(sample_rate);
        }

        /* Continue capturing decay after signal ends */
        uint32_t remaining_ms = (capture_seconds * 1000) -
                                (mode == MODE_ROOM_MODES ? 25000 : 5000);
        for (uint32_t i = 0; i < remaining_ms / 100; i++) {
            lcd_display_measuring(mode, (i * 100 * 100) / (capture_seconds * 1000));
            vTaskDelay(pdMS_TO_TICKS(100));
        }

        gpio_set_level(AMP_SD, 0);  // mute
    } else {
        /* Noise mode: just capture ambient for 30s */
        for (uint32_t i = 0; i < capture_seconds * 10; i++) {
            lcd_display_measuring(mode, (i * 100) / (capture_seconds * 10));
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }

    /* Stop capture and retrieve samples */
    i2s_manager_read_captured(captured_l, captured_r, total_samples);

    /* ---- DSP Processing ---- */
    acoustic_results_t results;
    memset(&results, 0, sizeof(results));
    results.speed_of_sound = speed_of_sound;
    results.temperature = temp;
    results.humidity = hum;

    if (mode != MODE_NOISE) {
        ESP_LOGI(TAG, "Extracting impulse response...");
        float *impulse_l = impulse_response_extract(captured_l, total_samples,
                                                      sample_rate);
        float *impulse_r = impulse_response_extract(captured_r, total_samples,
                                                      sample_rate);
        if (!impulse_l) {
            ESP_LOGE(TAG, "Impulse response extraction failed");
            free(captured_l); free(captured_r);
            return;
        }

        switch (mode) {
        case MODE_RT60:
            acoustic_params_compute_rt60(impulse_l, total_samples, sample_rate,
                                          speed_of_sound, &results);
            break;
        case MODE_FREQ:
            acoustic_params_compute_freq_response(impulse_l, total_samples,
                                                    sample_rate, &results);
            break;
        case MODE_ROOM_MODES:
            room_modes_analyze(impulse_l, total_samples, sample_rate,
                               speed_of_sound, &results);
            break;
        case MODE_CLARITY:
            acoustic_params_compute_clarity(impulse_l, total_samples,
                                              sample_rate, &results);
            break;
        default:
            break;
        }

        free(impulse_l);
        free(impulse_r);
    } else {
        noise_analyzer_compute_nc(captured_l, total_samples, sample_rate, &results);
    }

    /* Display and broadcast results */
    lcd_display_results(mode, &results);
    ble_service_notify_results(mode, &results);

    if (wifi_server_is_active()) {
        wifi_server_post_results(mode, &results);
    }

    ESP_LOGI(TAG, "Measurement complete (%s)", mode_names[mode]);

    /* Print RT60 if available */
    if (mode == MODE_RT60) {
        for (int i = 0; i < 6; i++) {
            ESP_LOGI(TAG, "  RT60 %d Hz: %.3f s", 125 << i, results.rt60[i]);
        }
    }

    free(captured_l);
    free(captured_r);
}

/* Console command handler (USB-C serial) */
static void console_task(void *pv) {
    char line[128];
    while (1) {
        if (fgets(line, sizeof(line), stdin)) {
            /* Strip newline */
            line[strcspn(line, "\r\n")] = '\0';

            if (strcmp(line, "measure rt60") == 0) {
                current_mode = MODE_RT60; measure_pending = true;
            } else if (strcmp(line, "measure freq") == 0) {
                current_mode = MODE_FREQ; measure_pending = true;
            } else if (strcmp(line, "measure modes") == 0) {
                current_mode = MODE_ROOM_MODES; measure_pending = true;
            } else if (strcmp(line, "measure clarity") == 0) {
                current_mode = MODE_CLARITY; measure_pending = true;
            } else if (strcmp(line, "measure noise") == 0) {
                current_mode = MODE_NOISE; measure_pending = true;
            } else if (strncmp(line, "cal spm ", 8) == 0) {
                float db = atof(line + 8);
                power_manager_cal_spl(db);
                ESP_LOGI(TAG, "Speaker SPL calibrated to %.1f dB", db);
            } else if (strcmp(line, "cal mic") == 0) {
                /* TODO: mic sensitivity matching calibration */
                ESP_LOGI(TAG, "Mic calibration started...");
            } else if (strncmp(line, "wifi start ", 11) == 0) {
                /* Parse SSID and password */
                char *ssid = line + 11;
                char *pass = strchr(ssid, ' ');
                if (pass) { *pass = '\0'; pass++; }
                wifi_server_start(ssid, pass ? pass : "");
            } else if (strcmp(line, "wifi stop") == 0) {
                wifi_server_stop();
            } else if (strcmp(line, "status") == 0) {
                float vbat = power_manager_read_battery();
                ESP_LOGI(TAG, "Battery: %.2f V, Mode: %s",
                         vbat, mode_names[current_mode]);
            } else if (strcmp(line, "sleep") == 0) {
                lcd_display_off();
                gpio_set_level(AMP_SD, 0);
                esp_deep_sleep_start();
            } else if (strlen(line) > 0) {
                ESP_LOGW(TAG, "Unknown command: %s", line);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Echo Mote — Room Acoustic Analyzer");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize I2C bus (for BME280) */
    bme280_init();

    /* Initialize I2S buses (speaker + dual mics) */
    i2s_manager_init();

    /* Initialize LCD */
    lcd_display_init();

    /* Initialize amplifier shutdown (muted by default) */
    gpio_config_t amp_cfg = {
        .pin_bit_mask = (1ULL << AMP_SD),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&amp_cfg);
    gpio_set_level(AMP_SD, 0);  // Start muted

    /* Configure button GPIOs */
    gpio_config_t btn_cfg = {
        .pin_bit_mask = (1ULL << BTN_MEASURE) | (1ULL << BTN_MODE) | (1ULL << BTN_POWER),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&btn_cfg);

    /* Create semaphores for button ISRs */
    measure_sem = xSemaphoreCreateBinary();
    mode_sem = xSemaphoreCreateBinary();

    /* Install GPIO ISR service */
    gpio_install_isr_service(0);
    gpio_isr_handler_add(BTN_MEASURE, measure_isr, NULL);
    gpio_isr_handler_add(BTN_MODE, mode_isr, NULL);
    gpio_isr_handler_add(BTN_POWER, power_isr, NULL);

    /* Initialize power manager */
    power_manager_init();

    /* Initialize chirp generator (precompute inverse chirp in PSRAM) */
    chirp_generator_init(48000);

    /* Initialize BLE */
    ble_service_init();

    /* Create tasks */
    xTaskCreate(button_task, "buttons", 4096, NULL, 5, NULL);
    xTaskCreate(console_task, "console", 4096, NULL, 3, NULL);

    /* Main measurement loop */
    while (1) {
        if (measure_pending) {
            measure_pending = false;
            run_measurement(current_mode);
        }

        /* Idle display */
        float vbat = power_manager_read_battery();
        float temp = 22.0f, hum = 50.0f, pres = 1013.0f;
        bme280_read(&temp, &hum, &pres);
        lcd_display_idle(current_mode, vbat, temp, hum);

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}