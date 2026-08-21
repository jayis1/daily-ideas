/*
 * Spectra Charm — ESP32-C3 WS2812 RGB LED Indicator
 * led_indicator.c
 */

#include "led_indicator.h"
#include "driver/rmt.h"
#include "esp_log.h"

#define RMT_CHANNEL  RMT_CHANNEL_0
#define WS2812_T0H  14   /* 0.35 us in 25MHz ticks */
#define WS2812_T0L  34   /* 0.85 us */
#define WS2812_T1H  34   /* 0.85 us */
#define WS2812_T1L  14   /* 0.35 us */
#define WS2812_RESET 500 /* >50 us low */

static int led_gpio = -1;
static uint8_t current_r = 0, current_g = 0, current_b = 0;

void LED_Init(int gpio)
{
    led_gpio = gpio;

    rmt_config_t config = RMT_DEFAULT_CONFIG_TX(gpio, RMT_CHANNEL);
    config.clk_div = 2; /* 40 MHz */
    rmt_config(&config);
    rmt_driver_install(RMT_CHANNEL, 0, 0);

    LED_SetColor(LED_COLOR_OFF);
}

void LED_SetColor(LEDColor_t color)
{
    switch (color) {
    case LED_COLOR_OFF:   current_r = 0;   current_g = 0;   current_b = 0;   break;
    case LED_COLOR_RED:   current_r = 30;  current_g = 0;   current_b = 0;   break;
    case LED_COLOR_GREEN: current_r = 0;   current_g = 30;  current_b = 0;   break;
    case LED_COLOR_BLUE:  current_r = 0;   current_g = 0;   current_b = 30;  break;
    case LED_COLOR_CYAN:  current_r = 0;   current_g = 30;  current_b = 30;  break;
    case LED_COLOR_YELLOW: current_r = 30;  current_g = 30;  current_b = 0;   break;
    case LED_COLOR_WHITE: current_r = 20;  current_g = 20;  current_b = 20;  break;
    }
}

void LED_Update(void)
{
    if (led_gpio < 0) return;

    /* Build WS2812 bit stream using RMT */
    uint8_t grb[3] = { current_g, current_r, current_b };
    rmt_item32_t items[25]; /* 24 data bits + 1 reset */

    int bit_idx = 0;
    for (int byte_idx = 0; byte_idx < 3; byte_idx++) {
        for (int b = 7; b >= 0; b--) {
            if (grb[byte_idx] & (1 << b)) {
                items[bit_idx].val = 0;
                items[bit_idx].duration0 = WS2812_T1H;
                items[bit_idx].duration1 = WS2812_T1L;
            } else {
                items[bit_idx].val = 0;
                items[bit_idx].duration0 = WS2812_T0H;
                items[bit_idx].duration1 = WS2812_T0L;
            }
            bit_idx++;
        }
    }

    /* Reset */
    items[24].val = 0;
    items[24].duration0 = 0;
    items[24].duration1 = WS2812_RESET;

    rmt_write_items(RMT_CHANNEL, items, 25, true);
    rmt_wait_tx_done(RMT_CHANNEL, pdMS_TO_TICKS(100));
}