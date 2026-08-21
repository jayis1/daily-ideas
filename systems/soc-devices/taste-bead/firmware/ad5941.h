/* ad5941.h — AD5941 analog front-end driver for Taste Bead
 *
 * AD5941 is Analog Devices' high-precision impedance and electrochemical
 * AFE. It contains:
 *   - 12-bit/16-bit voltage DAC for excitation
 *   - Transimpedance amplifier (TIA) with programmable gain
 *   - 16-bit/24-bit sigma-delta ADC
 *   - On-chip DFT engine (compute magnitude+phase in hardware)
 *   - Multiple internal switches for calibration and measurement modes
 *
 * We use it in impedance measurement mode (MTRP/INAMP/RTIA path) to do
 * multi-frequency EIS across the electrode array.
 */

#ifndef TASTE_BEAD_AD5941_H
#define TASTE_BEAD_AD5941_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

/* AD5941 register addresses (selected — full list in datasheet) */
#define AD5941_REG_AFECON      0x1000
#define AD5941_REG_AFE_HPDAC   0x2000
#define AD5941_REG_AFE_LPDAC   0x2008
#define AD5941_REG_AFE_TIA     0x2009
#define AD5941_REG_AFE_PGA     0x200A
#define AD5941_REG_AFE_ADCPga  0x200B
#define AD5941_REG_AFE_DFTCFG  0x2010
#define AD5941_REG_AFE_DFTNUM  0x2011
#define AD5941_REG_AFE_FREQ    0x2012
#define AD5941_REG_AFE_SWCON   0x2100
#define AD5941_REG_AFE_CALCON  0x2101

/* TIA gain resistor values (Ω) — selectable via register */
#define RTIA_200      200
#define RTIA_1K       1000
#define RTIA_4K       4000
#define RTIA_10K      10000
#define RTIA_100K     100000
#define RTIA_1M       1000000

/* Excitation amplitude (mV peak) */
#define EXC_10MV      10
#define EXC_50MV      50
#define EXC_100MV     100
#define EXC_200MV     200
#define EXC_400MV     400
#define EXC_800MV     800
#define EXC_1100MV    1100

/* Measurement result */
typedef struct {
    float z_mag;     /* Impedance magnitude (Ω) */
    float z_phase;   /* Impedance phase (degrees) */
    float z_real;    /* Real part (Ω) */
    float z_imag;    /* Imaginary part (Ω) */
    float freq_hz;   /* Actual frequency (Hz) */
} ad5941_z_point_t;

/* Calibration data (stored in NVS) */
typedef struct {
    bool open_done;
    bool short_done;
    bool kcl_done;
    float open_mag[20];      /* Open-circuit magnitude at each freq */
    float open_phase[20];    /* Open-circuit phase at each freq */
    float short_mag[20];     /* Short-circuit magnitude at each freq */
    float short_phase[20];   /* Short-circuit phase at each freq */
    float kcl_mag[20];       /* 0.01M KCl magnitude at each freq */
    float kcl_phase[20];     /* 0.01M KCl phase at each freq */
    float rtia_actual;       /* Actual RTIA value used */
    int64_t cal_timestamp;   /* When calibration was performed */
} ad5941_cal_t;

/* Initialize AD5941 over SPI */
esp_err_t ad5941_init(int cs_pin, int sck_pin, int miso_pin,
                      int mosi_pin, int irq_pin, int reset_pin);

/* Perform a single impedance measurement at a given frequency */
esp_err_t ad5941_measure_z(float freq_hz, float exc_amplitude,
                            uint32_t rtia, ad5941_z_point_t *result);

/* Run a full frequency sweep and return results for one electrode */
esp_err_t ad5941_sweep(const float *freqs, int num_freqs,
                        float exc_amplitude, uint32_t rtia,
                        ad5941_z_point_t *results);

/* Set/get calibration data */
esp_err_t ad5941_set_calibration(const ad5941_cal_t *cal);
esp_err_t ad5941_get_calibration(ad5941_cal_t *cal);

/* Auto-select optimal RTIA for a given electrode/frequency */
uint32_t ad5941_select_rtia(float freq_hz, float exc_amplitude);

/* Apply calibration correction to raw measurement */
void ad5941_apply_calibration(ad5941_z_point_t *raw,
                               const ad5941_cal_t *cal,
                               int freq_index);

/* Hardware reset */
void ad5941_reset(void);

/* Get last error */
const char *ad5941_last_error(void);

#endif /* TASTE_BEAD_AD5941_H */