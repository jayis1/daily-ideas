/*
 * Flux Ring — led_feedback.c
 * WS2812B RGB LED feedback for field strength visualization.
 *
 * SPDX-License-Identifier: MIT
 */

#include "led_feedback.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(led_feedback, LOG_LEVEL_INF);

#define WS2812B_GPIO_PIN  5

/* Timing (nRF52840 @ 64MHz, ~15.6ns per cycle) */
#define T0H_CYCLES  22   /* ~0.35us */
#define T0L_CYCLES  60   /* ~0.9us */
#define T1H_CYCLES  60   /* ~0.9us */
#define T1L_CYCLES  22   /* ~0.35us */
#define RESET_US    60   /* >50us reset */

static const struct device *gpio_dev;

/* Simple RGB color */
typedef struct {
    uint8_t r, g, b;
} rgb_t;

/* Color map table: threshold in Gauss, base color */
typedef struct {
    float threshold;
    rgb_t color;
} color_map_entry_t;

static const color_map_entry_t color_map[] = {
    {  0.5f, {   0,  30, 255 } },  /* Soft blue   */
    {  1.0f, {   0, 200, 255 } },  /* Cyan        */
    {  3.0f, {   0, 255,  80 } },  /* Green       */
    { 10.0f, { 255, 255,   0 } },  /* Yellow      */
    { 50.0f, { 255, 140,   0 } },  /* Orange      */
    {800.0f, { 255,  20,   0 } },  /* Red         */
};
#define COLOR_MAP_SIZE (sizeof(color_map) / sizeof(color_map[0]))

static void ws2812b_send_bit(int val)
{
    /* Bit-bang WS2812B protocol using nRF52840 GPIO */
    nrf_gpio_pin_set(NRF_GPIO_PIN_MAP(0, WS2812B_GPIO_PIN));
    if (val) {
        /* 1-bit: hold high for ~0.9us */
        nrf_delay_ns(900);
        nrf_gpio_pin_clear(NRF_GPIO_PIN_MAP(0, WS2812B_GPIO_PIN));
        nrf_delay_ns(350);
    } else {
        /* 0-bit: hold high for ~0.35us */
        nrf_delay_ns(350);
        nrf_gpio_pin_clear(NRF_GPIO_PIN_MAP(0, WS2812B_GPIO_PIN));
        nrf_delay_ns(900);
    }
}

static void ws2812b_send_byte(uint8_t byte)
{
    /* MSB first */
    for (int i = 7; i >= 0; i--) {
        ws2812b_send_bit((byte >> i) & 1);
    }
}

static void ws2812b_send_color(rgb_t color)
{
    /* WS2812B expects GRB order */
    ws2812b_send_byte(color.g);
    ws2812b_send_byte(color.r);
    ws2812b_send_byte(color.b);
}

static void ws2812b_reset(void)
{
    nrf_gpio_pin_clear(NRF_GPIO_PIN_MAP(0, WS2812B_GPIO_PIN));
    k_usleep(RESET_US);
}

int led_feedback_init(void)
{
    gpio_dev = DEVICE_DT_GET(DT_NODELABEL(gpio0));
    if (!device_is_ready(gpio_dev)) {
        LOG_ERR("GPIO not ready for WS2812B");
        return -1;
    }

    gpio_pin_configure(gpio_dev, WS2812B_GPIO_PIN, GPIO_OUTPUT_INACTIVE);
    ws2812b_reset();

    /* Show startup: brief white flash */
    rgb_t white = { 30, 30, 30 };
    ws2812b_send_color(white);
    ws2812b_reset();
    k_msleep(200);
    ws2812b_send_color((rgb_t){0, 0, 0});
    ws2812b_reset();

    LOG_INF("WS2812B LED initialized");
    return 0;
}

void led_feedback_set_field(float magnitude_gauss, pole_t pole)
{
    rgb_t color = { 0, 0, 0 };

    /* Find the appropriate color band */
    for (int i = 0; i < COLOR_MAP_SIZE; i++) {
        if (magnitude_gauss < color_map[i].threshold) {
            if (i == 0) {
                color = color_map[0].color;
            } else {
                /* Interpolate between previous and current */
                float range = color_map[i].threshold - color_map[i-1].threshold;
                float frac = (magnitude_gauss - color_map[i-1].threshold) / range;
                frac = frac < 0 ? 0 : (frac > 1 ? 1 : frac);

                color.r = (uint8_t)(color_map[i-1].color.r +
                          frac * (color_map[i].color.r - color_map[i-1].color.r));
                color.g = (uint8_t)(color_map[i-1].color.g +
                          frac * (color_map[i].color.g - color_map[i-1].color.g));
                color.b = (uint8_t)(color_map[i-1].color.b +
                          frac * (color_map[i].color.b - color_map[i-1].color.b));
            }
            break;
        }
    }

    /* Pole tint: N-pole adds warm (red), S-pole adds cool (blue) */
    if (pole == POLE_N) {
        color.r = (color.r < 220) ? color.r + 30 : 255;
    } else if (pole == POLE_S) {
        color.b = (color.b < 220) ? color.b + 30 : 255;
    }

    /* Scale brightness: very weak field → dim, strong → bright */
    float brightness;
    if (magnitude_gauss < 0.3f) {
        brightness = 0.2f;  /* Dim ambient */
    } else if (magnitude_gauss < 1.0f) {
        brightness = 0.4f;
    } else if (magnitude_gauss < 10.0f) {
        brightness = 0.7f;
    } else {
        brightness = 1.0f;  /* Full brightness for strong fields */
    }

    color.r = (uint8_t)(color.r * brightness);
    color.g = (uint8_t)(color.g * brightness);
    color.b = (uint8_t)(color.b * brightness);

    /* Send to WS2812B */
    unsigned int key = irq_lock();  /* Disable interrupts for timing */
    ws2812b_send_color(color);
    irq_unlock(key);
    ws2812b_reset();
}

void led_feedback_off(void)
{
    unsigned int key = irq_lock();
    ws2812b_send_color((rgb_t){0, 0, 0});
    irq_unlock(key);
    ws2812b_reset();
}