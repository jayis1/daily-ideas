/*
 * hall-puck / firmware / Core / Inc / ads122u04.h
 * ADS122U04 24-bit delta-sigma ADC driver (SPI)
 *
 * Configured for differential voltage measurement with INA333:
 *   - AIN0-AIN1 differential, PGA gain 1-128
 *   - Data rate 20-1000 SPS
 *   - Internal voltage reference (2.048V) or external
 *
 * MIT License.
 */
#ifndef ADS122U04_H
#define ADS122U04_H

#include <stdint.h>
#include <stdbool.h>

/* ADS122U04 registers */
#define ADC_REG_CONFIG0     0x00
#define ADC_REG_CONFIG1     0x01
#define ADC_REG_CONFIG2     0x02
#define ADC_REG_CONFIG3     0x03
#define ADC_REG_FIR         0x04
#define ADC_REG_IDAC        0x05
#define ADC_REG_RTDC        0x06
#define ADC_REG_GPIOCFG     0x07

/* PGA gain settings */
#define ADC_GAIN_1          0x00
#define ADC_GAIN_2          0x01
#define ADC_GAIN_4          0x02
#define ADC_GAIN_8          0x03
#define ADC_GAIN_16         0x04
#define ADC_GAIN_32         0x05
#define ADC_GAIN_64         0x06
#define ADC_GAIN_128        0x07

/* Data rate (normal mode) */
#define ADC_DR_20SPS        0x00
#define ADC_DR_45SPS        0x01
#define ADC_DR_90SPS        0x02
#define ADC_DR_175SPS       0x03
#define ADC_DR_330SPS       0x04
#define ADC_DR_600SPS       0x05
#define ADC_DR_1000SPS      0x06

/* Voltage reference */
#define ADC_VREF_INTERNAL   0x00  /* 2.048V internal */
#define ADC_VREF_EXTERNAL   0x02  /* REFP0/REFN0 */
#define ADC_VREF_ANALOG     0x03  /* AVDD/AVSS */

/* INA333 gain settings (external resistor + analog switch) */
#define INA_GAIN_1X         0   /* R_gain = open (unity) */
#define INA_GAIN_10X        1   /* R_gain = 5.6 kΩ */
#define INA_GAIN_100X       2   /* R_gain = 560 Ω */
#define INA_GAIN_1000X      3   /* R_gain = 56 Ω */

typedef enum {
    ADC_OK = 0,
    ADC_ERR_SPI = -1,
    ADC_ERR_TIMEOUT = -2,
    ADC_ERR_NOT_READY = -3,
} adc_err_t;

/* Initialize ADS122U04 for differential voltage measurement */
adc_err_t ads122u04_init(void);

/* Read raw 24-bit ADC code (blocking, waits for DRDY) */
adc_err_t ads122u04_read_raw(int32_t *raw);

/* Read voltage in volts (differential, after INA333 gain) */
adc_err_t ads122u04_read_voltage(float *voltage);

/* Read sample-terminal voltage in µV (accounts for INA333 gain) */
adc_err_t ads122u04_read_voltage_uv(float *voltage_uv);

/* Set PGA gain */
adc_err_t ads122u04_set_gain(uint8_t gain);

/* Set data rate */
adc_err_t ads122u04_set_data_rate(uint8_t rate);

/* Set INA333 gain (external analog switch) */
void ads122u04_set_ina_gain(uint8_t gain);

/* Auto-range INA333 gain for optimal resolution */
uint8_t ads122u04_auto_range(float voltage_uv);

/* Start/synchronize conversion */
adc_err_t ads122u04_start_sync(void);

/* Reset ADC */
adc_err_t ads122u04_reset(void);

#endif /* ADS122U04_H */