/*
 * aero-reed — main.c
 * Breath-controlled electronic wind instrument firmware (ESP32-S3)
 */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs_flash.h"

#include "touch.h"
#include "breath.h"
#include "lip.h"
#include "imu.h"
#include "synth.h"
#include "audio.h"
#include "midi.h"
#include "display.h"
#include "patch.h"
#include "power.h"
#include "tasks.h"

static const char *TAG = "aero";

/* ── Shared state (updated by sensor tasks, read by synth/midi tasks) ──── */
aero_state_t g_state = {0};

void app_main(void)
{
    ESP_LOGI(TAG, "Aero Reed booting…");

    /* NVS for patch storage */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Load patches from NVS */
    patch_load_all();
    g_state.patch_idx = 0;

    /* Initialise subsystems */
    power_init();
    display_init();
    touch_init();
    breath_init();
    lip_init();
    imu_init();
    synth_init();
    audio_init();   /* I2S → PCM5102A */
    midi_init();    /* BLE + USB MIDI */

    ESP_LOGI(TAG, "All subsystems up. Patch 0: %s", patch_name(0));

    /* ── Sensor fusion task (10 ms / 100 Hz) ─────────────────────────── */
    xTaskCreate(sensor_task, "sensor", 4096, NULL, 5, NULL);

    /* ── Synth render task (fills I2S DMA buffers at 44.1 kHz) ───────── */
    xTaskCreate(synth_task, "synth", 8192, NULL, 10, NULL);

    /* ── MIDI + display task (20 ms / 50 Hz) ─────────────────────────── */
    xTaskCreate(midi_display_task, "midi_disp", 6144, NULL, 4, NULL);

    /* ── Power monitor task (1 s / 1 Hz) ─────────────────────────────── */
    xTaskCreate(power_task, "power", 2048, NULL, 3, NULL);

    /* ── BOOT button handler (patch change / power off) ──────────────── */
    xTaskCreate(boot_button_task, "button", 2048, NULL, 6, NULL);

    ESP_LOGI(TAG, "Aero Reed ready. Blow to play!");
}