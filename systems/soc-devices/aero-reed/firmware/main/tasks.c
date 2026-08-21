/*
 * tasks.c — sensor fusion + BOOT button tasks
 */
#include "tasks.h"
#include "synth.h"
#include "touch.h"
#include "breath.h"
#include "lip.h"
#include "imu.h"
#include "patch.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "tasks";
#define BOOT_PIN 0

static int prev_patch_idx = 0;

void sensor_task(void *arg)
{
    (void)arg;
    const TickType_t period = pdMS_TO_TICKS(10);  /* 100 Hz */
    TickType_t last = xTaskGetTickCount();

    while (1) {
        /* Scan all sensors */
        touch_scan();
        breath_scan();
        lip_scan();
        imu_scan();

        /* Update shared state */
        g_state.current_note = touch_decode_note();
        g_state.breath_vel    = breath_get_velocity();
        g_state.breath_gate   = breath_get_gate();
        g_state.bend_cents    = lip_get_bend_cents();
        g_state.modulation    = imu_get_modulation();
        g_state.vibrato_rate  = imu_get_vibrato_rate();
        g_state.vibrato_depth = imu_get_vibrato_depth();

        vTaskDelayUntil(&last, period);
    }
}

void boot_button_task(void *arg)
{
    (void)arg;
    bool last_held = false;
    uint32_t hold_start = 0;

    while (1) {
        bool held = (gpio_get_level(BOOT_PIN) == 0);  /* active-low */
        if (held && !last_held) {
            hold_start = xTaskGetTickCount();
        }
        if (!held && last_held) {
            uint32_t dur = (xTaskGetTickCount() - hold_start) * portTICK_PERIOD_MS;
            if (dur > 1000) {
                /* Long press → power off (deep sleep) */
                ESP_LOGI(TAG, "Long press → deep sleep");
                esp_deep_sleep_start();
            } else if (dur > 50) {
                /* Short press → next patch */
                patch_next();
                g_state.patch = *patch_get(g_state.patch_idx);
                ESP_LOGI(TAG, "Patch → %d: %s", g_state.patch_idx, g_state.patch.name);
            }
        }
        last_held = held;
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}