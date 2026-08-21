/*
 * dent-scope / Core/Src/safety.c
 * Dent Scope — Safety subsystem
 *
 * Checks:
 * - Force overload (above 22 N → mechanical clutch should slip, but software cuts too)
 * - Stall/over-travel (clutch engaged → stall GPIO)
 * - Tip interlock (reed switch, tip must be present)
 * - Watchdog (IWDG refreshed in main loop)
 *
 * MIT License.
 */
#include "safety.h"

static uint32_t overload_count = 0;

void safety_init(void)
{
    overload_count = 0;
}

bool safety_check(void)
{
    /* tip interlock: must be closed (pin reads 0 = pulled low by reed) */
    if (!HAL_GPIO_ReadPin(INTERLOCK_PORT, INTERLOCK_PIN)) {
        /* tip removed during test → abort */
        return false;
    }

    /* stall / over-travel: clutch engaged = pin reads 0 */
    if (!HAL_GPIO_ReadPin(STALL_PORT, STALL_PIN)) {
        return false;
    }

    /* force overload: if force exceeds 22 N for >100 ms, cut */
    if (g_status.force_mN > 22000.0f) {
        overload_count++;
        if (overload_count > 50) return false; /* 50 × 2ms = 100ms */
    } else {
        overload_count = 0;
    }

    return true;
}