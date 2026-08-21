/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/button.c — Trigger + user buttons (GPIO, debounced)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "button.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TRIGGER_PIN   4
#define MENU_PIN      5
#define MODE_PIN      6

static volatile uint8_t g_trig = 0, g_menu = 0, g_mode = 0;

static void IRAM_ATTR isr_handler(void *arg)
{
    int pin = (int)(intptr_t)arg;
    if (pin == TRIGGER_PIN) g_trig = 1;
    else if (pin == MENU_PIN) g_menu = 1;
    else if (pin == MODE_PIN) g_mode = 1;
}

void button_init(void)
{
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << TRIGGER_PIN) | (1ULL << MENU_PIN) | (1ULL << MODE_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&cfg);
    gpio_install_isr_service(0);
    gpio_isr_handler_add(TRIGGER_PIN, isr_handler, (void *)TRIGGER_PIN);
    gpio_isr_handler_add(MENU_PIN, isr_handler, (void *)MENU_PIN);
    gpio_isr_handler_add(MODE_PIN, isr_handler, (void *)MODE_PIN);
}

uint8_t button_trigger_pressed(void)
{
    uint8_t v = g_trig; g_trig = 0; return v;
}

uint8_t button_menu_pressed(void)
{
    uint8_t v = g_menu; g_menu = 0; return v;
}

uint8_t button_mode_pressed(void)
{
    uint8_t v = g_mode; g_mode = 0; return v;
}