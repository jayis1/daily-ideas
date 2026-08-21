/*
 * types.h — shared types for the Bolt Compass firmware
 *
 * All signal-path modules share these structs so the detection,
 * classification, bearing, ranging, and storm-tracking stages can pass
 * a single sferic descriptor through the pipeline without copying.
 */
#ifndef BOLT_COMPASS_TYPES_H
#define BOLT_COMPASS_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define ADC_CH         4          /* ADS131M04 channels                */
#define ADC_RATE       8000       /* samples per second per channel    */
#define RING_LEN       2048       /* 256 ms ring at 8 ksps             */
#define SFERIC_WIN     400        /* 50 ms window at 8 ksps            */
#define NFEAT          16         /* feature vector length             */
#define NCLASS         3          /* CG, IC, CC                        */

/* class labels */
enum { CLASS_CG = 0, CLASS_IC = 1, CLASS_CC = 2 };

/* One 4-channel ADC sample (24-bit ADC → int16 after PGA/shift). */
typedef struct {
    int16_t ch[ADC_CH];           /* [0]=NS, [1]=EW, [2]=slow-E, [3]=fast-E */
} sample_t;

/* Circular ring buffer of samples, in PSRAM. */
typedef struct {
    sample_t  *buf;                /* RING_LEN entries                  */
    volatile int  wr;              /* write index (ISR-updated)         */
    volatile uint64_t ts_us;       /* timestamp of last sample (GPS)    */
} ring_t;

/* Extracted sferic features + raw peaks. */
typedef struct {
    /* waveform peaks (loop-amplitude units) */
    float peak_ns;
    float peak_ew;
    float peak_slow_e;
    float peak_fast_e;
    /* timing */
    float rise_us;                 /* 10→90 % rise time                 */
    float zero_cross_us;           /* time to first zero-cross after peak */
    /* energy ratios */
    float slow_tail_ratio;         /* energy 5–50 ms after peak / total  */
    float loop_coherence;          /* |cos(Δφ_NS-EW)| at peak            */
    float spectral_centroid_khz;   /* FFT centroid                      */
    /* polarity / sign */
    int   e_sign;                  /* +1 / -1 / 0                       */
    /* the 16-dim feature vector used by the classifier */
    float feat[NFEAT];
    /* the window (for logging / streaming) */
    int16_t wave_ns[SFERIC_WIN];
    int16_t wave_ew[SFERIC_WIN];
    int16_t wave_e[SFERIC_WIN];
    /* timestamp (GPS) of the trigger sample */
    uint64_t ts_us;
} sferic_t;

/* Classifier output. */
typedef struct {
    int   label;                   /* CLASS_CG / IC / CC                */
    float conf;                    /* softmax confidence 0..1           */
    float prob[NCLASS];
} classify_t;

/* Bearing + distance result. */
typedef struct {
    float azimuth_deg;             /* 0..360, 0=N, clockwise            */
    float distance_km;             /* propagation-model estimate        */
    float peak_field_uv;           /* calibrated peak E-field (µV/m)    */
} geo_t;

/* A fully-resolved stroke (sferic + class + geo). */
typedef struct {
    uint64_t    ts_us;
    sferic_t    sf;
    classify_t  cls;
    geo_t       geo;
} stroke_t;

/* Storm cell (DBSCAN output). */
typedef struct {
    float bearing_deg;
    float distance_km;
    int   stroke_count;
    int   cg_count;
    float flash_rate_per_min;
    uint64_t first_seen_us;
    uint64_t last_seen_us;
    float approach_kmph;           /* d(distance)/dt (negative = closing) */
    bool  active;
} storm_cell_t;

#define MAX_STORM_CELLS 8

typedef struct {
    storm_cell_t cell[MAX_STORM_CELLS];
    int n;
} storm_t;

/* Alert types */
typedef enum {
    ALERT_NONE = 0,
    ALERT_STORM_BUILDING,          /* slow-E electrification rising    */
    ALERT_STORM_APPROACHING,       /* CG cell < 20 km, closing         */
    ALERT_STORM_IMMINENT,          /* CG cell < 10 km                  */
    ALERT_FIRST_CG,                /* first CG of the day              */
} alert_t;

#endif /* BOLT_COMPASS_TYPES_H */