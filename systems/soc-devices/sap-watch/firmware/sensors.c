/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * sensors.c — SHT45, TSL2591, DS18B20, MAX17048 drivers
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "sensors.h"
#include <math.h>
#include <string.h>

/* ---- Platform I2C / 1-Wire stubs (implemented in port layer) ---- */
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_read(uint8_t addr, uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern void delay_ms(uint32_t ms);
extern void delay_us(uint32_t us);
extern void gpio_write(int pin, int val);
extern int  gpio_read(int pin);

/* ---- SHT45 temperature/humidity ---- */

int sht45_read(float *temp_c, float *rh_pct)
{
    uint8_t cmd = 0xFD;   /* SHT45: measure with clock stretching, repeatability high */
    if (i2c_write(SHT45_ADDR, &cmd, 1) != 0)
        return -1;
    delay_ms(10);  /* max measurement time */

    uint8_t raw[6];
    if (i2c_read(SHT45_ADDR, raw, 6) != 0)
        return -1;

    /* raw[0..1] = temp, raw[2] = CRC, raw[3..4] = RH, raw[5] = CRC */
    uint16_t t_ticks = (raw[0] << 8) | raw[1];
    uint16_t rh_ticks = (raw[3] << 8) | raw[4];

    /* SHT4x conversion formulas */
    *temp_c = -45.0f + 175.0f * (float)t_ticks / 65535.0f;
    *rh_pct = -6.0f + 125.0f * (float)rh_ticks / 65535.0f;

    /* Clip RH to valid range */
    if (*rh_pct < 0.0f) *rh_pct = 0.0f;
    if (*rh_pct > 100.0f) *rh_pct = 100.0f;

    return 0;
}

/* ---- TSL2591 ambient light ---- */

int tsl2591_init(void)
{
    uint8_t cmd_enable = 0x51;  /* ENABLE, PON=1, AEN=1 */
    uint8_t cfg = 0x12;          /* AGAIN=med (x25), ATIME=100ms */
    if (i2c_write_reg(TSL2591_ADDR, 0x00, &cmd_enable, 1) != 0)
        return -1;
    delay_ms(1);
    if (i2c_write_reg(TSL2591_ADDR, 0x01, &cfg, 1) != 0)
        return -1;
    delay_ms(120);  /* first integration */
    return 0;
}

int tsl2591_read(float *lux)
{
    uint8_t reg = 0x14;  /* CH0DATA_L */
    uint8_t raw[4];
    if (i2c_read_reg(TSL2591_ADDR, reg, raw, 4) != 0)
        return -1;

    uint16_t ch0 = (raw[1] << 8) | raw[0];  /* full spectrum */
    uint16_t ch1 = (raw[3] << 8) | raw[2];  /* IR */

    /* TSL2591 lux formula (gain=25x, integration=100ms → 2.5x factor) */
    float cpl = 2.5f * 100.0f;  /* counts per lux */
    float lux_val = ((float)ch0 - (float)ch1) * (1.0f - (float)ch1 / (float)(ch0 + 1)) / cpl;
    *lux = (lux_val > 0.0f) ? lux_val : 0.0f;
    return 0;
}

/* ---- DS18B20 sapwood temperature (1-Wire, parasitic power) ---- */

/* 1-Wire low-level: implemented in port layer */
extern int  onewire_reset(void);
extern void onewire_write_byte(uint8_t byte);
extern uint8_t onewire_read_byte(void);

int ds18b20_read(float *temp_c)
{
    /* Strong pull-up power */
    gpio_write(PIN_1WIRE_POWER, 1);

    if (onewire_reset() != 0) {
        gpio_write(PIN_1WIRE_POWER, 0);
        return -1;
    }

    /* Skip ROM (single device) + Convert T (0x44) */
    onewire_write_byte(0xCC);
    onewire_write_byte(0x44);

    /* Hold strong pull-up during conversion (~750 ms for 12-bit) */
    delay_ms(750);
    gpio_write(PIN_1WIRE_POWER, 0);

    if (onewire_reset() != 0)
        return -1;

    /* Skip ROM + Read Scratchpad (0xBE) */
    onewire_write_byte(0xCC);
    onewire_write_byte(0xBE);

    uint8_t scratch[9];
    for (int i = 0; i < 9; i++)
        scratch[i] = onewire_read_byte();

    /* Temperature: 16-bit signed, 0.0625 °C per LSB */
    int16_t raw = (scratch[1] << 8) | scratch[0];
    *temp_c = (float)raw * 0.0625f;

    return 0;
}

/* ---- MAX17048 fuel gauge ---- */

int max17048_init(void)
{
    /* The MAX17048 auto-loads its model on power-up.
     * Quick-start command to reset if needed.
     */
    uint16_t qs = 0x4000;
    if (i2c_write_reg(MAX17048_ADDR, 0x06, (uint8_t *)&qs, 2) != 0)
        return -1;
    delay_ms(500);  /* model load delay */
    return 0;
}

int max17048_read_soc(float *percent)
{
    uint8_t raw[2];
    if (i2c_read_reg(MAX17048_ADDR, 0x04, raw, 2) != 0)
        return -1;
    /* SOC register: MSB = integer %, LSB = 1/256 % */
    *percent = (float)raw[0] + (float)raw[1] / 256.0f;
    return 0;
}

int max17048_read_voltage(float *volts)
{
    uint8_t raw[2];
    if (i2c_read_reg(MAX17048_ADDR, 0x02, raw, 2) != 0)
        return -1;
    /* VCELL register: 78.125 µV per LSB (12-bit, 4mV per bit in upper byte) */
    uint16_t vcell = (raw[0] << 8) | raw[1];
    *volts = (float)vcell * 78.125e-6f;
    return 0;
}

/* ---- High-level sensor read ---- */

int sensors_read_all(sensor_data_t *data)
{
    int errors = 0;

    if (sht45_read(&data->air_temp_c, &data->rh_pct) != 0) {
        data->air_temp_c = NAN;
        data->rh_pct = NAN;
        errors++;
    }

    if (tsl2591_read(&data->light_lux) != 0) {
        data->light_lux = NAN;
        errors++;
    }

    if (ds18b20_read(&data->sapwood_temp_c) != 0) {
        data->sapwood_temp_c = NAN;
        errors++;
    }

    if (max17048_read_soc(&data->battery_pct) != 0) {
        data->battery_pct = NAN;
        errors++;
    }

    if (max17048_read_voltage(&data->battery_v) != 0) {
        data->battery_v = NAN;
        errors++;
    }

    /* Compute VPD if we have T and RH */
    if (!isnan(data->air_temp_c) && !isnan(data->rh_pct)) {
        data->vpd_kpa = heat_ratio_compute_vpd(data->air_temp_c, data->rh_pct);
    } else {
        data->vpd_kpa = NAN;
    }

    return (errors > 0) ? -1 : 0;
}