/*
 * ad5933.h — AD5933 impedance analyzer driver
 *
 * Controls the AD5933 to perform DFT measurements at each frequency
 * point in the sweep. The AD5933 provides real/imaginary impedance
 * data that is converted to admittance for the π-network method.
 */

#ifndef QUARTZ_TUNER_AD5933_H
#define QUARTZ_TUNER_AD5933_H

#include "types.h"

/* AD5933 I2C address */
#define AD5933_ADDR     0x0D    /* A0=GND */

/* AD5933 registers */
#define AD5933_REG_CTRL_H       0x80
#define AD5933_REG_CTRL_L       0x81
#define AD5933_REG_START_FREQ_H 0x82
#define AD5933_REG_START_FREQ_M 0x83
#define AD5933_REG_START_FREQ_L 0x84
#define AD5933_REG_FREQ_INC_H   0x85
#define AD5933_REG_FREQ_INC_M   0x86
#define AD5933_REG_FREQ_INC_L   0x87
#define AD5933_REG_NUM_INC_H    0x88
#define AD5933_REG_NUM_INC_L    0x89
#define AD5933_REG_SETTLE_H     0x8A
#define AD5933_REG_SETTLE_L     0x8B
#define AD5933_REG_STATUS       0x8F
#define AD5933_REG_REAL_H       0x94
#define AD5933_REG_REAL_L       0x95
#define AD5933_REG_IMAG_H       0x96
#define AD5933_REG_IMAG_L       0x97

/* AD5933 control commands */
#define AD5933_CTRL_INIT_START_FREQ  0x10
#define AD5933_CTRL_START_SWEEP      0x20
#define AD5933_CTRL_INC_FREQ         0x30
#define AD5933_CTRL_REPEAT_FREQ      0x40
#define AD5933_CTRL_POWER_DOWN       0xA0
#define AD5933_CTRL_STANDBY          0xB0
#define AD5933_CTRL_TEMP_MEASURE     0x90

/* Initialize AD5933: set MCLK source, configure for impedance measurement */
int ad5933_init(void);

/* Start a measurement at a specific frequency (set by Si5351A externally).
 * Since the AD5933's internal sweep is not used (the Si5351A does the
 * frequency stepping), we program the AD5933 for single-frequency DFT
 * measurement at each point. */
int ad5933_measure_at_freq(uint32_t freq_hz, complex_t *result);

/* Read the DFT result (real + imaginary) at the current frequency */
int ad5933_read_dft(complex_t *result);

/* Set the number of settling cycles (default: 10) */
void ad5933_set_settling(uint16_t cycles);

/* Set the number of DFT points (default: 1024) */
void ad5933_set_dft_points(uint16_t points);

/* Set the gain range (0 = ±5.12 V, 1 = ±2.56 V, etc.) */
void ad5933_set_range(uint8_t range);

/* Set the PGA gain (1x or 5x) */
void ad5933_set_pga_gain(bool gain_5x);

/* Convert raw DFT to calibrated admittance using calibration coefficients */
void ad5933_to_admittance(const complex_t *raw, const calibration_t *cal,
                           complex_t *admittance);

/* Read AD5933 internal temperature (for reference) */
float ad5933_read_temp(void);

/* Power down AD5933 for sleep */
void ad5933_sleep(void);
void ad5933_wake(void);

#endif /* QUARTZ_TUNER_AD5933_H */