/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * power.c — Battery management, solar charge monitoring, deep-sleep
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "power.h"
#include "sensors.h"
#include <math.h>

/* ---- Platform stubs ---- */
extern void enter_stop_mode(void);
extern void wake_from_stop(void);
extern uint16_t adc_read(int channel);
extern void gpio_write(int pin, int val);
extern int  gpio_read(int pin);

/* ---- Module state ---- */
static float battery_pct = 100.0f;
static float battery_v = 4.0f;
static float solar_v = 0.0f;
static int   charging = 0;
static int   in_deep_sleep = 0;

int power_init(void)
{
    /* Initialize MAX17048 fuel gauge */
    if (max17048_init() != 0)
        return -1;
    max17048_read_soc(&battery_pct);
    max17048_read_voltage(&battery_v);
    return 0;
}

void power_update(void)
{
    /* Read fuel gauge */
    max17048_read_soc(&battery_pct);
    max17048_read_voltage(&battery_v);

    /* Read solar panel voltage via ADC (1:4 divider) */
    uint16_t adc_raw = adc_read(15);  /* ADC1_IN15 = PB0 */
    solar_v = (float)adc_raw * (3.3f / 4095.0f) * ADC_SOLAR_DIVIDER;

    /* Charging if solar voltage > battery voltage + 0.3 V */
    charging = (solar_v > (battery_v + 0.3f)) ? 1 : 0;

    /* Update status LED */
    if (charging)
        gpio_write(PIN_LED_AMBER, 1);
    else
        gpio_write(PIN_LED_AMBER, 0);
}

float power_get_battery_pct(void) { return battery_pct; }
float power_get_battery_v(void) { return battery_v; }
float power_get_solar_v(void) { return solar_v; }
int   power_is_charging(void) { return charging; }
int   power_is_low(void) { return battery_pct < BATTERY_LOW_PCT; }
int   power_is_critical(void) { return battery_pct < BATTERY_CRIT_PCT; }

/*
 * Determine if the device should enter deep-sleep mode.
 * Below DEEP_SLEEP_LOW_SOC, the device wakes only once per hour
 * for a single measurement, extending runtime from hours to days.
 */
int power_should_deep_sleep(void)
{
    return (battery_pct < DEEP_SLEEP_LOW_SOC);
}

void power_enter_deep_sleep(void)
{
    in_deep_sleep = 1;
    /* Configure RTC wake-up for 1 hour */
    extern void rtc_set_wakeup(uint32_t seconds);
    rtc_set_wakeup(3600);

    /* Power down non-essential peripherals */
    extern void probe_power_down(void);
    probe_power_down();

    /* Enter STOP mode (lowest power that retains RAM) */
    enter_stop_mode();

    /* --- Wakes here after RTC interrupt --- */
    wake_from_stop();
    in_deep_sleep = 0;
}

int power_in_deep_sleep(void) { return in_deep_sleep; }

/*
 * Check if battery is too low for a heat pulse.
 * The heater draws ~180 mA for 2 s — if battery is below 3.4 V
 * (near depletion), skip the pulse to avoid brownout.
 */
int power_can_fire_heater(void)
{
    return (battery_v > 3.4f && battery_pct > BATTERY_CRIT_PCT);
}