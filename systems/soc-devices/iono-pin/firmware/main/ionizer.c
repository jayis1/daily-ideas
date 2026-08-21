/*
 * ionizer.c — Ni-63 / corona ionizer enable (safety-interlocked)
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * PA2 drives the ionizer enable (Ni-63 shutter-bias supply OR corona power).
 * Enable is gated by the safety subsystem: reed interlock closed, no HV fault.
 *
 * SPDX-License-Identifier: MIT
 */
#include "ionizer.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include "safety.h"

static bool g_on = false;

void ionizer_init(void)
{
    g_on = false;
    GPIO_InitTypeDef io = {0};
    io.Pin = GPIO_PIN_2;
    io.Mode = GPIO_MODE_OUTPUT_PP;
    io.Pull = GPIO_NOPULL;
    io.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &io);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, GPIO_PIN_RESET);
}

bool ionizer_safety_ok(void)
{
    return safety_interlock_closed() && !safety_fault();
}

void ionizer_enable(bool on)
{
    if (on && !ionizer_safety_ok()) {
        g_on = false;
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, GPIO_PIN_RESET);
        return;
    }
    g_on = on;
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

bool ionizer_is_enabled(void) { return g_on; }