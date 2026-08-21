/* ui.c — User interface (buttons, mode state machine) for Taste Bead
 *
 * Three buttons:
 *   ID  — trigger identification sweep
 *   MODE — cycle through modes
 *   LIB  — in Library mode: browse/delete; in Learn mode: confirm
 *
 * The UI task runs on Core 1, polls buttons via GPIO, and sends trigger
 * commands to the EIS sweep task via a FreeRTOS queue.
 */

#include "ui.h"
#include "sdkconfig.h"
#include "display.h"
#include "library.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <string.h>

static const char *TAG = "ui";

static QueueHandle_t g_trigger_queue = NULL;
static QueueHandle_t g_result_queue = NULL;
static ui_mode_t g_mode = UI_MODE_IDENTIFY;
static int g_lib_browser_index = 0;
static bool g_monitor_active = false;

/* Debounce state */
static uint32_t g_btn_last_press[3] = {0, 0, 0};
#define DEBOUNCE_MS 200

static void set_led(uint8_t r, uint8_t g, uint8_t b)
{
    /* RGB LED is common-cathode: drive high to illuminate */
    gpio_set_level(PIN_LED_R, r);
    gpio_set_level(PIN_LED_G, g);
    gpio_set_level(PIN_LED_B, b);
}

void ui_set_led(uint8_t r, uint8_t g, uint8_t b)
{
    set_led(r, g, b);
}

static const char *mode_name(ui_mode_t mode)
{
    switch (mode) {
    case UI_MODE_IDENTIFY:  return "IDENTIFY";
    case UI_MODE_LIBRARY:   return "LIBRARY";
    case UI_MODE_LEARN:     return "LEARN";
    case UI_MODE_MONITOR:   return "MONITOR";
    case UI_MODE_RAW:       return "RAW STREAM";
    case UI_MODE_CALIBRATE: return "CALIBRATE";
    default:                return "IDLE";
    }
}

static void on_mode_button(void)
{
    /* Cycle to next mode */
    g_mode = (ui_mode_t)((g_mode + 1) % UI_MODE_COUNT);

    /* Stop monitor if switching away */
    if (g_monitor_active && g_mode != UI_MODE_MONITOR) {
        ui_cmd_t cmd = UI_CMD_STOP_MONITOR;
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
        g_monitor_active = false;
    }

    /* Show mode on display */
    display_show_message("Mode:", (char *)mode_name(g_mode));

    /* Set LED color based on mode */
    switch (g_mode) {
    case UI_MODE_IDENTIFY:  set_led(0, 1, 0); break; /* green */
    case UI_MODE_LIBRARY:   set_led(0, 0, 1); break; /* blue */
    case UI_MODE_LEARN:     set_led(1, 0, 0); break; /* red */
    case UI_MODE_MONITOR:   set_led(0, 1, 1); break; /* cyan */
    case UI_MODE_RAW:       set_led(1, 0, 1); break; /* magenta */
    case UI_MODE_CALIBRATE: set_led(1, 1, 0); break; /* yellow */
    default:                set_led(0, 0, 0); break;
    }
}

static void on_id_button(void)
{
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;

    switch (g_mode) {
    case UI_MODE_IDENTIFY:
        /* Trigger identification sweep */
        display_show_message("Measuring...", "Dip probe in liquid");
        ui_cmd_t cmd = UI_CMD_TRIGGER_SWEEP;
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
        break;

    case UI_MODE_LEARN:
        /* Trigger learn sweep (will prompt for label via BLE) */
        display_show_message("Learning...", "Dip probe in sample");
        cmd = UI_CMD_LEARN_SWEEP;
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
        break;

    case UI_MODE_MONITOR:
        /* Toggle monitor mode */
        if (g_monitor_active) {
            cmd = UI_CMD_STOP_MONITOR;
            xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
            g_monitor_active = false;
            display_show_message("Monitor stopped", mode_name(g_mode));
        } else {
            cmd = UI_CMD_MONITOR_SWEEP;
            xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
            g_monitor_active = true;
            display_show_message("Monitor active", "Auto-sweep every 10s");
        }
        break;

    case UI_MODE_CALIBRATE:
        /* Cycle through calibration steps: open → short → KCl */
        if (now - g_btn_last_press[0] < 2000) {
            /* Double press → short */
            display_show_message("SHORT cal", "Short all electrodes");
            cmd = UI_CMD_CAL_SHORT;
        } else if (now - g_btn_last_press[0] < 4000) {
            /* Triple press → KCl */
            display_show_message("KCl 0.01M cal", "Dip in 0.01M KCl");
            cmd = UI_CMD_CAL_KCL;
        } else {
            /* Single press → open */
            display_show_message("OPEN cal", "Remove probe from liquid");
            cmd = UI_CMD_CAL_OPEN;
        }
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
        break;

    case UI_MODE_RAW:
        /* Start raw streaming */
        display_show_message("Streaming raw", "Via BLE only");
        cmd = UI_CMD_TRIGGER_SWEEP;
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);
        break;

    default:
        break;
    }
    g_btn_last_press[0] = now;
}

static void on_lib_button(void)
{
    switch (g_mode) {
    case UI_MODE_LIBRARY:
        /* Browse to next library entry */
        g_lib_browser_index = (g_lib_browser_index + 1) %
                              (library_count() > 0 ? library_count() : 1);
        ui_cmd_t cmd = UI_CMD_NEXT_LIB_ENTRY;
        xQueueSend(g_trigger_queue, &cmd, portMAX_DELAY);

        /* Show entry on display */
        library_entry_t entry;
        if (library_get(g_lib_browser_index, &entry) == ESP_OK) {
            display_show_library(g_lib_browser_index, library_count(),
                                  entry.label, entry.measurement_count);
        }
        break;

    case UI_MODE_LEARN:
        /* Long press in learn mode = delete last entry
         * Short press = confirm/capture */
        /* For simplicity, LIB button in Learn mode triggers capture */
        on_id_button();
        break;

    default:
        break;
    }
}

esp_err_t ui_init(void)
{
    /* Create trigger queue */
    g_trigger_queue = xQueueCreate(4, sizeof(ui_cmd_t));
    assert(g_trigger_queue);

    /* Configure button GPIOs as inputs with pull-ups */
    uint64_t mask = (1ULL << PIN_BTN_ID) | (1ULL << PIN_BTN_MODE) |
                    (1ULL << PIN_BTN_LIB);
    gpio_config_t cfg = {
        .pin_bit_mask = mask,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&cfg);

    /* Configure RGB LED GPIOs as outputs */
    uint64_t led_mask = (1ULL << PIN_LED_R) | (1ULL << PIN_LED_G) |
                        (1ULL << PIN_LED_B);
    gpio_config_t led_cfg = {
        .pin_bit_mask = led_mask,
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&led_cfg);

    /* Initial LED: green (identify mode) */
    set_led(0, 1, 0);

    ESP_LOGI(TAG, "UI initialized (mode: %s)", mode_name(g_mode));
    return ESP_OK;
}

void ui_poll(void)
{
    static uint32_t last_poll = 0;
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    if (now - last_poll < 10) return;  /* poll at 100 Hz max */
    last_poll = now;

    /* Check buttons (active-low with pull-up) */
    int btn_pins[3] = {PIN_BTN_ID, PIN_BTN_MODE, PIN_BTN_LIB};
    static bool btn_prev[3] = {true, true, true};

    for (int i = 0; i < 3; i++) {
        bool level = gpio_get_level(btn_pins[i]);
        if (level == false && btn_prev[i] == true) {
            /* Button press (falling edge) */
            if (now - g_btn_last_press[i] > DEBOUNCE_MS) {
                g_btn_last_press[i] = now;
                switch (i) {
                case 0: on_id_button(); break;
                case 1: on_mode_button(); break;
                case 2: on_lib_button(); break;
                }
            }
        }
        btn_prev[i] = level;
    }
}

void ui_set_status(const char *msg)
{
    display_show_message("Status:", (char *)msg);
}

QueueHandle_t ui_trigger_queue(void)
{
    return g_trigger_queue;
}

ui_mode_t ui_get_mode(void)
{
    return g_mode;
}

/* UI task */
static void ui_task(void *arg)
{
    ESP_LOGI(TAG, "UI task started on core %d", xPortGetCoreID());

    while (1) {
        ui_poll();

        /* Check for BLE commands */
        /* (BLE command handling would be integrated here) */

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

esp_err_t ui_start(QueueHandle_t result_queue)
{
    g_result_queue = result_queue;

    /* Start UI task on core 1 */
    xTaskCreatePinnedToCore(ui_task, "ui_task", 4096, NULL, 3, NULL, 1);

    return ESP_OK;
}