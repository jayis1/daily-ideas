/*
 * cor-sono / firmware / main.c
 * Main application + state machine (Core 1)
 */
#include "main.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

static const char *TAG = "cor-sono";

const char *const CLASS_NAMES[N_CLASSES] = {
    "Normal", "S3 gallop", "S4 gallop", "Sys murmur",
    "Dia murmur", "Crackles", "Wheeze", "Pleural rub"
};

corsono_ctx_t g_ctx = {
    .state = ST_IDLE, .mode = MODE_HEART, .volume_db = 15,
    .heart_rate = 0, .class_id = CL_NORMAL, .confidence = 0,
    .battery_pct = 100, .charging = false, .sd_present = false
};

uint64_t millis(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

static void init_nvs(void)
{
    esp_err_t r = nvs_flash_init();
    if (r == ESP_ERR_NVS_NO_FREE_PAGES || r == ESP_ERR_NVS_NEW_VERSION_FOUND)
        (void)nvs_flash_erase(), nvs_flash_init();
}

static void status_led_set(bool on) { gpio_set_level(36, on ? 1 : 0); }

/* Button callbacks (defined in buttons.c) */
extern void on_button_record(void);
extern void on_button_mode(void);
extern void on_button_menu(void);

/* ---- state transitions ---- */
static void enter_state(corsono_state_t s)
{
    ESP_LOGI(TAG, "state %d -> %d", g_ctx.state, s);
    g_ctx.state = s;
    switch (s) {
    case ST_IDLE:    status_led_set(false); break;
    case ST_ARMING:  status_led_set(true);  break;
    case ST_LISTEN:  status_led_set(true);  break;
    case ST_RECORD:  status_led_set(true);  break;
    case ST_RESULT:  status_led_set(false); break;
    }
}

/* main app_main */
void app_main(void)
{
    ESP_LOGI(TAG, "Cor Sono — Pocket Smart Stethoscope booting...");

    init_nvs();

    /* GPIO: status LED */
    gpio_config_t led_cfg = {
        .pin_bit_mask = 1ULL << 36, .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = false, .pull_down_en = false, .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&led_cfg);

    /* Bring up subsystems */
    audio_init();
    anc_init();
    pcg_init();
    classifier_init();
    oled_init();
    sd_logger_init();
    buttons_init();
    ble_stream_init();
    wifi_web_init();

    /* Start Core 0 audio acquisition task pinned to core 0 */
    xTaskCreatePinnedToCore(audio_task, "audio", 8192, NULL, 10, NULL, 0);
    /* Start Core 1 PCG analysis + classification task */
    xTaskCreatePinnedToCore(pcg_task, "pcg", 12288, NULL, 6, NULL, 1);

    ESP_LOGI(TAG, "boot complete. state=IDLE");

    /* Main loop: handle state machine on Core 1 */
    enter_state(ST_IDLE);
    while (1) {
        switch (g_ctx.state) {
        case ST_IDLE:
            /* waiting for record button */
            vTaskDelay(pdMS_TO_TICKS(50));
            break;
        case ST_ARMING:
            /* self-test in pcg_task; transition handled there */
            vTaskDelay(pdMS_TO_TICKS(20));
            break;
        case ST_LISTEN:
        case ST_RECORD:
            /* streaming audio + classification; monitor stop button */
            vTaskDelay(pdMS_TO_TICKS(50));
            break;
        case ST_RESULT:
            /* display result; menu button returns to IDLE */
            vTaskDelay(pdMS_TO_TICKS(50));
            break;
        }
    }
}

/* ---- button handlers (called from buttons.c ISR-compatible context) ---- */
void on_button_record(void)
{
    if (g_ctx.state == ST_IDLE) {
        enter_state(ST_ARMING);
    } else if (g_ctx.state == ST_LISTEN || g_ctx.state == ST_RECORD) {
        enter_state(ST_RESULT);
    } else if (g_ctx.state == ST_RESULT) {
        enter_state(ST_IDLE);
    }
}

void on_button_mode(void)
{
    g_ctx.mode = (corsono_mode_t)((g_ctx.mode + 1) % 3);
    ESP_LOGI(TAG, "mode -> %d", g_ctx.mode);
}

void on_button_menu(void)
{
    if (g_ctx.state == ST_RESULT) enter_state(ST_IDLE);
    else if (g_ctx.state == ST_LISTEN) enter_state(ST_RECORD);
}