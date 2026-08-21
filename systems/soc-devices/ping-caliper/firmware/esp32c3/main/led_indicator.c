/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/led_indicator.c — Status LED driver
 *
 * Drives 3 GPIO outputs (red, green, blue status LEDs). The blue LED
 * reflects BLE link state. The red LED indicates flaw/battery-low.
 * The green LED is the "ready/measuring" indicator.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "led_indicator.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define LED_R_PIN 7
#define LED_G_PIN 8
#define LED_B_PIN 10

static led_state_t g_state[3] = {LED_OFF, LED_OFF, LED_OFF};

static void set_gpio(int pin, int on)
{
    gpio_set_level(pin, on);
}

static void led_task(void *arg)
{
    (void)arg;
    int tick = 0;
    for (;;) {
        for (int i = 0; i < 3; i++) {
            int pin = (i == 0) ? LED_R_PIN : (i == 1) ? LED_G_PIN : LED_B_PIN;
            int on = 0;
            switch (g_state[i]) {
            case LED_OFF: on = 0; break;
            case LED_ON:  on = 1; break;
            case LED_BLINK: on = (tick / 5) % 2; break;
            case LED_BLINK_FAST: on = (tick / 1) % 2; break;
            }
            set_gpio(pin, on);
        }
        tick++;
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void led_indicator_init(void)
{
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << LED_R_PIN) | (1ULL << LED_G_PIN) | (1ULL << LED_B_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    xTaskCreate(led_task, "led", 1024, NULL, 1, NULL);
}

void led_indicator_set(led_t led, led_state_t state)
{
    if (led > LED_BLUE) return;
    g_state[led] = state;
}