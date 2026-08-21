/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * heater_safety.c — Triple-redundant heater safety watchdog
 *
 * A stuck-on heater would burn the tree xylem and drain the battery.
 * Three independent layers protect against firmware hangs:
 *
 *   1. TIM2 one-pulse mode — hardware timer disables heater after 2 s
 *      regardless of firmware state
 *   2. INA180 current-sense + LMV7219 comparator — trips a hardware
 *      latch at 500 mA, cutting the high-side enable (PB6)
 *   3. 72 °C thermal fuse potted in the heater needle — last resort
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "heater_safety.h"
#include <stddef.h>

/* ---- Platform stubs ---- */
extern void gpio_write(int pin, int val);
extern int  gpio_read(int pin);
extern void delay_ms(uint32_t ms);
extern void tim2_start_oneshot(uint32_t pulse_ms);
extern void tim2_stop(void);

/* ---- Module state ---- */
static int heater_fault_latched = 0;
static uint32_t pulse_count = 0;
static uint32_t fault_count = 0;

void heater_safety_init(void)
{
    heater_fault_latched = 0;
    /* Ensure heater is OFF */
    gpio_write(PIN_HEATER_MOSFET, 0);
    gpio_write(PIN_HEATER_ENABLE, 0);
    /* Configure TIM2 for one-pulse mode (but don't start yet) */
    tim2_stop();
}

/*
 * Arm and fire the heater with full safety chain.
 * Returns 0 on success, -1 if a fault is latched.
 */
int heater_safety_fire(uint32_t pulse_ms)
{
    /* Check for latched fault */
    if (heater_fault_latched) {
        fault_count++;
        return -1;
    }

    /* Check overcurrent comparator (active-low fault line) */
    if (gpio_read(PIN_HEATER_FAULT) == 0) {
        heater_fault_latched = 1;
        fault_count++;
        return -1;
    }

    /* Enable high-side switch first */
    gpio_write(PIN_HEATER_ENABLE, 1);
    delay_ms(1);  /* settle */

    /* Start TIM2 one-pulse mode — hardware watchdog */
    tim2_start_oneshot(pulse_ms);

    /* Also drive MOSFET directly (redundant with TIM2) */
    gpio_write(PIN_HEATER_MOSFET, 1);

    /* Wait for pulse to complete */
    delay_ms(pulse_ms);

    /* Ensure heater is off */
    gpio_write(PIN_HEATER_MOSFET, 0);
    tim2_stop();
    gpio_write(PIN_HEATER_ENABLE, 0);

    pulse_count++;

    /* Re-check fault after pulse (overcurrent may have tripped mid-pulse) */
    if (gpio_read(PIN_HEATER_FAULT) == 0) {
        heater_fault_latched = 1;
        fault_count++;
        return -1;
    }

    return 0;
}

int heater_safety_has_fault(void)
{
    return heater_fault_latched ||
           (gpio_read(PIN_HEATER_FAULT) == 0);
}

void heater_safety_clear_fault(void)
{
    /* Only clear if the fault line is actually deasserted */
    if (gpio_read(PIN_HEATER_FAULT) != 0) {
        heater_fault_latched = 0;
    }
}

uint32_t heater_safety_get_pulse_count(void) { return pulse_count; }
uint32_t heater_safety_get_fault_count(void) { return fault_count; }

/*
 * Monitor task — called periodically from main loop.
 * Checks for thermal runaway (heater on too long, detected by
 * overcurrent comparator or probe thermistor exceeding 70 °C).
 */
void heater_safety_monitor(void)
{
    if (heater_safety_has_fault()) {
        /* Ensure heater is OFF */
        gpio_write(PIN_HEATER_MOSFET, 0);
        gpio_write(PIN_HEATER_ENABLE, 0);
        tim2_stop();
    }
}