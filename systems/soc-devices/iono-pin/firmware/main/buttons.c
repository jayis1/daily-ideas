/*
 * buttons.c — debounced mode/scan/cal buttons + encoder
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Buttons on PC0 (MODE), PC1 (SCAN), PC2 (CAL). Active low (pull-up).
 * EC11 encoder on PB4/PB5 (handled via EXTI in a full impl; stub here).
 *
 * SPDX-License-Identifier: MIT
 */
#include "buttons.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

static uint32_t g_last_tick[3] = {0};
static uint8_t g_last_state[3] = {1,1,1};

void buttons_init(void)
{
    GPIO_InitTypeDef io = {0};
    io.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2;
    io.Mode = GPIO_MODE_INPUT;
    io.Pull = GPIO_PULLUP;
    io.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &io);
}

button_t buttons_poll(void)
{
    uint16_t pins[3] = { GPIO_PIN_0, GPIO_PIN_1, GPIO_PIN_2 };
    button_t ids[3] = { BTN_MODE, BTN_SCAN, BTN_CAL };
    uint32_t now = HAL_GetTick();
    for (int i = 0; i < 3; i++) {
        uint8_t s = (uint8_t)HAL_GPIO_ReadPin(GPIOC, pins[i]);
        if (s == 0 && g_last_state[i] == 1 && (now - g_last_tick[i]) > 200) {
            g_last_tick[i] = now;
            g_last_state[i] = 0;
            return ids[i];
        }
        if (s == 1) g_last_state[i] = 1;
    }
    return BTN_NONE;
}

int buttons_encoder_delta(void)
{
    /* EC11 encoder handling via EXTI omitted for brevity; returns 0 */
    return 0;
}