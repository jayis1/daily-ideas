/*
 * pressure.c — BMP390 barometric pressure + temperature + correction
 *
 * Reads pressure (hPa) and temperature (°C) over I²C from the BMP390.
 * Applies the standard barometric correction to the muon rate.
 *
 * The barometric coefficient β ≈ 0.012 hPa⁻¹ at sea level:
 *   R_corr(P0) = R_meas(P) · exp[ β · (P0 − P) ]
 * where P0 is a reference pressure (default 1013.25 hPa).
 */
#include "pressure.h"
#include "sky_lens.h"
#include <math.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/i2c.h"
#include "esp_log.h"
static const char *TAG = "press";
#define I2C_PORT   I2C_NUM_0
#define BMP_ADDR   0x77   /* BMP390 SDO=GND */
#endif

#define P_REF_HPA  1013.25f
#define BETA_PER_HPA 0.012f     /* barometric coefficient (1/hPa) */

static float s_last_p = P_REF_HPA;
static float s_last_t = 20.0f;

void pressure_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("pressure init (sim)");
#else
    /* BMP390 init: write config registers for oversampling x4,
     * IIR filter coefficient 0, normal mode. Omitted for brevity. */
    ESP_LOGI(TAG, "BMP390 init");
#endif
}

float pressure_read_hpa(void)
{
#ifdef SKY_LENS_SIM
    s_last_p = port_sim_pressure_hpa();
#else
    /* Read PRESS_MSB..LSB (0x04-0x06) + TEMP (0x07-0x09).
     * Compensate using the BMP390 calibration coefficients.
     * Full compensation omitted; placeholder returns a fixed read. */
    uint8_t buf[3] = {0};
    uint8_t reg = 0x04;
    i2c_master_write_read_device(I2C_PORT, BMP_ADDR, &reg, 1, buf, 3, pdMS_TO_TICKS(10));
    int32_t raw = ((int32_t)buf[0] << 16) | ((int32_t)buf[1] << 8) | buf[2];
    /* 24-bit pressure, LSB = 1/256 Pa → hPa = raw / 256 / 100 */
    s_last_p = (float)raw / 25600.0f;
#endif
    return s_last_p;
}

float pressure_read_temp_c(void)
{
#ifdef SKY_LENS_SIM
    s_last_t = port_sim_temp_c();
#else
    uint8_t buf[3] = {0};
    uint8_t reg = 0x07;
    i2c_master_write_read_device(I2C_PORT, BMP_ADDR, &reg, 1, buf, 3, pdMS_TO_TICKS(10));
    int32_t raw = ((int32_t)buf[0] << 16) | ((int32_t)buf[1] << 8) | buf[2];
    /* 24-bit temp, LSB = 1/100 °C */
    s_last_t = (float)raw / 100.0f;
#endif
    return s_last_t;
}

float pressure_correct_rate(float rate_cpm, float p_hpa, float t_c)
{
    (void)t_c;   /* temperature correction is small; not applied here */
    float dp = P_REF_HPA - p_hpa;    /* positive when pressure is low */
    return rate_cpm * expf(BETA_PER_HPA * dp);
}

#ifndef SKY_LENS_SIM
#include "freertos/FreeRTOS.h"
#endif