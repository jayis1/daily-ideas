/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * spectrometer.c — AS7343 driver and spectral acquisition engine
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "spectrometer.h"
#include "led_driver.h"
#include <math.h>
#include <string.h>

/* AS7343 Register Map */
#define AS7343_REG_WHO_AM_I      0x92
#define AS7343_REG_ENABLE        0x80
#define AS7343_REG_ATIME         0x81
#define AS7343_REG_ASTEP         0xCA   /* Integration step count (12-bit) */
#define AS7343_REG_AGAIN         0x83
#define AS7343_REG_CFG0          0xAB
#define AS7343_REG_CFG1          0xAC
#define AS7343_REG_CFG6          0xAF
#define AS7343_REG_CH0_DATA_L    0x61   /* F1 415nm */
#define AS7343_REG_CH1_DATA_L    0x63   /* F2 445nm */
#define AS7343_REG_CH2_DATA_L    0x65   /* F3 480nm */
#define AS7343_REG_CH3_DATA_L    0x67   /* F4 515nm */
#define AS7343_REG_CH4_DATA_L    0x69   /* F5 555nm */
#define AS7343_REG_CH5_DATA_L    0x6B   /* F6 590nm */
#define AS7343_REG_CH6_DATA_L    0x6D   /* F7 630nm */
#define AS7343_REG_CH7_DATA_L    0x6F   /* F8 680nm */
#define AS7343_REG_NIR_DATA_L    0x71   /* NIR 910nm */
#define AS7343_REG_CLEAR_DATA_L  0x73   /* Clear (broadband) */
#define AS7343_REG_INTEN         0xF4   /* LED current control */
#define AS7343_REG_ID            0x9C

/* AS7343 Channel wavelengths (nm) */
static const float as7343_wavelengths[AS7343_NUM_CHANNELS] = {
    415.0f, /* F1 */
    445.0f, /* F2 */
    480.0f, /* F3 */
    515.0f, /* F4 */
    555.0f, /* F5 */
    590.0f, /* F6 */
    630.0f, /* F7 */
    680.0f, /* F8 */
    910.0f, /* NIR */
};

/* AS7343 Channel FWHM (nm) — approximate */
static const float as7343_fwhm[AS7343_NUM_CHANNELS] = {
    22.0f, 28.0f, 26.0f, 28.0f, 26.0f, 22.0f, 22.0f, 18.0f, 16.0f
};

/* ---- SPI helpers ---- */
extern SPI_HandleTypeDef hspi1;

static inline void AS7343_CS_Low(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
}

static inline void AS7343_CS_High(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}

static uint8_t AS7343_ReadReg(uint8_t reg)
{
    uint8_t tx[2] = { reg, 0x00 };
    uint8_t rx[2] = { 0 };
    AS7343_CS_Low();
    HAL_SPI_TransmitReceive(&hspi1, tx, rx, 2, 100);
    AS7343_CS_High();
    return rx[1];
}

static void AS7343_WriteReg(uint8_t reg, uint8_t val)
{
    uint8_t tx[2] = { reg | 0x80, val }; /* Write bit set */
    AS7343_CS_Low();
    HAL_SPI_Transmit(&hspi1, tx, 2, 100);
    AS7343_CS_High();
}

static void AS7343_ReadBurst(uint8_t startReg, uint8_t *buf, uint16_t len)
{
    uint8_t tx = startReg | 0x20; /* Auto-increment bit */
    AS7343_CS_Low();
    HAL_SPI_Transmit(&hspi1, &tx, 1, 100);
    HAL_SPI_Receive(&hspi1, buf, len, 200);
    AS7343_CS_High();
}

/* ========================================================================
 * AS7343 Initialization
 * ======================================================================== */
HAL_StatusTypeDef Spectrometer_Init(void)
{
    uint8_t id;

    /* Verify device ID */
    id = AS7343_ReadReg(AS7343_REG_WHO_AMI);
    if (id != 0x39) {
        return HAL_ERROR;
    }

    /* Enable the spectral engine and wait for power-on */
    AS7343_WriteReg(AS7343_REG_ENABLE, 0x01);  /* PON = 1 */
    HAL_Delay(10);

    /* Configure spectral measurement */
    AS7343_WriteReg(AS7343_REG_ATIME, 29);      /* ATIME = 29 → 100ms integration */
    AS7343_WriteReg(AS7343_REG_ASTEP, 999);     /* ASTEP = 999 → max integration steps */
    AS7343_WriteReg(AS7343_REG_AGAIN, 0x09);    /* Gain = 256x (high sensitivity) */

    /* Configure LED */
    AS7343_WriteReg(AS7343_REG_CFG6, 0x04);     /* LED drive enabled */

    return HAL_OK;
}

/* ========================================================================
 * Read all 10 channels from AS7343
 * ======================================================================== */
static void AS7343_ReadAllChannels(AS7343_Data_t *data)
{
    uint8_t buf[20];
    uint16_t raw;

    /* Start spectral measurement */
    uint8_t enable = AS7343_ReadReg(AS7343_REG_ENABLE);
    AS7343_WriteReg(AS7343_REG_ENABLE, enable | 0x02); /* SP_EN = 1 */

    /* Wait for measurement complete — data-ready on PB7 or polling */
    uint32_t timeout = 2000; /* 2 second timeout */
    while ((AS7343_ReadReg(AS7343_REG_ENABLE) & 0x02) && timeout--) {
        HAL_Delay(1);
    }

    /* Read channel data — 2 bytes per channel, 10 channels */
    AS7343_ReadBurst(AS7343_REG_CH0_DATA_L, buf, 20);

    for (int i = 0; i < AS7343_NUM_CHANNELS; i++) {
        raw = (uint16_t)buf[i * 2] | ((uint16_t)buf[i * 2 + 1] << 8);
        data->channels[i] = (float)raw;
    }

    /* Also read clear channel */
    raw = (uint16_t)buf[18] | ((uint16_t)buf[19] << 8);
    data->clear = (float)raw;
}

/* ========================================================================
 * Multi-LED Sweep Acquisition
 * ======================================================================== */
/*
 * The AS7343 provides 8 visible + 1 NIR channels at fixed wavelengths.
 * We augment these by sweeping LED drive current and using the UV LED
 * to extend sensitivity down to 340 nm. Each LED current step changes
 * the spectral power distribution slightly, giving us more sampling
 * points after deconvolution.
 *
 * Sweep sequence:
 *   1. UV LED on, low current → acquire (8 UV-weighted channels)
 *   2. UV LED on, high current → acquire (8 UV-weighted channels)
 *   3. White LED low current → acquire (8 channels)
 *   4. White LED medium current → acquire (8 channels)
 *   5. White LED high current → acquire (8 channels)
 *   6. White LED very high current → acquire (8 channels)
 *
 * Total: 48 channel readings + deconvolution → 128 effective points
 */

typedef struct {
    AS7343_Data_t uv_low;
    AS7343_Data_t uv_high;
    AS7343_Data_t white[4]; /* 4 current levels */
} SweepData_t;

static void PerformLEDSweep(SweepData_t *sweep)
{
    /* Phase 1: UV LED acquisition */
    LEDDriver_SetWhiteLED(false);
    LEDDriver_SetUVLED(true);

    LEDDriver_SetUVCurrent(UV_CURRENT_LOW);
    HAL_Delay(50); /* Settle */
    AS7343_ReadAllChannels(&sweep->uv_low);

    LEDDriver_SetUVCurrent(UV_CURRENT_HIGH);
    HAL_Delay(50);
    AS7343_ReadAllChannels(&sweep->uv_high);

    LEDDriver_SetUVLED(false);

    /* Phase 2: White LED acquisition at 4 current levels */
    LEDDriver_SetWhiteLED(true);

    static const uint16_t white_levels[4] = {
        WHITE_CURRENT_25,
        WHITE_CURRENT_50,
        WHITE_CURRENT_75,
        WHITE_CURRENT_100
    };

    for (int i = 0; i < 4; i++) {
        LEDDriver_SetWhiteCurrent(white_levels[i]);
        HAL_Delay(30); /* Settle */
        AS7343_ReadAllChannels(&sweep->white[i]);
    }

    LEDDriver_SetWhiteLED(false);
}

/* ========================================================================
 * Dark Acquisition
 * ======================================================================== */
void Spectrometer_AcquireDark(float dark[SPECTRUM_POINTS])
{
    AS7343_Data_t raw;

    /* All LEDs off */
    LEDDriver_SetWhiteLED(false);
    LEDDriver_SetUVLED(false);
    HAL_Delay(100);

    /* Acquire dark signal */
    AS7343_ReadAllChannels(&raw);

    /* Map 8 AS7343 channels to first 8 spectrum points */
    for (int i = 0; i < AS7343_NUM_CHANNELS; i++) {
        dark[i] = raw.channels[i];
    }

    /* Remaining points filled by deconvolution later */
    for (int i = AS7343_NUM_CHANNELS; i < SPECTRUM_POINTS; i++) {
        dark[i] = 0.0f; /* Deconvolution will interpolate */
    }
}

/* ========================================================================
 * Blank (Reference) Acquisition
 * ======================================================================== */
void Spectrometer_AcquireBlank(float reference[SPECTRUM_POINTS],
                                const float dark[SPECTRUM_POINTS])
{
    SweepData_t sweep;
    AS7343_Data_t darkData;

    /* Get dark current at each LED level */
    LEDDriver_SetWhiteLED(false);
    LEDDriver_SetUVLED(false);
    HAL_Delay(100);
    AS7343_ReadAllChannels(&darkData);

    /* Perform LED sweep with blank cuvette */
    PerformLEDSweep(&sweep);

    /* Combine sweep data into reference spectrum with dark subtraction */
    /* Use white LED at 75% as primary reference (best SNR) */
    for (int i = 0; i < AS7343_NUM_CHANNELS; i++) {
        reference[i] = sweep.white[2].channels[i] - dark[i];
        if (reference[i] < 1.0f) reference[i] = 1.0f; /* Floor */
    }

    /* Run deconvolution to fill 128 points */
    Deconv_Interpolate(reference, as7343_wavelengths, as7343_fwhm,
                        AS7343_NUM_CHANNELS, reference);
}

/* ========================================================================
 * Sample Acquisition
 * ======================================================================== */
void Spectrometer_AcquireSample(float absorbance[SPECTRUM_POINTS],
                                  const float reference[SPECTRUM_POINTS],
                                  const float dark[SPECTRUM_POINTS],
                                  SpectrumResult_t *result)
{
    SweepData_t sweep;
    float sample_raw[SPECTRUM_POINTS];

    /* Perform LED sweep with sample cuvette */
    PerformLEDSweep(&sweep);

    /* Combine sweep data into sample spectrum with dark subtraction */
    for (int i = 0; i < AS7343_NUM_CHANNELS; i++) {
        sample_raw[i] = sweep.white[2].channels[i] - dark[i];
        if (sample_raw[i] < 1.0f) sample_raw[i] = 1.0f;
    }

    /* Deconvolve to 128 points */
    Deconv_Interpolate(sample_raw, as7343_wavelengths, as7343_fwhm,
                        AS7343_NUM_CHANNELS, sample_raw);

    /* Calculate absorbance: A = -log10(sample / reference) */
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        if (reference[i] > 0.0f && sample_raw[i] > 0.0f) {
            float transmittance = sample_raw[i] / reference[i];
            if (transmittance > 0.0f) {
                absorbance[i] = -log10f(transmittance);
                /* Clamp to valid absorbance range */
                if (absorbance[i] < 0.0f) absorbance[i] = 0.0f;
                if (absorbance[i] > 2.0f) absorbance[i] = 2.0f;
            } else {
                absorbance[i] = 2.0f; /* Saturated */
            }
        } else {
            absorbance[i] = 2.0f;
        }
    }

    /* Baseline correction — remove scattering offset */
    Baseline_Correct(absorbance);

    /* Find peaks for result */
    result->num_peaks = 0;
    for (int i = 2; i < SPECTRUM_POINTS - 2; i++) {
        if (absorbance[i] > absorbance[i-1] && absorbance[i] > absorbance[i+1] &&
            absorbance[i] > 0.02f) {
            float wavelength = 340.0f + (360.0f * i / (SPECTRUM_POINTS - 1));
            result->peaks[result->num_peaks].wavelength = wavelength;
            result->peaks[result->num_peaks].absorbance = absorbance[i];
            result->num_peaks++;
            if (result->num_peaks >= MAX_PEAKS) break;
        }
    }

    result->status = SCAN_OK;
}