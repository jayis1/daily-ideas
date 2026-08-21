/*
 * Flux Ring — touch_input.c
 * Capacitive touch input for mode cycling.
 *
 * Uses nRF52840's built-in capacitive touch sensor peripheral
 * or a simple GPIO-based touch detection.
 *
 * SPDX-License-Identifier: MIT
 */

#include "touch_input.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(touch_input, LOG_LEVEL_INF);

#define TOUCH_PIN  9  /* P0.09 — capacitive touch pad */

/* Timing constants */
#define DEBOUNCE_MS      50
#define DOUBLE_TAP_MS    400

/* Callbacks */
static void (*on_single_tap)(void) = NULL;
static void (*on_double_tap)(void) = NULL;

/* State */
static int64_t last_tap_time = 0;
static bool touch_active = false;
static int64_t touch_start_time = 0;

/* GPIO interrupt callback */
static struct gpio_callback touch_cb_data;

static void touch_isr(const struct device *dev,
                       struct gpio_callback *cb,
                       uint32_t pins)
{
    /* Debounce in ISR context — minimal work */
    int64_t now = k_uptime_get();

    bool pressed = gpio_pin_get(dev, TOUCH_PIN);

    if (pressed && !touch_active) {
        touch_active = true;
        touch_start_time = now;
    } else if (!pressed && touch_active) {
        touch_active = false;
        int64_t duration = now - touch_start_time;

        /* Only register taps that lasted 20-500ms (not long hold) */
        if (duration >= 20 && duration <= 500) {
            int64_t since_last = now - last_tap_time;

            if (since_last < DOUBLE_TAP_MS && since_last > 50) {
                /* Double tap detected */
                if (on_double_tap) {
                    on_double_tap();
                }
                last_tap_time = 0;  /* Reset to avoid triple-detect */
            } else {
                /* Potential single tap — wait for double tap window */
                last_tap_time = now;
            }
        }
    }
}

/* Work item for deferred single-tap detection (after double-tap window) */
static struct k_work_delayable single_tap_work;

static void single_tap_handler(struct k_work *work)
{
    /* If we get here, no double tap was detected within the window */
    if (last_tap_time > 0) {
        if (on_single_tap) {
            on_single_tap();
        }
        last_tap_time = 0;
    }
}

int touch_input_init(void (*single_tap_cb)(void),
                     void (*double_tap_cb)(void))
{
    on_single_tap = single_tap_cb;
    on_double_tap = double_tap_cb;

    const struct device *gpio_dev = DEVICE_DT_GET(DT_NODELABEL(gpio0));
    if (!device_is_ready(gpio_dev)) {
        LOG_ERR("GPIO not ready for touch input");
        return -1;
    }

    /* Configure touch pin as input with pull-up */
    gpio_pin_configure(gpio_dev, TOUCH_PIN,
                       GPIO_INPUT | GPIO_PULL_UP);

    /* Setup interrupt on both edges */
    gpio_pin_interrupt_configure(gpio_dev, TOUCH_PIN,
                                  GPIO_INT_EDGE_BOTH);

    gpio_init_callback(&touch_cb_data, touch_isr, BIT(TOUCH_PIN));
    gpio_add_callback(gpio_dev, &touch_cb_data);

    /* Initialize deferred work for single-tap detection */
    k_work_init_delayable(&single_tap_work, single_tap_handler);

    LOG_INF("Touch input initialized on P0.%02d", TOUCH_PIN);
    return 0;
}

void touch_input_poll(void)
{
    /* Check if we need to fire single-tap callback
     * (after the double-tap detection window expires)
     */
    if (last_tap_time > 0) {
        int64_t since = k_uptime_get() - last_tap_time;
        if (since >= DOUBLE_TAP_MS) {
            if (on_single_tap) {
                on_single_tap();
            }
            last_tap_time = 0;
        }
    }
}