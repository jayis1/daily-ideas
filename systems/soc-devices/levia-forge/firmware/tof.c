/*
 * Levia Forge — VL53L0X Time-of-Flight Driver (I2C0)
 * Measures distance to levitated particle for height feedback.
 *
 * SPDX-License-Identifier: MIT
 */
#include "tof.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include <string.h>

#define VL53L0X_ADDR      0x29

/* VL53L0X registers */
#define REG_SYSRANGE_START              0x00
#define REG_RESULT_INTERRUPT_STATUS     0x13
#define REG_RESULT_RANGE_STATUS         0x14
#define REG_I2C_SLAVE_DEVICE_ADDRESS    0x8A
#define REG_VHV_CONFIG_PAD_SCL_SDA__EXSUP_SUPPLY  0x30
#define REG_MSRC_CONFIG_CONTROL         0x60
#define REG_SYSTEM_SEQUENCE_CONFIG      0x01
#define REG_CORE_CONFIG_STATUS          0x2F
#define REG_FINAL_RANGE_CONFIG_MIN_SNR  0x67
#define REG_FINAL_RANGE_CONFIG_VALID_PHASE_LOW  0x69
#define REG_FINAL_RANGE_CONFIG_VALID_PHASE_HIGH 0x6A
#define REG_SYSTEM_INTERMEASUREMENT_PERIOD  0x04

static bool initialized = false;
static uint8_t sensor_addr = VL53L0X_ADDR;

static bool i2c_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = { reg, val };
    return i2c_write_blocking(i2c0, sensor_addr, buf, 2, false) == 2;
}

static bool i2c_read_reg(uint8_t reg, uint8_t *val, size_t len)
{
    if (i2c_write_blocking(i2c0, sensor_addr, &reg, 1, true) != 1)
        return false;
    return i2c_read_blocking(i2c0, sensor_addr, val, len, false) == (int)len;
}

static bool vl53l0x_data_init(void)
{
    /* Set 2.8V mode (bit 0 of reg 0x89) — required for proper operation */
    uint8_t val;
    if (!i2c_read_reg(0x89, &val, 1)) return false;
    val &= ~0x01;
    if (!i2c_write_reg(0x89, val)) return false;

    /* Set I2C standard mode */
    if (!i2c_write_reg(0x88, 0x00)) return false;

    /* MSRC config: signal rate limit */
    if (!i2c_read_reg(REG_MSRC_CONFIG_CONTROL, &val, 1)) return false;
    val |= 0x01;
    if (!i2c_write_reg(REG_MSRC_CONFIG_CONTROL, val)) return false;

    /* Set signal rate limit to 0.1 MCPS (6.3 / 10) */
    if (!i2c_write_reg(0x44, 0x00)) return false;
    if (!i2c_write_reg(0x45, 0x63)) return false;

    /* System sequence: enable both steps (0x08 and 0x10) */
    if (!i2c_write_reg(REG_SYSTEM_SEQUENCE_CONFIG, 0xFF)) return false;

    return true;
}

static bool vl53l0x_static_init(void)
{
    /* Simplified static init — full SPAD calibration omitted for brevity.
     * In production, perform SPAD calibration per datasheet section 2.4. */
    if (!i2c_write_reg(REG_SYSTEM_SEQUENCE_CONFIG, 0x01)) return false;
    /* ... SPAD calibration would go here ... */
    if (!i2c_write_reg(REG_SYSTEM_SEQUENCE_CONFIG, 0xFF)) return false;
    return true;
}

static bool vl53l0x_perform_ref_calibration(void)
{
    /* Reference calibration steps (simplified) */
    if (!i2c_write_reg(REG_SYSTEM_SEQUENCE_CONFIG, 0x09)) return false;
    if (!i2c_write_reg(0x96, 0x00)) return false;
    /* ... full calibration sequence per datasheet ... */
    if (!i2c_write_reg(REG_SYSTEM_SEQUENCE_CONFIG, 0xFF)) return false;
    return true;
}

static bool vl53l0x_set_continuous_mode(void)
{
    /* Set system mode: continuous (bit 1 of SYSRANGE) */
    if (!i2c_write_reg(REG_SYSRANGE_START, 0x03)) return false;
    return true;
}

void tof_init(void)
{
    /* Initialize I2C0 at 400 kHz */
    i2c_init(i2c0, 400000);
    gpio_set_function(PIN_I2C0_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C0_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C0_SDA);
    gpio_pull_up(PIN_I2C0_SCL);

    /* Reset sensor via XSHUT if connected (optional, not shown here) */
    sleep_ms(10);

    /* Check if sensor is present */
    uint8_t val;
    if (!i2c_read_reg(0xC0, &val, 1) || val != 0xEE) {
        initialized = false;
        return;
    }

    /* Initialize sensor */
    if (!vl53l0x_data_init()) { initialized = false; return; }
    if (!vl53l0x_static_init()) { initialized = false; return; }
    if (!vl53l0x_perform_ref_calibration()) { initialized = false; return; }
    if (!vl53l0x_set_continuous_mode()) { initialized = false; return; }

    initialized = true;
}

float tof_read_distance_mm(void)
{
    if (!initialized) return -1.0f;

    /* Check if new data is available */
    uint8_t status;
    if (!i2c_read_reg(REG_RESULT_INTERRUPT_STATUS, &status, 1))
        return -1.0f;

    if (!(status & 0x04))
        return -1.0f;  /* no new data */

    /* Read 12-bit distance (big-endian, 2 bytes at reg 0x14+10) */
    uint8_t data[2];
    if (!i2c_read_reg(0x14 + 10, data, 2))
        return -1.0f;

    uint16_t distance = (data[0] << 8) | data[1];

    /* Clear interrupt by writing to RESULT_INTERRUPT_STATUS */
    i2c_write_reg(REG_SYSTEM_INTERRUPT_CLEAR, 0x01);

    if (distance == 8190 || distance == 8191)
        return -1.0f;  /* out of range */

    return (float)distance;
}

bool tof_is_present(void)
{
    return initialized;
}