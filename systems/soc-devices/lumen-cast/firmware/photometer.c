/**
 * lumen_cast/firmware/photometer.c — OPT3001 illuminance sensor driver
 *
 * Texas Instruments OPT3001DNPT
 *   I2C address: 0x44 (ADDR pin to GND) or 0x45 (ADDR to VDD)
 *   Range: 0.045 – 188,000 lux (auto-range)
 *   23-bit effective resolution
 *   Spectral response: closely matched to photopic V(λ)
 *
 * Registers:
 *   0x00 RESULT (16-bit)
 *   0x01 CONFIGURATION
 *   0x02 LOW_LIMIT
 *   0x03 HIGH_LIMIT
 *   0x04 MANUFACTURER_ID (0x5449)
 *   0x05 DEVICE_ID (0x3001)
 */

#include "main.h"
#include <string.h>

#define TAG "OPT"

#define OPT3001_REG_RESULT     0x00
#define OPT3001_REG_CONFIG     0x01
#define OPT3001_REG_MANUF_ID   0x04
#define OPT3001_REG_DEVICE_ID  0x05

/* Configuration register bits:
 * [15:12] RN   = range select (1100b = auto-range, full scale)
 * [11]    CT   = conversion time (0 = 100ms, 1 = 800ms)
 * [10]    M    = mode (0 = shutdown, 1 = single-shot)
 * [9]     OVF  = overflow flag
 * [8]     CRF  = conversion ready flag
 * [7]     FH   = fault high
 * [6]     FL   = fault low
 * [5:4]   POL  = INT pin polarity
 * [3]     ME   = mask exponent
 * [2:0]   FC   = fault count
 *
 * For continuous 100ms conversions: CONFIG = 0xC610
 * (RN=1100 auto, CT=0 100ms, M=1 continuous, ME=0)
 */
#define OPT3001_CONFIG_CONT_100MS  0xC610
#define OPT3001_CONFIG_CONT_800MS  0xCE10

int opt3001_init(void)
{
    /* Verify device ID */
    uint16_t manuf = i2c_read16(OPT3001_I2C_ADDR, OPT3001_REG_MANUF_ID);
    uint16_t dev_id = i2c_read16(OPT3001_I2C_ADDR, OPT3001_REG_DEVICE_ID);

    if (manuf != 0x5449 || dev_id != 0x3001) {
        LOGE(TAG, "OPT3001 not found (manuf=0x%04X dev=0x%04X)", manuf, dev_id);
        return -1;
    }

    LOGI(TAG, "OPT3001 detected (manuf=0x%04X dev=0x%04X)", manuf, dev_id);

    /* Configure: auto-range, 100ms, continuous conversion */
    i2c_write16(OPT3001_I2C_ADDR, OPT3001_REG_CONFIG, OPT3001_CONFIG_CONT_100MS);

    delay_ms(150);  /* wait for first conversion */
    return 0;
}

int opt3001_read_lux(float *lux)
{
    /* Read result register (16-bit)
     * Format: [15:12] exponent (N), [11:0] mantissa (R)
     * lux = 0.01 × R × 2^N
     */
    uint16_t raw = i2c_read16(OPT3001_I2C_ADDR, OPT3001_REG_RESULT);

    uint32_t exponent = (raw >> 12) & 0x0F;
    uint32_t mantissa = raw & 0x0FFF;

    /* Check for overflow (exponent = 0x0F) */
    if (exponent == 0x0F) {
        LOGW(TAG, "OPT3001 overflow (too bright)");
        *lux = 188000.0f;
        return -1;
    }

    /* lux = 0.01 × mantissa × 2^exponent */
    float result = 0.01f * (float)mantissa;
    for (uint32_t i = 0; i < exponent; i++)
        result *= 2.0f;

    *lux = result;
    return 0;
}