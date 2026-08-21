/*
 * Spectra Charm — ESP32-C3 Button Handler
 * button.c
 */

#include "button.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static int scan_btn_gpio = -1;
static int mode_btn_gpio = -1;

void Button_Init(int scan_gpio, int mode_gpio)
{
    scan_btn_gpio = scan_gpio;
    mode_btn_gpio = mode_gpio;

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << scan_gpio) | (1ULL << mode_gpio),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
}

static bool debounce(int gpio)
{
    /* Simple debounce: read twice with 20ms gap */
    if (gpio_get_level(gpio) == 0) {
        vTaskDelay(pdMS_TO_TICKS(20));
        if (gpio_get_level(gpio) == 0) {
            /* Wait for release */
            while (gpio_get_level(gpio) == 0) {
                vTaskDelay(pdMS_TO_TICKS(10));
            }
            return true;
        }
    }
    return false;
}

ButtonType_t Button_WaitPress(void)
{
    for (;;) {
        if (scan_btn_gpio >= 0 && debounce(scan_btn_gpio)) {
            return BUTTON_SCAN;
        }
        if (mode_btn_gpio >= 0 && debounce(mode_btn_gpio)) {
            return BUTTON_MODE;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}