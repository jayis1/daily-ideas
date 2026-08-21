/*
 * kappa-pin / firmware / main / adc24.h
 * ADS122U04 24-bit delta-sigma ADC driver (SPI)
 *
 * Configured for 4-wire PT1000 RTD measurement:
 *   - IDAC1 → AIN0 (excitation positive)  = 1 mA
 *   - IDAC2 → AIN1 (excitation negative)  = 1 mA (ratiometric)
 *   - Differential input: AIN2 - AIN3 (sense leads)
 *   - PGA gain = 1, data rate = 120 SPS (turbo mode for transient capture)
 *
 * MIT License.
 */
#ifndef ADC24_H
#define ADC24_H

#include <stdint.h>
#include <stdbool.h>

/* ADS122U04 SPI pins (shared SPI bus) */
#define ADC24_CS_PIN        3
#define ADC24_DRDY_PIN      4
#define SPI_SCK_PIN         5
#define SPI_MISO_PIN        6
#define SPI_MOSI_PIN        7
#define SPI_HOST            SPI2_HOST

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
#define ADC_DR_TURBO        0x07  /* turbo mode bit in config1 */

/* IDAC current settings */
#define ADC_IDAC_OFF        0x00
#define ADC_IDAC_10UA       0x01
#define ADC_IDAC_50UA       0x02
#define ADC_IDAC_100UA      0x03
#define ADC_IDAC_250UA      0x04
#define ADC_IDAC_500UA      0x05
#define ADC_IDAC_750UA      0x06
#define ADC_IDAC_1000UA     0x07  /* 1 mA */
#define ADC_IDAC_1500UA     0x08
#define ADC_IDAC_2000UA     0x09

/* Ratiometric RTD reference resistor (precision) */
#define RTD_REF_RESISTOR    8200.0f   /* 8.2 kΩ precision reference */
#define PT1000_R0           1000.0f   /* PT1000 at 0°C */
#define PT1000_A            3.9083e-3f
#define PT1000_B            (-5.775e-7f)
#define PT1000_C            (-4.183e-12f)

typedef enum {
    ADC_OK = 0,
    ADC_ERR_SPI = -1,
    ADC_ERR_TIMEOUT = -2,
    ADC_ERR_NOT_READY = -3,
} adc_err_t;

/* Initialize ADS122U04 for 4-wire RTD, 1 mA IDAC, 120 SPS turbo */
adc_err_t adc24_init(void);

/* Read raw 24-bit ADC code (blocking, waits for DRDY) */
adc_err_t adc24_read_raw(int32_t *raw);

/* Read RTD resistance in ohms (ratiometric) */
adc_err_t adc24_read_resistance(float *r_ohm);

/* Read temperature in °C from PT1000 via Callendar-Van Dusen */
adc_err_t adc24_read_temperature(float *temp_c);

/* Set data rate */
adc_err_t adc24_set_data_rate(uint8_t rate);

/* Start/synchronize conversion */
adc_err_t adc24_start_sync(void);

#endif /* ADC24_H */