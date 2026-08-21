/* mux.c — ADG715 8:1 analog switch driver */

#include "mux.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "mux";

static int g_en_pin = -1, g_s0_pin = -1, g_s1_pin = -1, g_s2_pin = -1;
static int g_selected = MUX_ELECTRODE_NONE;

esp_err_t mux_init(int en_pin, int s0_pin, int s1_pin, int s2_pin)
{
    g_en_pin = en_pin;
    g_s0_pin = s0_pin;
    g_s1_pin = s1_pin;
    g_s2_pin = s2_pin;

    uint64_t mask = (1ULL << en_pin) | (1ULL << s0_pin) |
                    (1ULL << s1_pin) | (1ULL << s2_pin);
    gpio_config_t cfg = {
        .pin_bit_mask = mask,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    esp_err_t ret = gpio_config(&cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GPIO config failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Start disabled for safety */
    mux_disable();
    ESP_LOGI(TAG, "MUX initialized (EN=%d S0=%d S1=%d S2=%d)",
             en_pin, s0_pin, s1_pin, s2_pin);
    return ESP_OK;
}

esp_err_t mux_select(int electrode)
{
    if (electrode < 0 || electrode > 7) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Set address bits */
    gpio_set_level(g_s0_pin, electrode & 0x01);
    gpio_set_level(g_s1_pin, (electrode >> 1) & 0x01);
    gpio_set_level(g_s2_pin, (electrode >> 2) & 0x01);

    /* Enable the mux (active low on ADG715) */
    gpio_set_level(g_en_pin, 0);

    g_selected = electrode;
    ESP_LOGD(TAG, "Selected electrode %d", electrode);
    return ESP_OK;
}

esp_err_t mux_disable(void)
{
    /* Disable mux (active low) */
    gpio_set_level(g_en_pin, 1);
    g_selected = MUX_ELECTRODE_NONE;
    return ESP_OK;
}

int mux_get_selected(void)
{
    return g_selected;
}