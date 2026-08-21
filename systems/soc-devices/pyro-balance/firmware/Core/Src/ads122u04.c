/*
 * pyro-balance / Core/Src/ads122u04.c
 * ADS122U04 24-bit ADC driver (I²C) — PT1000 4-wire RTD.
 */
#include "ads122u04.h"
#include "flash_store.h"

extern I2C_HandleTypeDef hi2c2;

static uint8_t ads_write_reg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg | 0x40, val };
    return HAL_I2C_Master_Transmit(&hi2c2, ADS122U04_ADDR, buf, 2, 50);
}

static uint8_t ads_read_reg(uint8_t reg, uint8_t* val) {
    uint8_t r = reg | 0x20;
    HAL_I2C_Master_Transmit(&hi2c2, ADS122U04_ADDR, &r, 1, 50);
    return HAL_I2C_Master_Receive(&hi2c2, ADS122U04_ADDR, val, 1, 50);
}

void ads_init(void) {
    /* Config0: AINp=AIN0, AINn=AIN1, gain=1, PGA enabled */
    ads_write_reg(ADS122U04_REG_CONFIG0, 0x01);
    /* Config1: 250 SPS, normal mode, continuous, temperature sensor off */
    ads_write_reg(ADS122U04_REG_CONFIG1, 0x04);
    /* Config2: Vref = internal 2.048V, IDAC1 → AIN2 (250 µA) */
    ads_write_reg(ADS122U04_REG_CONFIG2, 0x0A);
    /* Config3: IDAC magnitude 250 µA */
    ads_write_reg(ADS122U04_REG_CONFIG3, 0x10);
}

void ads_set_rtd_mode(void) { ads_init(); }

void ads_start_conversion(void) {
    uint8_t cmd = 0x08; /* START */
    HAL_I2C_Master_Transmit(&hi2c2, ADS122U04_ADDR, &cmd, 1, 50);
}

bool ads_ready(void) {
    /* read config2 bit DRDY not available in this stub; assume ready after delay */
    return true;
}

int32_t ads_read_raw(void) {
    uint8_t cmd = 0x10; /* RDATA */
    uint8_t buf[3] = {0,0,0};
    HAL_I2C_Master_Transmit(&hi2c2, ADS122U04_ADDR, &cmd, 1, 50);
    HAL_I2C_Master_Receive(&hi2c2, ADS122U04_ADDR, buf, 3, 50);
    int32_t v = ((int32_t)buf[0] << 16) | ((int32_t)buf[1] << 8) | buf[2];
    if (v & 0x800000) v |= ~0xFFFFFF;
    return v;
}

float ads_read_volts(void) {
    int32_t raw = ads_read_raw();
    /* Vref 2.048V, gain 1 → LSB = 2.048/2^23 = 0.244 µV */
    return raw * (2.048f / 8388608.0f);
}

float ads_read_temp_c(void) {
    /* ratiometric: RTD across AIN0/AIN1, IDAC drives through RTD + reference R.
       Simple method: read voltage, convert to resistance, then CVD. */
    float v = ads_read_volts();
    /* assume 250 µA excitation → R = V / 250e-6 */
    float r = v / 0.000250f;
    return rtd_resistance_to_temp(r);
}

float rtd_resistance_to_temp(float r_ohm) {
    /* Callendar–Van Dusen: R(t) = R0*(1 + A*t + B*t^2), t>=0
       A = 3.9083e-3, B = -5.775e-7, R0 = 1000 (PT1000) */
    float R0 = (g_cfg.ads_rtd_r0 > 0) ? g_cfg.ads_rtd_r0 : 1000.0f;
    float A = 3.9083e-3f, B = -5.775e-7f;
    /* solve quadratic: B*t^2 + A*t + (1 - r/R0) = 0 */
    float c = 1.0f - r_ohm / R0;
    float disc = A*A - 4.0f*B*c;
    if (disc < 0) return -1000.0f;
    float t = (-A + sqrtf(disc)) / (2.0f*B);
    return t;
}