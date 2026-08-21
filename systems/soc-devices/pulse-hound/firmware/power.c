/*
 * Pulse Hound — RF Signal Hunter
 * power.c — MAX17048 fuel gauge, low-power mode, TP4056 charge status
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "power.h"
#include "config.h"
#include <string.h>

/* ---- I2C / GPIO HAL stubs ---- */
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern void gpio_set(int pin, int val);
extern int  gpio_read(int pin);

/* ---- State ---- */
static int battery_pct = 100;
static int is_charging = 0;
static int low_power_active = 0;

/* ---- MAX17048 driver ---- */
static int max17048_read_u16(uint8_t reg, uint16_t *val)
{
    uint8_t data[2];
    if (i2c_read_reg(MAX17048_ADDR, reg, data, 2) != 0)
        return -1;
    *val = ((uint16_t)data[0] << 8) | data[1];
    return 0;
}

static int max17048_write_u16(uint8_t reg, uint16_t val)
{
    uint8_t data[2];
    data[0] = (uint8_t)(val >> 8);
    data[1] = (uint8_t)(val & 0xFF);
    return i2c_write_reg(MAX17048_ADDR, reg, data, 2);
}

int power_init(void)
{
    /* Quick-start the MAX17048 (if POR occurred) */
    uint16_t status;
    if (max17048_read_u16(MAX17048_REG_VERSION, &status) != 0)
        return -1;

    /* If version reads 0x00xx, device is present */
    if ((status & 0xFF00) == 0 && (status & 0x00FF) == 0)
        return -1; /* no device */

    /* Read initial SoC */
    power_update();
    return 0;
}

void power_update(void)
{
    uint16_t soc_raw;
    if (max17048_read_u16(MAX17048_REG_SOC, &soc_raw) == 0) {
        /* SoC is in 1/256 % units in the high byte */
        battery_pct = soc_raw >> 8;
        if (battery_pct > 100) battery_pct = 100;
    }

    /* Charge status from TP4056 CHRG pin (active low = charging) */
    is_charging = (gpio_read(CHRG_STATUS_GPIO) == 0) ? 1 : 0;

    /* Low-power mode transition */
    if (battery_pct <= BATTERY_CRIT_PCT && !low_power_active) {
        low_power_active = 1;
    } else if (battery_pct > BATTERY_LOW_PCT && low_power_active) {
        low_power_active = 0;
    }
}

int power_get_battery_pct(void)
{
    return battery_pct;
}

int power_is_charging(void)
{
    return is_charging;
}

int power_is_low_power(void)
{
    return low_power_active;
}

int power_can_sustain_sweep(void)
{
    /* Need at least 8% battery for active sweeping */
    return battery_pct > BATTERY_CRIT_PCT;
}

int power_can_sustain_df(void)
{
    /* DF mode needs more power (stepper) — need 15% */
    return battery_pct > BATTERY_LOW_PCT;
}

float power_get_voltage(void)
{
    uint16_t vcell_raw;
    if (max17048_read_u16(MAX17048_REG_VCELL, &vcell_raw) != 0)
        return 0.0f;
    /* VCELL: 78.125 µV per LSB → voltage = raw * 78.125e-6 */
    return (float)vcell_raw * 78.125e-6f;
}

void power_enter_deep_sleep(void)
{
    /* In a real implementation, this would configure ESP32 deep sleep
     * with ULP or timer wakeup. Here we just flag it. */
    low_power_active = 1;
}

void power_exit_deep_sleep(void)
{
    low_power_active = 0;
}