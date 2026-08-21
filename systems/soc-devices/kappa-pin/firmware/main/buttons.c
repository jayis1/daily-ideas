/*
 * kappa-pin / firmware / main / buttons.c
 * Debounced button input
 *
 * MIT License.
 */
#include "buttons.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "btn";

#define DEBOUNCE_MS     30
#define LONG_PRESS_MS   1000

typedef struct {
    int pin;
    bool last_state;        /* last raw state (true = pressed) */
    bool debounced;         /* debounced state */
    int64_t last_change;    /* last change time (us) */
    int64_t press_start;    /* press start time (us) */
} button_t;

static button_t buttons[3];

void buttons_init(void)
{
    int pins[] = { BTN_MEASURE_PIN, BTN_MODE_PIN, BTN_MENU_PIN };
    for (int i = 0; i < 3; i++) {
        buttons[i].pin = pins[i];
        buttons[i].last_state = false;
        buttons[i].debounced = false;
        buttons[i].last_change = 0;
        buttons[i].press_start = 0;

        gpio_config_t io = {
            .pin_bit_mask = (1ULL << pins[i]),
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io);
    }
    ESP_LOGI(TAG, "Buttons initialized");
}

button_event_t buttons_poll(void)
{
    int64_t now = esp_timer_get_time();

    for (int i = 0; i < 3; i++) {
        bool raw = (gpio_get_level(buttons[i].pin) == 0);  /* active low */

        if (raw != buttons[i].last_state) {
            buttons[i].last_state = raw;
            buttons[i].last_change = now;
        }

        /* Debounce */
        if ((now - buttons[i].last_change) > (DEBOUNCE_MS * 1000)) {
            if (raw != buttons[i].debounced) {
                buttons[i].debounced = raw;
                if (raw) {
                    /* Press detected */
                    buttons[i].press_start = now;
                } else {
                    /* Release detected */
                    int64_t press_dur = now - buttons[i].press_start;
                    if (press_dur > (LONG_PRESS_MS * 1000)) {
                        /* Long press */
                        if (i == 0) return BTN_MEASURE_LONG;
                    } else if (press_dur > (DEBOUNCE_MS * 1000)) {
                        /* Short press */
                        switch (i) {
                            case 0: return BTN_MEASURE_PRESS;
                            case 1: return BTN_MODE_PRESS;
                            case 2: return BTN_MENU_PRESS;
                        }
                    }
                }
            }
        }
    }

    return BTN_NONE;
}

button_event_t buttons_wait(int timeout_ms)
{
    int64_t t_end = esp_timer_get_time() + (int64_t)timeout_ms * 1000;
    while (esp_timer_get_time() < t_end) {
        button_event_t ev = buttons_poll();
        if (ev != BTN_NONE) return ev;
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    return BTN_NONE;
}