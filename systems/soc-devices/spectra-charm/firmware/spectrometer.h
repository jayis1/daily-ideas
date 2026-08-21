/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * spectrometer.h — AS7343 driver and spectral acquisition API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SPECTROMETER_H
#define SPECTROMETER_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

#define SPECTRUM_POINTS    128
#define AS7343_NUM_CHANNELS 9   /* F1-F8 + NIR */
#define MAX_PEAKS          16

/* Scan types */
typedef enum {
    SCAN_TYPE_DARK   = 0,
    SCAN_TYPE_BLANK  = 1,
    SCAN_TYPE_SAMPLE = 2,
} ScanType_t;

/* Scan status codes */
typedef enum {
    SCAN_OK              = 0,
    SCAN_ERR_NO_CUVETTE  = 1,
    SCAN_ERR_INVALID     = 2,
    SCAN_ERR_TIMEOUT     = 3,
    SCAN_ERR_SATURATED   = 4,
} ScanStatus_t;

/* Compound IDs */
typedef enum {
    COMPOUND_NONE        = 0,
    COMPOUND_KMNO4       = 1,  /* Potassium permanganate */
    COMPOUND_K2CR2O7     = 2,  /* Potassium dichromate */
    COMPOUND_CUSO4       = 3,  /* Copper sulfate */
    COMPOUND_COCL2       = 4,  /* Cobalt chloride */
    COMPOUND_NISO4       = 5,  /* Nickel sulfate */
    COMPOUND_FESO4       = 6,  /* Iron sulfate */
    COMPOUND_NO3_ION     = 7,  /* Nitrate (with reagent) */
    COMPOUND_PO4_ION     = 8,  /* Phosphate (with reagent) */
    COMPOUND_CHLOROPHYLL = 9,  /* Chlorophyll */
    COMPOUND_TARTRAZINE  = 10, /* Yellow food dye */
    COMPOUND_ALLURA_RED  = 11, /* Red food dye */
    COMPOUND_BRILLIANT_BLUE = 12, /* Blue food dye */
    COMPOUND_FLUORESCEIN = 13,
    COMPOUND_RHODAMINE_B = 14,
    COMPOUND_QUININE     = 15,
    /* IDs 16-200: extended library in SPI flash */
} CompoundID_t;

/* Peak descriptor */
typedef struct {
    float wavelength;    /* nm */
    float absorbance;     /* AU */
} Peak_t;

/* Compound match result */
typedef struct {
    CompoundID_t compound_id;
    float confidence;       /* Cosine similarity 0-1 */
    float molar_absorptivity; /* L/(mol·cm) at peak */
    uint8_t name_len;
    char name[32];
} CompoundMatch_t;

/* Scan request */
typedef struct {
    ScanType_t type;
    uint8_t gain;          /* AS7343 gain setting */
    uint16_t integration;  /* Integration time multiplier */
} ScanRequest_t;

/* Spectrum result */
typedef struct {
    ScanStatus_t status;
    uint16_t scan_number;
    uint8_t num_peaks;
    Peak_t peaks[MAX_PEAKS];
    CompoundMatch_t match;
    float concentration;  /* mol/L, if compound matched */
} SpectrumResult_t;

/* AS7343 data structure */
typedef struct {
    float channels[AS7343_NUM_CHANNELS];
    float clear;
} AS7343_Data_t;

/* LED current levels */
typedef enum {
    UV_CURRENT_LOW  = 5,    /* ~5 mA */
    UV_CURRENT_HIGH = 50,   /* ~50 mA */
} UVCurrent_t;

typedef enum {
    WHITE_CURRENT_25  = 512,   /* DAC value for 25% */
    WHITE_CURRENT_50  = 1024,  /* DAC value for 50% */
    WHITE_CURRENT_75  = 1536,  /* DAC value for 75% */
    WHITE_CURRENT_100 = 2048,  /* DAC value for 100% */
} WhiteCurrent_t;

/* Public API */
HAL_StatusTypeDef Spectrometer_Init(void);
void Spectrometer_AcquireDark(float dark[SPECTRUM_POINTS]);
void Spectrometer_AcquireBlank(float reference[SPECTRUM_POINTS],
                                const float dark[SPECTRUM_POINTS]);
void Spectrometer_AcquireSample(float absorbance[SPECTRUM_POINTS],
                                  const float reference[SPECTRUM_POINTS],
                                  const float dark[SPECTRUM_POINTS],
                                  SpectrumResult_t *result);

#endif /* SPECTROMETER_H */